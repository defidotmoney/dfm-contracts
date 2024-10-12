import math

from brownie import Contract, ZERO_ADDRESS
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
)

# fees
from brownie import (
    PrimaryFeeAggregator,
    FeeConverter,
    FeeConverterWithBridge,
    StableStaker,
    StakerRewardRegulator,
)

from scripts.utils import deployconf, deploylog
from scripts.utils.createx import deploy_deterministic
from scripts.utils.float2int import to_int
from scripts.utils.rate0 import apy_to_rate0
from scripts.deploy.periphery import main as deploy_periphery
from scripts.utils.address_id import get_address_identifier


DETERMINISTIC_DEPLOYER = "0xDeF1c4aD4a9C6bcd718C91e6AB79958217FA27DA"
TEAM_MULTISIG = "0x222d2B30EcD382a058618d9F1ee01F147666E48b"

CORE_DEPLOY_SALT = "0xdef1c4ad4a9c6bcd718c91e6ab79958217fa27da00fd7df6d5c020290265c131"
STABLECOIN_DEPLOY_SALT = "0xdef1c4ad4a9c6bcd718c91e6ab79958217fa27da008c17e7bcb0ca2203ff159b"
CONTROLLER_DEPLOY_SALT = "0xdef1c4ad4a9c6bcd718c91e6ab79958217fa27da006a506030994eee0392f93b"
SMONEY_DEPLOY_SALT = "0xdef1c4ad4a9c6bcd718c91e6ab79958217fa27da006c69152ac62ee10102566e"


def main(deployer="0xbADbABEFA66BfA6e01C4918229ea65e20BbC79e2"):
    """
    Deploys core Defi.Money contracts to mainnet.
    """

    if deploylog.load():
        raise Exception("Deploy log exists for this chain! Delete if you wish to continue.")

    # Deploy core contracts
    deploy_core(deployer)

    # Deploy and configure fee converters and sMONEY
    deploy_fees(deployer)

    # Deploy and configure periphery contracts
    deploy_periphery(deployer)

    # Deploy and configure pegkeepers
    update_pegkeepers(deployer)

    # Deploy and add monetary policies,
    # Deploy MarketOperator and AMM implementations,
    # Add individual markets
    update_markets(deployer)

    print("Deployment complete!")
    print(f" * Core deployment addresses saved at {deploylog.get_path().as_posix()}")
    print(" * Remember to verify source code!")
    if deployconf.is_primary_network():
        print(" * NOTE: Priority receivers are not deployed")
    else:
        print(" * Remember to set token peers on existing deployments:")
        for token in deploylog.load()["tokens"].values():
            token = Contract(token)
            eid = token.thisId()
            print(f'     {token.symbol()}.setPeer({eid}, "0x{to_bytes(token.address).hex()}")')


def deploy_core(deployer):
    token_peers = deployconf.get_token_peers()
    config = deployconf.load()

    lz_endpoint = Contract(config["layerzero"]["endpoint"])

    # Deploy core contracts
    core = deploy_deterministic(
        DETERMINISTIC_DEPLOYER,
        CORE_DEPLOY_SALT,
        DFMProtocolCore,
        deployer,
        config["core_owner"]["fee_receiver"],
        config["core_owner"]["start_offset"],
    )

    stable = deploy_deterministic(
        DETERMINISTIC_DEPLOYER,
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
        DETERMINISTIC_DEPLOYER,
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

    # Core contract configuration
    controller.set_peg_keeper_regulator(regulator, False, {"from": deployer})
    stable.setMinter(controller, True, {"from": deployer})
    stable.setMinter(regulator, True, {"from": deployer})

    deploylog.update(core, stable, controller, stable_oracle, regulator)


def deploy_fees(deployer):
    token_peers = deployconf.get_token_peers()
    config = deployconf.load()
    lz_endpoint = Contract(config["layerzero"]["endpoint"])

    core = deploylog.get_deployment(DFMProtocolCore)
    controller = deploylog.get_deployment(MainController)
    stable = deploylog.get_deployment("MONEY")
    stable_oracle = deploylog.get_deployment(AggregateStablePrice)

    if deployconf.is_primary_network():
        fee_agg = PrimaryFeeAggregator.deploy(
            core, stable, to_int(config["fees"]["fee_agg"]["caller_incentive"]), {"from": deployer}
        )

        fee_conf = config["fees"]["fee_converter"]
        fee_converter = FeeConverter.deploy(
            core,
            controller,
            stable,
            fee_agg,
            config["fees"]["weth"],
            to_int(fee_conf["swap_bonus_pct"], 2),
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
        deploy_deterministic(
            DETERMINISTIC_DEPLOYER,
            SMONEY_DEPLOY_SALT,
            StableStaker,
            core,
            stable,
            fee_agg,
            staker_reg,
            f"staked {config['stablecoin']['name']}",
            symbol,
            int(fee_conf["cooldown_days"] * 86400),
            lz_endpoint,
            config["layerzero"]["oft_default_options"],
            [],
        )

        fee_agg.setFallbackReceiver(stable_staker, {"from": deployer})
        deploylog.update(fee_agg)

    else:
        fee_agg = deploylog.load(deployconf.primary_network())["fees"]["PrimaryFeeAggregator"]
        fee_conf = config["fees"]["fee_converter"]

        fee_converter = FeeConverterWithBridge.deploy(
            core,
            controller,
            stable,
            fee_agg,
            config["fees"]["weth"],
            to_int(fee_conf["swap_bonus_pct"], 2),
            to_int(fee_conf["relay_min_balance"]),
            to_int(fee_conf["relay_max_swap_debt_amount"]),
            config["layerzero"]["primary_eid"],
            to_int(fee_conf["bridge_bonus_pct"], 2),
            to_int(fee_conf["bridge_max_bonus_amount"]),
            {"from": deployer},
        )

        symbol = f"s{config['stablecoin']['symbol']}"
        stable_staker = deploy_deterministic(
            DETERMINISTIC_DEPLOYER,
            SMONEY_DEPLOY_SALT,
            BridgeTokenSimple,
            core,
            f"staked {config['stablecoin']['name']}",
            symbol,
            lz_endpoint,
            config["layerzero"]["oft_default_options"],
            token_peers[symbol],
        )

    core.setAddress(get_address_identifier("FEE_RECEIVER"), fee_converter, {"from": deployer})
    deploylog.update(stable_staker, fee_converter)


def update_pegkeepers(deployer):
    """
    Iterates the list of pegkeepers within the deployment config, and deploys / configures
    necessary pegkeepers that do not yet exist.
    """
    config = deployconf.load()

    if "peg_keepers" not in config:
        print("\n *** WARNING: deploy config does not include `peg_keepers` ***\n")
        return

    curve_ap = Contract(config["curve"]["address_provider"])
    curve_factory = Contract(curve_ap.get_address(12))

    core = deploylog.get_deployment(DFMProtocolCore)
    controller = deploylog.get_deployment(MainController)
    regulator = deploylog.get_deployment(PegKeeperRegulator)
    stable = deploylog.get_deployment("MONEY")
    stable_oracle = deploylog.get_deployment(AggregateStablePrice)
    price_pairs = [stable_oracle.price_pairs(i)[0] for i in range(8)]
    price_pairs = [i for i in price_pairs if i != ZERO_ADDRESS]

    # Deploy and configure pegkeepers
    pool_conf = config["peg_keepers"]["pool_config"]
    for token in config["peg_keepers"]["paired_assets"]:
        token = Contract(token)
        swap = curve_factory.find_pool_for_coins(stable, token)
        if swap in price_pairs:
            continue

        if swap == ZERO_ADDRESS:
            # Deploy AMM for pegkeeper
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


def update_markets(deployer):
    """
    Iterates the list of markets within the deployment config, and creates the
    markets that do not exist yet.
    """
    config = deployconf.load()
    if "markets" not in config:
        print("\n *** WARNING: deploy config does not include `markets` ***\n")
        return

    core = deploylog.get_deployment(DFMProtocolCore)
    controller = deploylog.get_deployment(MainController)
    stable = deploylog.get_deployment("MONEY")
    stable_oracle = deploylog.get_deployment(AggregateStablePrice)

    uptime_oracle = ZERO_ADDRESS
    if config["chainlink"]["sequencer_uptime"]:
        uptime_oracle = deploylog.get_deployment("Layer2UptimeOracle")

    # Deploy and add monetary policies
    mp_deployed = {}
    monetary_policy_indexes = {}
    for i in range(2**256 - 1):
        mp = controller.monetary_policies(i)
        if mp == ZERO_ADDRESS:
            break

        mp = AggMonetaryPolicy.at(mp)
        mp_deployed[mp.rate0()] = i

    for base_apy in set(i["base_apy"] for i in config["markets"]):
        rate0 = apy_to_rate0(base_apy)
        if rate0 in mp_deployed:
            monetary_policy_indexes[base_apy] = mp_deployed[rate0]
        else:
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
            monetary_policy_indexes[base_apy] = controller.n_monetary_policies() - 1

    # Deploy MarketOperator and AMM implementations
    for A in set(i["A"] for i in config["markets"]):
        if controller.get_implementations(A)[0] != ZERO_ADDRESS:
            continue
        market_impl = MarketOperator.deploy(core, controller, A, {"from": deployer})
        amm_impl = AMM.deploy(controller, stable, A, {"from": deployer})
        controller.set_implementations(A, market_impl, amm_impl, {"from": deployer})

    # Add individual markets
    for market_conf in config["markets"]:
        collateral = Contract(market_conf["collateral"])

        if controller.get_market(collateral) != ZERO_ADDRESS:
            continue

        # Deploy required oracle contract(s)
        if market_conf["oracle"]["type"] == "chainlink":
            oracle = AggregateChainedOracle.deploy(core, uptime_oracle, {"from": deployer})
            calldata_view = oracle.price.encode_input()
            calldata_write = oracle.price_w.encode_input()

            call_path = []
            cl_oracles = market_conf["oracle"]["address"]
            if isinstance(cl_oracles, str):
                cl_oracles = [cl_oracles]

            for cl_oracle in cl_oracles:
                cl_ema = ChainlinkEMA.deploy(
                    cl_oracle,
                    market_conf["oracle"].get("observations", 20),
                    market_conf["oracle"].get("interval", 30),
                    {"from": deployer},
                )
                call_path.append((cl_ema, 18, True, calldata_view, calldata_write))

            oracle.addCallPath(call_path, {"from": deployer})

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
