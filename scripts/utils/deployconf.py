import yaml
from pathlib import Path

from brownie import network, Contract

from scripts.utils import deploylog
from scripts.utils.connection import ConnectionManager


_token_peers = {}


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


def primary_network():
    return load()["layerzero"]["primary_network"]


def is_primary_network():
    return active_network() == primary_network()


def is_forked():
    return network.show_active().endswith("-fork")


def get_token_peers():
    if not is_primary_network() and not _token_peers:
        primary_log = deploylog.load(primary_network(), exist_only=True)

        with ConnectionManager(primary_network()):
            for name, addr in primary_log["tokens"].items():
                _token_peers[name] = Contract(addr).getGlobalPeers()

        if is_forked():
            # remove peers for the active chain, to avoid reverting
            # if the real deployment has already occured
            lz_endpoint = Contract(load()["layerzero"]["endpoint"])
            lz_eid = lz_endpoint.eid()
            for name, peers in _token_peers.items():
                _token_peers[name] = [i for i in peers if i[0] != lz_eid]

    return _token_peers
