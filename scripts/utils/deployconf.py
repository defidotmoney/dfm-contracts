import yaml
from pathlib import Path

from brownie import network


def _recursive_merge(base_dict, new_dict):
    for key, value in new_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict):
            _recursive_merge(base_dict[key], new_dict[key])
        else:
            base_dict[key] = value


def load(network_name=None):
    """
    Load data from a deployments/config file.
    """
    if network_name is None:
        network_name = active_network()

    # Load deployment config for the target network
    with Path("deployments/config/default.yaml").open() as fp:
        config = yaml.safe_load(fp)

    with Path(f"deployments/config/{network_name}.yaml").open() as fp:
        _recursive_merge(config, yaml.safe_load(fp))

    return config


def active_network():
    network_name = network.show_active()

    if is_forked():
        network_name = network_name[:-5]

    return network_name


def is_forked():
    return network.show_active().endswith("-fork")
