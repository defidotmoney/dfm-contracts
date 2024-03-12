"""
Stateful test to create and repay loans without moving the price oracle
"""

import boa
from contextlib import contextmanager
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, run_state_machine_as_test, rule, invariant
from ..conftest import approx


DEAD_SHARES = 1000


class AllGood(Exception):
    pass


class StatefulLendBorrow(RuleBasedStateMachine):
    n = st.integers(min_value=5, max_value=50)
    amount_frac = st.floats(min_value=0.01, max_value=2)
    c_amount = st.integers(min_value=10**13, max_value=2**128 - 1)
    user_id = st.integers(min_value=0, max_value=9)

    def __init__(self):
        super().__init__()
        self.debt_ceiling = self.market.debt_ceiling()
        for u in self.accounts:
            with boa.env.prank(u):
                self.collateral_token.approve(self.market, 2**256 - 1)
                self.stablecoin.approve(self.market, 2**256 - 1)

    @contextmanager
    def health_calculator(self, user, d_collateral, d_amount):
        if self.market.loan_exists(user):
            calculation_success = True
            try:
                future_health = self.market.health_calculator(user, d_collateral, d_amount, False)
                future_health_full = self.market.health_calculator(
                    user, d_collateral, d_amount, True
                )
            except Exception:
                calculation_success = False

            try:
                yield

                # If we are here - no exception has happened in the wrapped function
                assert calculation_success
                assert approx(self.market.health(user), future_health, 1e-4)
                assert approx(self.market.health(user, True), future_health_full, 1e-4)

            except AllGood:
                pass

        else:
            try:
                yield
            except AllGood:
                pass

    @rule(c_amount=c_amount, amount_frac=amount_frac, n=n, user_id=user_id)
    def create_loan(self, c_amount, amount_frac, n, user_id):
        user = self.accounts[user_id]
        amount = min(int(amount_frac * c_amount * 3000), self.debt_ceiling)

        with boa.env.prank(user):
            try:
                self.collateral_token._mint_for_testing(user, c_amount)
            except Exception:
                return  # Probably overflow

            if self.market.loan_exists(user):
                with boa.reverts("Loan already created"):
                    self.controller.create_loan(user, self.market, c_amount, amount, n)
                return

            too_high = False
            try:
                self.market.calculate_debt_n1(c_amount, amount, n)
            except Exception as e:
                too_high = "Debt too high" in str(e)
            if too_high:
                with boa.reverts():
                    self.controller.create_loan(user, self.market, c_amount, amount, n)
                return

            if self.market.total_debt() + amount > self.debt_ceiling:
                if (
                    self.market.total_debt() + amount
                ) * self.amm.get_rate_mul() > 2**256 - 1 or c_amount * self.amm.get_p() > 2**256 - 1:
                    with boa.reverts():
                        self.controller.create_loan(user, self.market, c_amount, amount, n)
                else:
                    with boa.reverts():  # Dept ceiling or too deep
                        self.controller.create_loan(user, self.market, c_amount, amount, n)
                return

            if amount == 0:
                with boa.reverts("No loan"):
                    self.controller.create_loan(user, self.market, c_amount, amount, n)
                    # It's actually division by zero which happens
                return

            if c_amount // n >= (2**128 - 1) // DEAD_SHARES:
                with boa.reverts():
                    self.controller.create_loan(user, self.market, c_amount, amount, n)
                return

            if c_amount // n <= 100:
                with boa.reverts():
                    # Amount too low or too deep
                    self.controller.create_loan(user, self.market, c_amount, amount, n)
                return

            try:
                self.controller.create_loan(user, self.market, c_amount, amount, n)
            except Exception as e:
                if c_amount // n > 2 * DEAD_SHARES and c_amount // n < (2**128 - 1) // DEAD_SHARES:
                    if "Too deep" not in str(e):
                        raise

    @rule(amount_frac=amount_frac, user_id=user_id)
    def repay(self, amount_frac, user_id):
        user = self.accounts[user_id]
        xy = self.amm.get_sum_xy(user)
        amount = min(int(amount_frac * (xy[1] * 3000 + xy[0])), self.debt_ceiling)

        with self.health_calculator(user, 0, -amount):
            with boa.env.prank(user):
                if amount == 0:
                    return
                if not self.market.loan_exists(user):
                    with boa.reverts("Loan doesn't exist"):
                        self.controller.close_loan(user, self.market)
                    raise AllGood()

                if amount >= self.market.debt(user):
                    self.controller.close_loan(user, self.market)
                else:
                    self.controller.adjust_loan(user, self.market, 0, -amount)

                if self.market.debt(user) == 0:
                    raise AllGood()

    @rule(c_amount=c_amount, user_id=user_id)
    def add_collateral(self, c_amount, user_id):
        user = self.accounts[user_id]

        with self.health_calculator(user, c_amount, 0):
            with boa.env.prank(user):
                if c_amount == 0:
                    return

                try:
                    self.collateral_token._mint_for_testing(user, c_amount)
                except Exception:
                    raise AllGood()

                if not self.market.loan_exists(user):
                    with boa.reverts("Loan doesn't exist"):
                        self.controller.adjust_loan(user, self.market, c_amount, 0)
                    return

                if (c_amount + self.amm.get_sum_xy(user)[1]) * self.amm.get_p() > 2**256 - 1:
                    with boa.reverts():
                        self.controller.adjust_loan(user, self.market, c_amount, 0)
                    raise AllGood()

                try:
                    self.controller.adjust_loan(user, self.market, c_amount, 0)
                except Exception:
                    # Tick overflow = ok
                    assert (c_amount + self.amm.get_sum_xy(user)[1]) > (2**128 - 1) // (
                        50 * DEAD_SHARES
                    )
                    raise AllGood()

    @rule(c_amount=c_amount, amount_frac=amount_frac, user_id=user_id)
    def borrow_more(self, c_amount, amount_frac, user_id):
        user = self.accounts[user_id]
        amount = min(int(amount_frac * c_amount * 3000), self.debt_ceiling)

        with self.health_calculator(user, c_amount, amount):
            with boa.env.prank(user):
                try:
                    self.collateral_token._mint_for_testing(user, c_amount)
                except Exception:
                    raise AllGood()

                if amount == 0:
                    self.controller.adjust_loan(user, self.market, c_amount, amount)
                    return

                if not self.market.loan_exists(user):
                    with boa.reverts("Loan doesn't exist"):
                        self.controller.adjust_loan(user, self.market, c_amount, amount)
                    return

                final_debt = self.market.debt(user) + amount
                x, y = self.amm.get_sum_xy(user)
                assert x == 0
                final_collateral = y + c_amount
                n1, n2 = self.amm.read_user_tick_numbers(user)
                n = n2 - n1 + 1

                too_high = False
                try:
                    self.market.calculate_debt_n1(final_collateral, final_debt, n)
                except Exception as e:
                    too_high = "Debt too high" in str(e)
                if too_high:
                    with boa.reverts("Debt too high"):
                        self.controller.adjust_loan(user, self.market, c_amount, amount)
                    raise AllGood()

                if self.market.total_debt() + amount > self.debt_ceiling:
                    if (self.market.total_debt() + amount) * self.amm.get_rate_mul() > 2**256 - 1:
                        with boa.reverts():
                            self.controller.adjust_loan(user, self.market, c_amount, amount)
                    else:
                        with boa.reverts():
                            self.controller.adjust_loan(user, self.market, c_amount, amount)
                    raise AllGood()

                if final_collateral * self.amm.get_p() > 2**256 - 1:
                    with boa.reverts():
                        self.controller.adjust_loan(user, self.market, c_amount, amount)
                    raise AllGood()

                self.controller.adjust_loan(user, self.market, c_amount, amount)

    @invariant()
    def debt_supply(self):
        assert (
            self.market.total_debt()
            == self.stablecoin.totalSupply() - self.stablecoin.balanceOf(self.market)
        )

    @invariant()
    def sum_of_debts(self):
        assert sum(self.market.debt(u) for u in self.accounts) == self.market.total_debt()

    @invariant()
    def health(self):
        for user in self.accounts:
            if self.market.loan_exists(user):
                assert self.market.health(user) > 0


def test_stateful_lendborrow(controller, amm, market, collateral_token, stablecoin, accounts):
    StatefulLendBorrow.TestCase.settings = settings(max_examples=200, stateful_step_count=20)
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    run_state_machine_as_test(StatefulLendBorrow)


def test_large_loan_fail(controller, amm, market, collateral_token, stablecoin, accounts):
    StatefulLendBorrow.TestCase.settings = settings(max_examples=200, stateful_step_count=20)
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    with boa.env.anchor():
        state = StatefulLendBorrow()
        state.create_loan(
            amount_frac=1.0, c_amount=340282366920938463463374607431768211456, n=5, user_id=0
        )


def test_repay_no_calculation_success(
    controller, amm, market, monetary_policy, collateral_token, stablecoin, accounts, admin
):
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    with boa.env.anchor():
        state = StatefulLendBorrow()
        state.create_loan(amount_frac=0.5, c_amount=10000000000, n=5, user_id=0)
        state.repay(amount_frac=1.0, user_id=0)
