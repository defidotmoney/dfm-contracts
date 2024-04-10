"""
Stateful test to create and repay loans without moving the price oracle
"""

import boa
from hypothesis import settings, Phase
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, run_state_machine_as_test, rule, invariant


DEAD_SHARES = 1000


class StatefulLendBorrow(RuleBasedStateMachine):
    n = st.integers(min_value=5, max_value=50)
    amount = st.integers(min_value=1, max_value=2**255 - 1)
    c_amount = st.integers(min_value=1, max_value=2**254)
    user_id = st.integers(min_value=0, max_value=9)

    def __init__(self):
        super().__init__()
        self.market = self.market
        self.debt_ceiling = self.market.debt_ceiling()
        for u in self.accounts:
            with boa.env.prank(u):
                self.collateral_token.approve(self.controller, 2**256 - 1)
                self.stablecoin.approve(self.controller, 2**256 - 1)

    @rule(c_amount=c_amount, amount=amount, n=n, user_id=user_id)
    def create_loan(self, c_amount, amount, n, user_id):
        user = self.accounts[user_id]

        with boa.env.prank(user):
            try:
                self.collateral_token._mint_for_testing(user, c_amount)
            except Exception:
                return  # Probably overflow

            if self.market.loan_exists(user):
                with boa.reverts("DFM:M Loan already exists"):
                    self.controller.create_loan(user, self.market, c_amount, amount, n)
                return

            too_high = False
            try:
                self.market.calculate_debt_n1(c_amount, amount, n)
            except Exception as e:
                too_high = "Debt too high" in str(e)
            if too_high:
                with boa.reverts("DFM:M Debt too high"):
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

            if c_amount // n > (2**128 - 1) // DEAD_SHARES:
                with boa.reverts():
                    self.controller.create_loan(user, self.market, c_amount, amount, n)
                return

            if c_amount // n <= DEAD_SHARES:
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

    @rule(amount=amount, user_id=user_id)
    def repay(self, amount, user_id):
        user = self.accounts[user_id]
        with boa.env.prank(user):
            if not self.market.loan_exists(user):
                with boa.reverts("DFM:M Loan doesn't exist"):
                    self.controller.adjust_loan(user, self.market, 0, -amount)
                return
            if amount >= self.market.debt(user):
                self.controller.close_loan(user, self.market)
            else:
                self.controller.adjust_loan(user, self.market, 0, -amount)

    @rule(c_amount=c_amount, user_id=user_id)
    def add_collateral(self, c_amount, user_id):
        user = self.accounts[user_id]

        with boa.env.prank(user):
            try:
                self.collateral_token._mint_for_testing(user, c_amount)
            except Exception:
                return  # Probably overflow

            if not self.market.loan_exists(user):
                with boa.reverts("DFM:M Loan doesn't exist"):
                    self.controller.adjust_loan(user, self.market, c_amount, 0)
                return

            if (c_amount + self.amm.get_sum_xy(user)[1]) * self.amm.get_p() > 2**256 - 1:
                with boa.reverts():
                    self.controller.adjust_loan(user, self.market, c_amount, 0)
                return

            try:
                self.controller.adjust_loan(user, self.market, c_amount, 0)
            except Exception:
                if (c_amount + self.amm.get_sum_xy(user)[1]) >= (2**128 - 1) // 50:
                    pass

    @rule(c_amount=c_amount, amount=amount, user_id=user_id)
    def borrow_more(self, c_amount, amount, user_id):
        user = self.accounts[user_id]

        with boa.env.prank(user):
            try:
                self.collateral_token._mint_for_testing(user, c_amount)
            except Exception:
                return  # Probably overflow

            if not self.market.loan_exists(user):
                with boa.reverts("DFM:M Loan doesn't exist"):
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
                with boa.reverts("DFM:M Debt too high"):
                    self.controller.adjust_loan(user, self.market, c_amount, amount)
                return

            if self.market.total_debt() + amount > self.debt_ceiling:
                if (self.market.total_debt() + amount) * self.amm.get_rate_mul() > 2**256 - 1:
                    with boa.reverts():
                        self.controller.adjust_loan(user, self.market, c_amount, amount)
                else:
                    with boa.reverts():
                        self.controller.adjust_loan(user, self.market, c_amount, amount)
                return

            if final_collateral * self.amm.get_p() > 2**256 - 1:
                with boa.reverts():
                    self.controller.adjust_loan(user, self.market, c_amount, amount)
                return

            try:
                self.controller.adjust_loan(user, self.market, c_amount, amount)
            except Exception:
                if (c_amount + self.amm.get_sum_xy(user)[1]) >= (2**128 - 1) // 50:
                    pass

    @invariant()
    def debt_supply(self):
        assert self.controller.total_debt() == self.stablecoin.totalSupply()

    @invariant()
    def sum_of_debts(self):
        assert sum(self.market.debt(u) for u in self.accounts) == self.controller.total_debt()

    @invariant()
    def health(self):
        for user in self.accounts:
            if self.market.loan_exists(user):
                assert self.market.health(user) > 0


def test_stateful_lendborrow(controller, amm, market, collateral_token, stablecoin, accounts):
    StatefulLendBorrow.TestCase.settings = settings(
        max_examples=50,
        stateful_step_count=20,
        phases=(Phase.explicit, Phase.reuse, Phase.generate, Phase.target),
    )
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    run_state_machine_as_test(StatefulLendBorrow)


def test_bad_health_underflow(controller, amm, market, collateral_token, stablecoin, accounts):
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    with boa.env.anchor():
        state = StatefulLendBorrow()
        state.create_loan(amount=1, c_amount=21, n=6, user_id=0)
        state.health()


def test_overflow(controller, amm, market, collateral_token, stablecoin, accounts):
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    with boa.env.anchor():
        state = StatefulLendBorrow()
        state.create_loan(
            amount=407364794483206832621538773467837164307398905518629081113581615337081836,
            c_amount=41658360764272065869638360137931952069431923873907374062,
            n=5,
            user_id=0,
        )


def test_health_overflow(controller, amm, market, collateral_token, stablecoin, accounts):
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    with boa.env.anchor():
        state = StatefulLendBorrow()
        state.create_loan(
            amount=256, c_amount=2787635851270792912435800128182537894764544, n=5, user_id=0
        )
        state.health()


def test_health_underflow_2(controller, amm, market, collateral_token, stablecoin, accounts):
    for k, v in locals().items():
        setattr(StatefulLendBorrow, k, v)
    with boa.env.anchor():
        state = StatefulLendBorrow()
        state.create_loan(amount=1, c_amount=44, n=6, user_id=0)
        state.health()
