from brownie import Contract, ZERO_ADDRESS

# periphery
from brownie import (
    FlashLoanZap,
    Layer2UptimeOracle,
    L2SequencerUptimeHook,
    MarketViews,
    SwapZap,
    WhitelistHook,
)

from scripts.utils import deployconf, deploylog


def main(deployer):
    """
    Deploy and configure all periphery contracts for the active network.
    """
    deploy_whitelist(deployer)
    deploy_uptime_hook(deployer)
    deploy_market_views(deployer)
    deploy_flashloan_zap(deployer)
    deploy_swap_zap(deployer)


def deploy_whitelist(deployer):
    if deployconf.load()["whitelist"]:
        controller = deploylog.get_deployment("MainController")
        hook = WhitelistHook.deploy(deployer, {"from": deployer})
        controller.add_market_hook(ZERO_ADDRESS, hook, {"from": deployer})
        deploylog.update(hook)


def deploy_uptime_hook(deployer):
    cl_oracle = deployconf.load()["chainlink"]["sequencer_uptime"]
    if cl_oracle:
        controller = deploylog.get_deployment("MainController")
        uptime_oracle = Layer2UptimeOracle.deploy(cl_oracle, {"from": deployer})
        hook = L2SequencerUptimeHook.deploy(uptime_oracle, {"from": deployer})
        controller.add_market_hook(ZERO_ADDRESS, hook, {"from": deployer})
        deploylog.update(uptime_oracle)


def deploy_market_views(deployer):
    controller = deploylog.get_deployment("MainController")

    views = MarketViews.deploy(controller, {"from": deployer})

    deploylog.update(views)

    return views


def deploy_flashloan_zap(deployer):
    controller, stable, router = _get_odos_zap_inputs()

    zap = FlashLoanZap.deploy(controller, stable, router, {"from": deployer})

    deploylog.update(zap)

    return zap


def deploy_swap_zap(deployer):
    controller, stable, router = _get_odos_zap_inputs()

    zap = SwapZap.deploy(controller, stable, router, {"from": deployer})

    deploylog.update(zap)

    return zap


def _get_odos_zap_inputs():
    controller = deploylog.get_deployment("MainController")
    stable = deploylog.get_deployment("MONEY")

    try:
        router = Contract(deployconf.load()["odos"]["router"])
    except:
        raise ValueError("Missing or invalid Odos router in deployment config")

    return controller, stable, router
