import brownie

# PegKeeper


def test_update(pk, alice):
    with brownie.reverts("DFM:PK Only regulator"):
        pk.update(alice, {"from": alice})


def test_set_new_caller_share(pk, alice):
    with brownie.reverts("DFM:PK Only owner"):
        pk.set_new_caller_share(0, {"from": alice})


def test_set_regulator(pk, regulator, alice):
    with brownie.reverts("DFM:PK Only controller"):
        pk.set_regulator(regulator, {"from": alice})


def test_pk_recall_debt(pk, alice):
    with brownie.reverts("DFM:PK Only regulator"):
        pk.recall_debt(10_000 * 10**18, {"from": alice})


# PegKeeperRegulator


def test_init_migrate_peg_keepers(regulator, alice):
    with brownie.reverts("DFM:R Only controller"):
        regulator.init_migrate_peg_keepers([], [], {"from": alice})


def test_add_peg_keeper(regulator, pk, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.add_peg_keeper(pk, 0, {"from": alice})


def test_remove_peg_keeper(regulator, pk, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.remove_peg_keeper(pk, {"from": alice})


def test_adjust_peg_keeper_debt_ceiling(regulator, pk, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.adjust_peg_keeper_debt_ceiling(pk, 0, {"from": alice})


def test_set_worst_price_threshold(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_worst_price_threshold(0, {"from": alice})


def test_set_price_deviation(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_price_deviation(10**18, {"from": alice})


def test_set_debt_parameters(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_debt_parameters(10**18, 10**18, {"from": alice})


def test_set_killed(regulator, alice):
    with brownie.reverts("DFM:R Only owner"):
        regulator.set_killed(True, {"from": alice})
