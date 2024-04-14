import brownie


def test_set_worst_price_threshold(regulator, deployer):
    regulator.set_worst_price_threshold(10**15, {"from": deployer})
    assert regulator.worst_price_threshold() == 10**15


def test_set_price_deviation(regulator, deployer):
    regulator.set_price_deviation(10**20, {"from": deployer})
    assert regulator.price_deviation() == 10**20


def test_set_debt_parameters(regulator, deployer):
    regulator.set_debt_parameters(10**16, 10**17, {"from": deployer})
    assert regulator.alpha() == 10**16
    assert regulator.beta() == 10**17


def test_set_caller_share(pk, deployer):
    pk.set_new_caller_share(10**5, {"from": deployer})


def test_set_worst_price_threshold_too_high(regulator, deployer):
    with brownie.reverts():
        regulator.set_worst_price_threshold(10**16 + 1, {"from": deployer})


def test_set_price_deviation_too_high(regulator, deployer):
    with brownie.reverts():
        regulator.set_price_deviation(10**20 + 1, {"from": deployer})


def test_set_debt_parameters_alpha_too_high(regulator, deployer):
    with brownie.reverts():
        regulator.set_debt_parameters(10**18 + 1, 10**17, {"from": deployer})


def test_set_debt_parameters_beta_too_high(regulator, deployer):
    with brownie.reverts():
        regulator.set_debt_parameters(10**16, 10**18 + 1, {"from": deployer})


def test_set_caller_share_too_high(pk, deployer):
    with brownie.reverts():
        pk.set_new_caller_share(10**6 + 1, {"from": deployer})
