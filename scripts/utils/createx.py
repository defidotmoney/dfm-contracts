from brownie import Contract

CREATE_X = "0xba5Ed099633D3B313e4D5F7bdc1305d3c28ba5Ed"


def deploy_deterministic(deployer, salt, container, *args):
    createx = Contract(CREATE_X)
    initcode = container.deploy.encode_input(*args)
    tx = createx.deployCreate3(salt, initcode, {"from": deployer})
    return container.at(tx.events["ContractCreation"]["newContract"])
