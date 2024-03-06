from brownie.network.account import Account
from brownie.network.contract import ContractContainer, Contract


def deploy_blueprint(contract: ContractContainer, deployer: Account) -> Contract:
    initcode = contract.bytecode
    initcode = bytes.fromhex(initcode[2:])
    initcode = b"\xfe\x71\x00" + initcode  # eip-5202 preamble version 0
    initcode = (
        b"\x61" + len(initcode).to_bytes(2, "big") + b"\x3d\x81\x60\x0a\x3d\x39\xf3" + initcode
    )
    tx = deployer.transfer(data=initcode)
    return contract.at(tx.contract_address)
