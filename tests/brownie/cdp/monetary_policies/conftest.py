import pytest


@pytest.fixture(scope="module")
def agg_policy(AggMonetaryPolicy, core, agg_stable, controller, deployer):
    return AggMonetaryPolicy.deploy(
        core, controller, agg_stable, 4431822020, 7 * 10**15, 10**17, {"from": deployer}
    )
