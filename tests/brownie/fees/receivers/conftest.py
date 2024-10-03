import pytest


@pytest.fixture(scope="module")
def votium(VotiumMock, stable, deployer):
    return VotiumMock.deploy(stable, {"from": deployer})


@pytest.fixture(scope="module")
def votemarket(VoteMarketMock, stable, deployer):
    return VoteMarketMock.deploy(stable, {"from": deployer})


@pytest.fixture(scope="module")
def votium_recv(VotiumFeeReceiver, core, votium, stable, mock_endpoint, deployer, alice, bob):
    return VotiumFeeReceiver.deploy(
        core, stable, votium, mock_endpoint, bob, [(alice, 3), (bob, 7)], {"from": deployer}
    )


@pytest.fixture(scope="module")
def votemarket_recv(VoteMarketFeeReceiver, core, stable, fee_agg, votemarket, alice, bob, deployer):
    return VoteMarketFeeReceiver.deploy(
        core, stable, fee_agg, votemarket, [(alice, 3), (bob, 7)], [], {"from": deployer}
    )
