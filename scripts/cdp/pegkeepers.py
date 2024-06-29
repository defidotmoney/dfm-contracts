from brownie import Contract, multicall


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

    raw_data = []
    with multicall(MULTICALL):
        # sequencing here looks weird, but it's optimized for multicall
        raw_data = [regulator.peg_keepers(i) for i in range(count)]
        raw_data = [i.dict() for i in raw_data]
        for data in raw_data:
            data["pool"] = Contract(data["pool"])
            data["peg_keeper"] = Contract(data["peg_keeper"])

        for data in raw_data:
            data["paired"] = data["pool"].coins(0)

        for data in raw_data:
            data["paired"] = Contract(data["paired"])

        for data in raw_data:
            pk = data["peg_keeper"]
            swap = data["pool"]
            paired = data["paired"]

            data.update(
                amounts=[paired.balanceOf(swap), stable.balanceOf(swap)],
                decimals=paired.decimals(),
                name=swap.name(),
                debt=pk.debt(),
                profit=regulator.estimate_caller_profit(pk),
                price=swap.get_p(0),
            )

    for data in raw_data:
        data["amounts"] = [data["amounts"][0] / 10 ** data["decimals"], data["amounts"][1] / 1e18]
        data["tvl"] = sum(data["amounts"])
        data["profit"] = data["profit"] / 1e18
        data["price"] = data["price"] / 1e18
        data["ceiling"] = data.pop("debt_ceiling")

    if sort_by:
        raw_data = sorted(raw_data, key=lambda x: x[sort_by], reverse=True)

    total_tvl = sum(i["tvl"] for i in raw_data)
    utilization = regulator.active_debt() / regulator.max_debt()

    print(f"Total TVL: ${total_tvl:,.2f}")
    print(f"Overall Utilization: {utilization:.2%}")

    for data in raw_data:
        tvl = data["tvl"]
        amounts = data["amounts"]
        print(f"\n{data['name']}")
        print(f"  TVL: ${data['tvl']:,.2f}")
        print(f"  Asset imbalance: {amounts[0]/tvl:.2%} / {amounts[1]/tvl:.2%}")
        print(f"  MONEY spot price: ${data['price']:.6f}")
        print(f"  PegKeeper utilization: {data['debt'] / data['ceiling']:.2%}")
        print(f"  Available caller profit: ${data['profit']:.2f}")


def update(acct, min_profit=0.25, receiver=None):
    """
    Checks for pegkeepers with sufficient profit, and calls to `update` on each.

    Args:
        acct: The account that will call to update
        min_profit: Minimum required profit, expressed in USD
                    (e.g 0.25 means the caller profits 25 cents)
        receiver: Address to send profit to (defaults to `acct`)
    """
    regulator = get_regulator()
    peg_keepers = get_pegkeepers()

    if receiver is None:
        receiver = acct

    estimated_profit = {}
    with multicall(MULTICALL):
        for pk in peg_keepers:
            estimated_profit[pk] = regulator.estimate_caller_profit(pk)

    in_profit = []
    for pk, profit in estimated_profit.items():
        if profit > min_profit * 1e18:
            in_profit.append(pk)

    if not in_profit:
        print("No pegkeepers with sufficient profit")
        return

    print(f"Found {len(in_profit)} pegkeepers with sufficient profit")
    if len(in_profit) == 1:
        regulator.update(in_profit[0], receiver, {"from": acct})
    else:
        payload = [
            (regulator, True, regulator.update.encode_input(pk, receiver)) for pk in in_profit
        ]
        Contract(MULTICALL).aggregate3(payload, {"from": acct})
