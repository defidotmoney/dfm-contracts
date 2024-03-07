import boa
import pytest
from hypothesis import strategies as st, given


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ADMIN_ACTIONS_DEADLINE = 3 * 86400


def test_price_range(peg_keepers, swaps, stablecoin, admin, receiver, pk_regulator):
    with boa.env.prank(admin):
        pk_regulator.set_price_deviation(10**17)
        for peg_keeper in peg_keepers:
            stablecoin.eval(f"self.balanceOf[{peg_keeper.address}] += {10 ** 18}")

    for peg_keeper, swap in zip(peg_keepers, swaps):
        assert pk_regulator.provide_allowed(peg_keeper)
        assert pk_regulator.withdraw_allowed(peg_keeper)

        # Move current price (get_p) a little
        swap.eval("self.rate_multipliers[0] *= 2")
        assert pk_regulator.provide_allowed(peg_keeper)
        assert pk_regulator.withdraw_allowed(peg_keeper)

        # Move further
        swap.eval("self.rate_multipliers[0] *= 5")

        assert not pk_regulator.provide_allowed(peg_keeper)
        assert not pk_regulator.withdraw_allowed(peg_keeper)


def test_price_order(
    peg_keepers,
    mock_peg_keepers,
    swaps,
    initial_amounts,
    stablecoin,
    admin,
    alice,
    mint_alice,
    pk_regulator,
    agg,
):
    with boa.env.prank(admin):
        for pk in [mock.address for mock in mock_peg_keepers]:
            pk_regulator.remove_peg_keeper(pk)

    # note: assuming swaps' prices are close enough
    for i, (peg_keeper, swap, (initial_amount, _)) in enumerate(
        zip(peg_keepers, swaps, initial_amounts)
    ):
        with boa.env.anchor():
            with boa.env.prank(admin):
                # Price change break aggregator.price() check
                agg.remove_price_pair(i)

            with boa.env.prank(alice):
                amount = 7 * initial_amount // 1000  # Just in
                # Make sure small decline still works
                swap.exchange(0, 1, amount, 0)
                boa.env.time_travel(seconds=6000)  # Update EMA
                assert pk_regulator.provide_allowed(peg_keeper)
                assert pk_regulator.withdraw_allowed(peg_keeper)  # no such check for withdraw

                # and a bigger one
                swap.exchange(0, 1, amount, 0)
                boa.env.time_travel(seconds=6000)  # Update EMA
                assert not pk_regulator.provide_allowed(peg_keeper)
                assert pk_regulator.withdraw_allowed(peg_keeper)


def test_aggregator_price(peg_keepers, mock_peg_keepers, pk_regulator, agg, admin, stablecoin):
    mock_peg_keeper = boa.load("contracts/testing/MockPegKeeper.vy", 10**18, stablecoin)
    with boa.env.prank(admin):
        agg.add_price_pair(mock_peg_keeper)
        for price in [0.95, 1.05]:
            mock_peg_keeper.set_price(int(price * 10**18))
            boa.env.time_travel(seconds=50000)
            for peg_keeper in peg_keepers:
                assert (pk_regulator.provide_allowed(peg_keeper) > 0) == (price > 1)
                assert (pk_regulator.withdraw_allowed(peg_keeper) > 0) == (price < 1)


def test_debt_limit(peg_keepers, mock_peg_keepers, pk_regulator, agg, admin, stablecoin):
    alpha, beta = 10**18 // 2, 10**18 // 4
    with boa.env.prank(admin):
        pk_regulator.set_debt_parameters(alpha, beta)
        for mock in mock_peg_keepers:
            mock.set_price(10**18)
    all_pks = mock_peg_keepers + peg_keepers

    # First peg keeper debt limit
    for pk in all_pks:
        pk.eval("self.debt = 0")
        stablecoin.eval(f"self.balanceOf[{pk.address}] = {10 ** 18}")
    for pk in all_pks:
        assert pk_regulator.provide_allowed(pk.address) == alpha**2 // 10**18

    # Three peg keepers debt limits
    for pk in all_pks[:2]:
        pk.eval("self.debt = 10 ** 18")
        stablecoin.eval(f"self.balanceOf[{pk.address}] = 0")
    for pk in all_pks[2:]:
        assert pk_regulator.provide_allowed(pk.address) == pytest.approx(10**18, abs=5)


def test_set_killed(pk_regulator, peg_keepers, admin):
    peg_keeper = peg_keepers[0]
    with boa.env.prank(admin):
        assert pk_regulator.is_killed() == 0

        assert pk_regulator.provide_allowed(peg_keeper)
        assert pk_regulator.withdraw_allowed(peg_keeper)

        pk_regulator.set_killed(1)
        assert pk_regulator.is_killed() == 1

        assert not pk_regulator.provide_allowed(peg_keeper)
        assert pk_regulator.withdraw_allowed(peg_keeper)

        pk_regulator.set_killed(2)
        assert pk_regulator.is_killed() == 2

        assert pk_regulator.provide_allowed(peg_keeper)
        assert not pk_regulator.withdraw_allowed(peg_keeper)

        pk_regulator.set_killed(3)
        assert pk_regulator.is_killed() == 3

        assert not pk_regulator.provide_allowed(peg_keeper)
        assert not pk_regulator.withdraw_allowed(peg_keeper)


def test_admin(pk_regulator, admin, alice):
    # initial parameters
    assert pk_regulator.worst_price_threshold() == 3 * 10 ** (18 - 4)
    assert pk_regulator.price_deviation() == 100 * 10**18
    assert (pk_regulator.alpha(), pk_regulator.beta()) == (10**18, 10**18)
    assert pk_regulator.is_killed() == 0

    # third party has no access
    with boa.env.prank(alice):
        with boa.reverts():
            pk_regulator.set_worst_price_threshold(10 ** (18 - 3))
        with boa.reverts():
            pk_regulator.set_price_deviation(10**17)
        with boa.reverts():
            pk_regulator.set_debt_parameters(10**18 // 2, 10**18 // 5)
        with boa.reverts():
            pk_regulator.set_killed(1)

    # admin has access
    with boa.env.prank(admin):
        pk_regulator.set_worst_price_threshold(10 ** (18 - 3))
        assert pk_regulator.worst_price_threshold() == 10 ** (18 - 3)

        pk_regulator.set_price_deviation(10**17)
        assert pk_regulator.price_deviation() == 10**17

        pk_regulator.set_debt_parameters(10**18 // 2, 10**18 // 5)
        assert (pk_regulator.alpha(), pk_regulator.beta()) == (10**18 // 2, 10**18 // 5)

        pk_regulator.set_killed(1)
        assert pk_regulator.is_killed() == 1


def get_peg_keepers(pk_regulator):
    return [
        # pk.get("peg_keeper") for pk in pk_regulator._storage.peg_keepers.get()  Available for titanoboa >= 0.1.8
        pk_regulator.peg_keepers(i)[0]
        for i in range(pk_regulator.eval("len(self.peg_keepers)"))
    ]


@pytest.fixture(scope="module")
def preset_peg_keepers(pk_regulator, admin, stablecoin):
    with boa.env.prank(admin):
        for pk in get_peg_keepers(pk_regulator):
            pk_regulator.remove_peg_keeper(pk)
    return [
        boa.load("contracts/testing/MockPegKeeper.vy", (1 + i) * 10**18, stablecoin).address
        for i in range(8)
    ]


@given(
    i=st.integers(min_value=1, max_value=8),
    j=st.integers(min_value=1, max_value=7),
)
def test_add_peg_keepers(pk_regulator, admin, preset_peg_keepers, i, j):
    j = min(i + j, 8)
    with boa.env.prank(admin):
        for pk in preset_peg_keepers[:i]:
            pk_regulator.add_peg_keeper(pk, 0)

        assert get_peg_keepers(pk_regulator) == preset_peg_keepers[:i]
        if j > i:
            for pk in preset_peg_keepers[i:j]:
                pk_regulator.add_peg_keeper(pk, 0)
            assert get_peg_keepers(pk_regulator) == preset_peg_keepers[:j]


@given(
    i=st.integers(min_value=1, max_value=8),
    js=st.lists(st.integers(min_value=0, max_value=7), min_size=1, max_size=8, unique=True),
)
def test_remove_peg_keepers(pk_regulator, admin, preset_peg_keepers, i, js):
    i = max(i, max(js) + 1)
    with boa.env.prank(admin):
        for pk in preset_peg_keepers[:i]:
            pk_regulator.add_peg_keeper(pk, 0)
        assert get_peg_keepers(pk_regulator) == preset_peg_keepers[:i]

        to_remove = [preset_peg_keepers[j] for j in js]
        for pk in to_remove:
            pk_regulator.remove_peg_keeper(pk)
        assert set(get_peg_keepers(pk_regulator)) == set(
            [preset_peg_keepers[k] for k in range(i) if k not in js]
        )


def test_peg_keepers_bad_values(pk_regulator, admin, preset_peg_keepers):
    with boa.env.prank(admin):
        for pk in preset_peg_keepers:
            pk_regulator.add_peg_keeper(pk, 0)

        pk_regulator.remove_peg_keeper(preset_peg_keepers[2])
        with boa.reverts():  # Could not find
            pk_regulator.remove_peg_keeper(preset_peg_keepers[2])
        with boa.reverts():  # Duplicate
            pk_regulator.add_peg_keeper(preset_peg_keepers[1], 0)

        pk_regulator.add_peg_keeper(preset_peg_keepers[2], 0)
