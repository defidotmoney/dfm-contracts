from brownie import Contract


CONTROLLER = "0x1337F001E280420EcCe9E7B934Fa07D67fdb62CD"
MULTICALL = "0xcA11bde05977b3631167028862bE2a173976CA11"
STABLE = "0x69420f9E38a4e60a62224C489be4BF7a94402496"


def get_regulator():
    controller = Contract(CONTROLLER)
    return Contract(controller.peg_keeper_regulator())


def get_pegkeepers():
    regulator = get_regulator()
    return [Contract(i) for i in regulator.get_peg_keepers_with_debt_ceilings()[0]]


def show_pegkeeper_stats(sort_by=None):
    stable = Contract(STABLE)
    regulator = get_regulator()
    count = len(get_pegkeepers())

    pk_data = []
    for i in range(count):
        data = regulator.peg_keepers(i)
        pk = Contract(data["peg_keeper"])
        swap = Contract(data["pool"])
        paired = Contract(swap.coins(0))
        amounts = [
            paired.balanceOf(swap) / (10 ** paired.decimals()),
            stable.balanceOf(swap) / (10**18),
        ]
        pk_data.append(
            {
                "name": swap.name(),
                "debt": pk.debt(),
                "ceiling": data["debt_ceiling"],
                "profit": regulator.estimate_caller_profit(pk) / 1e18,
                "amounts": amounts,
                "tvl": sum(amounts),
                "price": swap.get_p(0) / 1e18,
            }
        )

    if sort_by:
        pk_data = sorted(pk_data, key=lambda x: x[sort_by], reverse=True)

    total_tvl = sum(i["tvl"] for i in pk_data)
    utilization = regulator.active_debt() / regulator.max_debt()

    print(f"Total TVL: ${total_tvl:,.2f}")
    print(f"Overall Utilization: {utilization:.2%}")

    for data in pk_data:
        tvl = data["tvl"]
        amounts = data["amounts"]
        print(f"\n{data['name']}")
        print(f"  TVL: ${data['tvl']:,.2f}")
        print(f"  Asset imbalance: {amounts[0]/tvl:.2%} / {amounts[1]/tvl:.2%}")
        print(f"  MONEY spot price: ${data['price']:.6f}")
        print(f"  PegKeeper utilization: {data['debt'] / data['ceiling']:.2%}")
        print(f"  Available caller profit: ${data['profit']:.2f}")


def update(acct, min_profit=0.25):
    """
    Checks for pegkeepers with sufficient profit, and calls to `update` on each.

    acct: The account that will call to update
    min_profit: Minimum required profit, expressed in USD
                (e.g 0.25 means the caller profits 25 cents)
    """
    regulator = get_regulator()
    peg_keepers = get_pegkeepers()

    in_profit = []
    for pk in peg_keepers:
        profit = regulator.estimate_caller_profit(pk) / 1e18
        if profit < min_profit:
            continue
        in_profit.append(pk)

    if not in_profit:
        print("No pegkeepers with sufficient profit")
        return

    print(f"Found {len(in_profit)} pegkeepers with sufficient profit")
    if len(in_profit) == 1:
        regulator.update(in_profit[0], {"from": acct})
    else:
        payload = [(regulator, True, regulator.update.encode_input(pk, acct)) for pk in in_profit]
        Contract(MULTICALL).aggregate3(payload, {"from": acct})
