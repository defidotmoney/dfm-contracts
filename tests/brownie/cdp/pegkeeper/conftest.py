import pytest
from brownie_tokens import ERC20

PK_COUNT = 3


@pytest.fixture(scope="module")
def pk_swapcoins():
    return [ERC20() for i in range(PK_COUNT)]


@pytest.fixture(scope="module")
def pk_swaps(Stableswap, pk_swapcoins, stable, deployer, agg_stable):
    swap_list = []
    for i in range(PK_COUNT):
        coin = pk_swapcoins[i]
        rate_mul = [10 ** (36 - coin.decimals()), 10 ** (36 - stable.decimals())]
        swap = Stableswap.deploy(
            f"PegPool {i+1}", f"PP{i+1}", [coin, stable], rate_mul, 50, 1000000, {"from": deployer}
        )
        agg_stable.add_price_pair(swap, {"from": deployer})
        swap_list.append(swap)
    return swap_list


@pytest.fixture(scope="module")
def peg_keepers(PegKeeper, pk_swaps, core, stable, deployer, regulator, controller):
    pk_list = []
    for swap in pk_swaps:
        peg_keeper = PegKeeper.deploy(
            core, regulator, controller, stable, swap, 2 * 10**4, {"from": deployer}
        )
        pk_list.append(peg_keeper)

    return pk_list


@pytest.fixture(scope="module")
def pk(peg_keepers):
    return peg_keepers[0]


@pytest.fixture(scope="module")
def swap(pk_swaps):
    return pk_swaps[0]


@pytest.fixture(scope="module")
def coin(pk_swapcoins):
    return pk_swapcoins[0]
