import boa


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ADMIN_ACTIONS_DEADLINE = 3 * 86400


def test_parameters(peg_keepers, swaps, stablecoin, core, receiver, pk_regulator):
    for peg_keeper, swap in zip(peg_keepers, swaps):
        assert peg_keeper.pegged() == stablecoin.address
        assert peg_keeper.pool() == swap.address

        assert peg_keeper.caller_share() == 2 * 10**4
        assert peg_keeper.regulator() == pk_regulator.address


def test_update_access(
    peg_keepers,
    pk_regulator,
    peg_keeper_updater,
    add_initial_liquidity,
    provide_token_to_peg_keepers,
    imbalance_pools,
):
    imbalance_pools(1)
    with boa.env.prank(peg_keeper_updater):
        for pk in peg_keepers:
            pk_regulator.update(pk)


def test_set_new_caller_share(peg_keepers, admin):
    new_caller_share = 5 * 10**4
    with boa.env.prank(admin):
        for pk in peg_keepers:
            pk.set_new_caller_share(new_caller_share)
            assert pk.caller_share() == new_caller_share


def test_set_new_caller_share_bad_value(peg_keepers, admin):
    with boa.env.prank(admin):
        for pk in peg_keepers:
            with boa.reverts():  # dev: bad part value
                pk.set_new_caller_share(10**5 + 1)


def test_set_new_caller_share_only_admin(peg_keepers, alice):
    with boa.env.prank(alice):
        for pk in peg_keepers:
            with boa.reverts():  # dev: only admin
                pk.set_new_caller_share(5 * 10**4)


def test_set_new_regulator(peg_keepers, admin, controller, alice, bob):
    new_regulator = bob
    for pk in peg_keepers:
        with boa.env.prank(alice):
            with boa.reverts():  # dev: only admin
                pk.set_regulator(new_regulator)
        with boa.env.prank(controller.address):
            pk.set_regulator(new_regulator)
            assert pk.regulator() == new_regulator
            with boa.reverts():  # dev: zero address
                pk.set_regulator(ZERO_ADDRESS)
