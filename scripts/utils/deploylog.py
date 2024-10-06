from pathlib import Path
import yaml

from brownie import network
from brownie.network.contract import ContractContainer
from brownie.project import get_loaded_projects


def get_path(network_name=None, exist_only=False, strip_fork=False):
    """
    Get the path for a deployment log.
    """
    if network_name is None:
        network_name = network.show_active()
        if strip_fork and network_name.endswith("-fork"):
            network_name = network_name[:-5]

    path = Path(f"deployments/logs/{network_name}.yaml")
    if exist_only and not path.exists():
        raise Exception(f"Missing deploy log for {network_name}!")

    return path


def exists(network_name=None):
    """
    Check if a deployment log exists.
    """
    path = get_path(network_name)
    return path.exists()


def load(network_name=None, exist_only=False):
    """
    Load data from a deployment log.
    """
    path = get_path(network_name, exist_only, True)

    if not path.exists():
        return {}

    with path.open() as fp:
        data = yaml.safe_load(fp)

    return data


def get_deployment(contract_name):
    if isinstance(contract_name, ContractContainer):
        contract_name = contract_name._name

    log = load()
    deployments = {k: v for x in log.values() for k, v in x.items()}
    project = get_loaded_projects()[0]

    if contract_name in log["tokens"]:
        container = project.BridgeToken
    else:
        container = project[contract_name]

    return container.at(deployments[contract_name])


def update(*contracts):
    """
    Add one or more deployments to the deploy log of the current active network.
    If no log file exists, a new one is created.
    """
    network_name = network.show_active()
    project = get_loaded_projects()[0]
    ERC20 = project.interface.ERC20
    sources = project._sources
    deploy_log = load(network_name, False)

    for contract in contracts:

        if all(hasattr(contract, i) for i in ERC20.selectors.values()):
            name = contract.symbol()
            category = "tokens"
        else:
            name = contract._name
            category = Path(sources.get_source_path(name)).parts[1]

        deploy_log.setdefault(category, {})[name] = contract.address

    Path("./deployments/logs").mkdir(exist_ok=True)
    with get_path(network_name).open("w") as fp:
        yaml.safe_dump(deploy_log, fp)
