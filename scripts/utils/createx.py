from brownie import accounts, network, Contract

CREATE_X = "0xba5Ed099633D3B313e4D5F7bdc1305d3c28ba5Ed"


def deploy_deterministic(deployer, salt, container, *args):
    deployer = accounts.at(deployer, force=True)
    createx = Contract(CREATE_X)
    initcode = container.deploy.encode_input(*args)

    if network.show_active().endswith("-fork"):
        try:
            createx.deployCreate3.call(salt, initcode, {"from": deployer})
        except:
            # CreateX deploy fails - probably the real deploy already occured
            # on this chain. In this case we fall back to a normal deploy.
            contract = container.deploy(*args, {"from": deployer})
            return contract

    tx = createx.deployCreate3(salt, initcode, {"from": deployer})
    deploy_address = tx.events["ContractCreation"]["newContract"]
    contract = container.at(deploy_address)

    print(f"  {container._name} deployed at: {contract.address}\n")
    return contract
