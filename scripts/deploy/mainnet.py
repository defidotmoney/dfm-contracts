import math

from brownie import accounts, Contract, ZERO_ADDRESS
from brownie.convert import to_bytes

# core contracts
from brownie import (
    AggregateStablePrice,
    AggMonetaryPolicy,
    AMM,
    BridgeToken,
    BridgeTokenSimple,
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
    PriceOracleMock,
    Layer2UptimeOracle,
)

# fees
from brownie import (
    PrimaryFeeAggregator,
    FeeConverter,
    FeeConverterWithBridge,
    StableStaker,
    StakerRewardRegulator,
)

# hooks
from brownie import (
    L2SequencerUptimeHook,
    WhitelistHook,
)

from scripts.utils import deployconf, deploylog
from scripts.utils.connection import ConnectionManager
from scripts.utils.createx import deploy_deterministic
from scripts.utils.float2int import to_int
from scripts.utils.rate0 import apy_to_rate0
from scripts.deploy.periphery import main as deploy_periphery


TEAM_MULTISIG = "0x222d2B30EcD382a058618d9F1ee01F147666E48b"

CORE_DEPLOY_SALT = "0xdef1c4ad4a9c6bcd718c91e6ab79958217fa27da00fd7df6d5c020290265c131"
STABLECOIN_DEPLOY_SALT = "0xdef1c4ad4a9c6bcd718c91e6ab79958217fa27da008c17e7bcb0ca2203ff159b"
CONTROLLER_DEPLOY_SALT = "0xdef1c4ad4a9c6bcd718c91e6ab79958217fa27da006a506030994eee0392f93b"


def main():
    """
    Deploys core Defi.Money contracts to mainnet.
    """

    # TODO set the actual `account` objects here
    # deterministic deployer must be consistent between chains
    deterministic_deployer = "0xDeF1c4aD4a9C6bcd718C91e6AB79958217FA27DA"
    # normal deployer should be unique per-chain to avoid overlap in non-deterministic addresses
    deployer = "0xbADbABEFA66BfA6e01C4918229ea65e20BbC79e2"

    config = deployconf.load()
    is_forked = deployconf.is_forked()
    if not is_forked and deploylog.load():
        raise Exception("Deploy log exists for this chain! Delete if you wish to continue.")

    # Initialize required external contracts, in case of a misconfig we fail early
    lz_endpoint = Contract(config["layerzero"]["endpoint"])
    curve_ap = Contract(config["curve"]["address_provider"])
    curve_factory = Contract(curve_ap.get_address(12))
    lz_eid = lz_endpoint.eid()

    # Get remote peers for stablecoin
    is_primary_network = deployconf.active_network() == config["layerzero"]["primary_network"]
    token_peers = {}

    if not is_primary_network:
        primary_network_name = config["layerzero"]["primary_network"]

        if not deploylog.exists(primary_network_name):
            raise Exception("Missing deploy log for primary chain!")

        primary_log = deploylog.load(primary_network_name)
        fee_agg = primary_log["fees"]["PrimaryFeeAggregator"]

        with ConnectionManager(primary_network_name):
            for name, addr in primary_log["tokens"].items():
                peers = Contract(addr).getGlobalPeers()

                if is_forked:
                    # remove peers for the active chain, to avoid reverting
                    # if the real deployment has already occured
                    peers = [i for i in peers if i[0] != lz_eid]

                token_peers[name] = peers

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
        config["layerzero"]["oft_default_options"],
        token_peers.get(config["stablecoin"]["symbol"], []),
    )

    controller = deploy_deterministic(
        deterministic_deployer,
        CONTROLLER_DEPLOY_SALT,
        MainController,
        core,
        stable,
        [],
        to_int(config["main_controller"]["global_debt_ceiling"]),
    )

    stable_oracle = AggregateStablePrice.deploy(
        core, stable, to_int(config["stable_oracle"]["sigma"]), {"from": deployer}
    )
    regulator = PegKeeperRegulator.deploy(
        core,
        controller,
        stable,
        stable_oracle,
        to_int(config["peg_keepers"]["worst_price_threshold"]),
        to_int(config["peg_keepers"]["price_deviation"]),
        config["peg_keepers"]["action_delay"],
        {"from": deployer},
    )

    # deploy fee converters and sMONEY
    if is_primary_network:
        fee_agg = PrimaryFeeAggregator.deploy(
            core, stable, config["fees"]["fee_agg"]["caller_incentive"], {"from": deployer}
        )

        fee_conf = config["fees"]["fee_converter"]
        fee_converter = FeeConverter.deploy(
            core,
            controller,
            stable,
            fee_agg,
            config["fees"]["weth"],
            to_int(fee_conf["swap_bonus_pct"], 2),
            to_int(fee_conf["swap_max_bonus_amount"]),
            to_int(fee_conf["relay_min_balance"]),
            to_int(fee_conf["relay_max_swap_debt_amount"]),
            {"from": deployer},
        )

        fee_conf = config["fees"]["stable_staker"]
        staker_reg = StakerRewardRegulator.deploy(
            core,
            stable_oracle,
            to_int(fee_conf["min_price"]),
            to_int(fee_conf["max_price"]),
            to_int(fee_conf["min_pct"], 2),
            to_int(fee_conf["max_pct"], 2),
            {"from": deployer},
        )

        symbol = f"s{config['stablecoin']['symbol']}"
        stable_staker = StableStaker.deploy(
            core,
            stable,
            fee_agg,
            staker_reg,
            f"staked {config['stablecoin']['name']}",
            symbol,
            int(fee_conf["cooldown_days"] * 7),
            lz_endpoint,
            config["layerzero"]["oft_default_options"],
            token_peers.get(symbol, []),
            {"from": deployer},
        )

        fee_agg.setFallbackReceiver(stable_staker, {"from": deployer})

    else:
        fee_conf = config["fees"]["fee_converter"]
        fee_converter = FeeConverterWithBridge.deploy(
            core,
            controller,
            stable,
            fee_agg,
            config["fees"]["weth"],
            to_int(fee_conf["swap_bonus_pct"], 2),
            to_int(fee_conf["swap_max_bonus_amount"]),
            to_int(fee_conf["relay_min_balance"]),
            to_int(fee_conf["relay_max_swap_debt_amount"]),
            config["layerzero"]["primary_eid"],
            to_int(fee_conf["bridge_bonus_pct"], 2),
            to_int(fee_conf["bridge_max_bonus_amount"]),
            {"from": deployer},
        )

        symbol = f"s{config['stablecoin']['symbol']}"
        stable_staker = BridgeTokenSimple.deploy(
            core,
            f"staked {config['stablecoin']['name']}",
            symbol,
            lz_endpoint,
            config["layerzero"]["oft_default_options"],
            token_peers[symbol],
            {"from": deployer},
        )

    # Write the core deployment addresses to a log file. There are more contracts
    # to deploy, but with this we have enough to plug in our front-end.
    deploylog.update(
        core, stable, controller, stable_oracle, regulator, stable_staker, fee_converter
    )
    if is_primary_network:
        deploylog.update(fee_agg)

    # Core contract configuration
    controller.set_peg_keeper_regulator(regulator, False, {"from": deployer})
    stable.setMinter(controller, True, {"from": deployer})
    stable.setMinter(regulator, True, {"from": deployer})

    # Deploy and add monetary policies
    monetary_policy_indexes = {}
    for c, base_apy in enumerate(set(i["base_apy"] for i in config["markets"])):
        mp = AggMonetaryPolicy.deploy(
            core,
            controller,
            stable_oracle,
            apy_to_rate0(base_apy),
            to_int(config["monetary_policy"]["sigma"]),
            to_int(config["monetary_policy"]["target_debt_fraction"]),
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
        name = f"{token.symbol()}/{config['stablecoin']['symbol']} Curve LP"
        symbol = f"dfm{token.symbol()}"
        curve_factory.deploy_plain_pool(
            name,
            symbol,
            [token, stable],
            pool_conf["A"],
            to_int(pool_conf["fee"], 10),
            to_int(pool_conf["offpeg_fee_mul"], 10),
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
            to_int(config["peg_keepers"]["caller_profit_fraction"], 5),
            {"from": deployer},
        )

        # Configuration
        stable_oracle.add_price_pair(swap, {"from": deployer})
        regulator.add_peg_keeper(
            peg_keeper, to_int(config["peg_keepers"]["debt_ceiling"]), {"from": deployer}
        )

    # Optionally deploy l2 sequencer uptime oracle and hook
    uptime_oracle = ZERO_ADDRESS
    if config["chainlink"]["sequencer_uptime"]:
        uptime_oracle = Layer2UptimeOracle.deploy(
            config["chainlink"]["sequencer_uptime"], {"from": deployer}
        )
        hook = L2SequencerUptimeHook.deploy(uptime_oracle, {"from": deployer})
        controller.add_market_hook(ZERO_ADDRESS, hook, {"from": deployer})

    if config["whitelist"]:
        hook = WhitelistHook.deploy(deployer, {"from": deployer})
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
            print("WARNING: Deploying PriceOracleMock - do not use this in prod!")
            oracle = PriceOracleMock.deploy(
                market_conf["oracle"].get("price", 10**18), {"from": deployer}
            )

        else:
            raise Exception(f"Unknown oracle type: {market_conf['oracle']['type']}")

        # Create the actual market
        tx = controller.add_market(
            collateral,
            market_conf["A"],
            to_int(market_conf["amm_fee"]),
            to_int(market_conf["amm_admin_fee"]),
            oracle,
            monetary_policy_indexes[market_conf["base_apy"]],
            to_int(market_conf["loan_discount"]),
            to_int(market_conf["liquidation_discount"]),
            to_int(market_conf["debt_ceiling"]),
            {"from": deployer},
        )

        # Initialize brownie deploy artifacts for the new market
        MarketOperator.at(tx.events["AddMarket"]["market"])
        AMM.at(tx.events["AddMarket"]["amm"])

    # Deploy periphery contracts
    deploy_periphery(deployer)

    print("Deployment complete!")
    print(f" * Core deployment addresses saved at {deploylog.get_path().as_posix()}")
    print(" * Remember to verify source code!")
    if config["whitelist"]:
        print(" * Remember to add approved accounts to the whitelist!")
    else:
        print(" * NOTE: No whitelist active, any account can interact with the system.")
    if is_primary_network:
        print(" * NOTE: Priority receivers are not deployed")
    else:
        print(" * Remember to add the stablecoin as a peer on existing deployments:")
        for token in [stable, stable_staker]:
            print(f'     {token.symbol()}.setPeer({lz_eid}, "0x{to_bytes(token.address).hex()}")')
