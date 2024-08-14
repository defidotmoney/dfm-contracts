from brownie import Contract

# periphery
from brownie import (
    FlashLoanZap,
    MarketViews,
    SwapZap,
)

from scripts.utils import deployconf, deploylog


def main(deployer):
    """
    Deploy all periphery contracts to the active network.
    """
    deploy_market_views(deployer)
    deploy_flashloan_zap(deployer)
    deploy_swap_zap(deployer)


def deploy_market_views(deployer):
    controller = deploylog.load(exist_only=True)["cdp"]["MainController"]

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
    log = deploylog.load(exist_only=True)
    controller = Contract(log["cdp"]["MainController"])
    stable = Contract(log["tokens"]["MONEY"])

    try:
        router = Contract(deployconf.load()["odos"]["router"])
    except:
        raise ValueError("Missing or invalid Odos router in deployment config")

    return controller, stable, router
