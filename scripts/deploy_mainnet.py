import math
import yaml
from pathlib import Path

from brownie import accounts, network, Contract, ZERO_ADDRESS
from brownie.convert import to_bytes

# core contracts
from brownie import (
    AggregateStablePrice,
    AggMonetaryPolicy,
    AMM,
    BridgeToken,
    DFMProtocolCore,
    MainController,
    MarketOperator,
    PegKeeper,
    PegKeeperRegulator,
)

# oracles
from brownie import (
    AggregateChainedOracle,
    ChainlinkEMA,
    DummyPriceOracle,
    Layer2UptimeOracle,
)

# hooks
from brownie import (
    L2SequencerUptimeHook,
)

# periphery
from brownie import (
    MarketViews,
)

from scripts.utils.connection import ConnectionManager
from scripts.utils.createx import deploy_deterministic
from scripts.utils.rate0 import apy_to_rate0


# TODO
CORE_DEPLOY_SALT = "0x01"
STABLECOIN_DEPLOY_SALT = "0x02"
CONTROLLER_DEPLOY_SALT = "0x03"


def _recursive_merge(base_dict, new_dict):
    for key, value in new_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict):
            _recursive_merge(base_dict[key], new_dict[key])
        else:
            base_dict[key] = value


def main():
    """
    Deploys core Defi.Money contracts to mainnet.
    """

    # TODO
    deterministic_deployer = "0xDeF1c4aD4a9C6bcd718C91e6AB79958217FA27DA"
    deployer = accounts[0]

    network_name = network.show_active()
    deploy_log = Path(f"./deployments/logs/{network_name}.yaml")
    if network_name.endswith("-fork"):
        network_name = network_name[:-5]
    elif deploy_log.exists():
        raise Exception("Deploy log exists for this chain! Delete if you wish to continue.")

    # Load deployment config for the target network
    with Path("deployments/config/default.yaml").open() as fp:
        config = yaml.safe_load(fp)

    with Path(f"deployments/config/{network_name}.yaml").open() as fp:
        _recursive_merge(config, yaml.safe_load(fp))

    # Get remote peers for stablecoin
    stable_peers = []
    Path("./deployments/logs").mkdir(exist_ok=True)
    if network_name != config["layerzero"]["primary_network"]:
        primary_network_name = config["layerzero"]["primary_network"]
        primary_deploy_log = Path(f"deployments/logs/{primary_network_name}.yaml")
        if not primary_deploy_log.exists():
            raise Exception("Missing deploy log for primary chain!")
        with primary_deploy_log.open() as fp:
            remote_stable = yaml.safe_load(fp)[config["stablecoin"]["symbol"]]
        with ConnectionManager(primary_network_name):
            stable_peers = Contract(remote_stable).getGlobalPeers()

    # Initialize required external contracts, in case of a misconfig we fail early
    lz_endpoint = Contract(config["layerzero"]["endpoint"])
    curve_ap = Contract(config["curve"]["address_provider"])
    curve_factory = Contract(curve_ap.get_address(12))

    # Deploy core contracts
    core = deploy_deterministic(
        deterministic_deployer,
        CORE_DEPLOY_SALT,
        DFMProtocolCore,
        deployer,
        config["core_owner"]["fee_receiver"],
        config["core_owner"]["start_offset"],
    )

    stable = deploy_deterministic(
        deterministic_deployer,
        STABLECOIN_DEPLOY_SALT,
        BridgeToken,
        core,
        config["stablecoin"]["name"],
        config["stablecoin"]["symbol"],
        lz_endpoint,
        config["stablecoin"]["default_options"],
        stable_peers,
    )

    controller = deploy_deterministic(
        deterministic_deployer,
        CONTROLLER_DEPLOY_SALT,
        MainController,
        core,
        stable,
        [],
        config["main_controller"]["global_debt_ceiling"] * 1e18,
    )

    stable_oracle = AggregateStablePrice.deploy(
        core, stable, config["stable_oracle"]["sigma"] * 1e18, {"from": deployer}
    )
    regulator = PegKeeperRegulator.deploy(
        core,
        controller,
        stable,
        stable_oracle,
        config["peg_keepers"]["worst_price_threshold"] * 1e18,
        config["peg_keepers"]["price_deviation"] * 1e18,
        config["peg_keepers"]["action_delay"],
        {"from": deployer},
    )

    # Deploy periphery contracts
    views = MarketViews.deploy(controller, {"from": deployer})

    # Write the core deployment addresses to a log file. There are more contracts
    # to deploy, but with this we have enough to plug in our front-end.
    deployments = {
        "DFMProtocolCore": core.address,
        config["stablecoin"]["symbol"]: stable.address,
        "MainController": controller.address,
        "AggregateStablePrice": stable_oracle.address,
        "PegKeeperRegulator": regulator.address,
        "MarketViews": views.address,
    }
    with deploy_log.open("w") as fp:
        yaml.safe_dump(deployments, fp)

    # Core contract configuration
    controller.set_peg_keeper_regulator(regulator, False, {"from": deployer})
    stable.setMinter(controller, True, {"from": deployer})
    stable.setMinter(regulator, True, {"from": deployer})

    # Deploy and add monetary policies
    monetary_policy_indexes = {}
    for c, base_apy in enumerate(set(i["base_apy"] for i in config["markets"])):
        mp = AggMonetaryPolicy.deploy(
            core,
            stable_oracle,
            controller,
            apy_to_rate0(base_apy),
            config["monetary_policy"]["sigma"] * 1e18,
            config["monetary_policy"]["target_debt_fraction"] * 1e18,
            {"from": deployer},
        )
        controller.add_new_monetary_policy(mp, {"from": deployer})
        monetary_policy_indexes[base_apy] = c

    # Deploy MarketOperator and AMM implementations
    for A in set(i["A"] for i in config["markets"]):
        market_impl = MarketOperator.deploy(core, controller, A, {"from": deployer})
        amm_impl = AMM.deploy(controller, stable, A, {"from": deployer})
        controller.set_implementations(A, market_impl, amm_impl, {"from": deployer})

    # Deploy and configure pegkeepers
    pool_conf = config["peg_keepers"]["pool_config"]
    for token in config["peg_keepers"]["paired_assets"]:
        # Deploy AMM for pegkeeper
        token = Contract(token)
        name = f"{config['stablecoin']['symbol']}/{token.symbol()} Curve LP"
        symbol = f"{config['stablecoin']['symbol']}{token.symbol()}"
        curve_factory.deploy_plain_pool(
            name,
            symbol,
            [stable, token],
            pool_conf["A"],
            pool_conf["fee"] * 1e10,
            pool_conf["offpeg_fee_mul"] * 1e10,
            round(pool_conf["ma_seconds"] / math.log(2)),
            0,
            [0, 0],
            [0, 0],
            [ZERO_ADDRESS, ZERO_ADDRESS],
            {"from": deployer},
        )
        swap = curve_factory.find_pool_for_coins(stable, token)

        # Deploy pegkeeper
        peg_keeper = PegKeeper.deploy(
            core,
            regulator,
            controller,
            stable,
            swap,
            config["peg_keepers"]["caller_profit_fraction"] * 1e5,
            {"from": deployer},
        )

        # Configuration
        stable_oracle.add_price_pair(swap, {"from": deployer})
        regulator.add_peg_keeper(
            peg_keeper, config["peg_keepers"]["debt_ceiling"] * 1e18, {"from": deployer}
        )

    # Optionally deploy l2 sequencer uptime oracle and hook
    uptime_oracle = ZERO_ADDRESS
    if config["chainlink"]["sequencer_uptime"]:
        uptime_oracle = Layer2UptimeOracle.deploy(
            config["chainlink"]["sequencer_uptime"], {"from": deployer}
        )
        hook = L2SequencerUptimeHook.deploy(uptime_oracle, {"from": deployer})
        controller.add_market_hook(ZERO_ADDRESS, hook, {"from": deployer})

    # Add individual markets
    for market_conf in config["markets"]:
        collateral = Contract(market_conf["collateral"])

        # Deploy required oracle contract(s)
        if market_conf["oracle"]["type"] == "chainlink":
            cl_ema = ChainlinkEMA.deploy(
                market_conf["oracle"]["address"],
                market_conf["oracle"].get("observations", 10),
                market_conf["oracle"].get("interval", 60),
                {"from": deployer},
            )
            oracle = AggregateChainedOracle.deploy(core, uptime_oracle, {"from": deployer})
            calldata_view = oracle.price.encode_input()
            calldata_write = oracle.price_w.encode_input()
            oracle.addCallPath(
                [
                    (cl_ema, 18, True, calldata_view, calldata_write),
                    (stable_oracle, 18, False, calldata_view, calldata_write),
                ],
                {"from": deployer},
            )

        elif market_conf["oracle"]["type"] == "dummy":
            print("WARNING: Deploying DummyPriceOracle - do not use this in prod!")
            oracle = DummyPriceOracle.deploy(
                market_conf["oracle"].get("price", 10**18), {"from": deployer}
            )

        else:
            raise Exception(f"Unknown oracle type: {market_conf['oracle']['type']}")

        # Create the actual market
        tx = controller.add_market(
            collateral,
            market_conf["A"],
            market_conf["amm_fee"] * 1e18,
            market_conf["amm_admin_fee"] * 1e18,
            oracle,
            monetary_policy_indexes[market_conf["base_apy"]],
            market_conf["loan_discount"] * 1e18,
            market_conf["liquidation_discount"] * 1e18,
            market_conf["debt_ceiling"] * 1e18,
            {"from": deployer},
        )

        # Initialize brownie deploy artifacts for the new market
        MarketOperator.at(tx.events["AddMarket"]["market"])
        AMM.at(tx.events["AddMarket"]["amm"])

    print("Deployment complete!")
    print(f" * Core deployment addresses saved at {deploy_log.as_posix()}")
    print(" * Remember to verify source code!")
    if stable_peers:
        print(" * Remember to add the stablecoin as a peer on existing deployments:")
        print(f'     setPeer({lz_endpoint.eid()}, "0x{to_bytes(stable.address).hex()}")')
