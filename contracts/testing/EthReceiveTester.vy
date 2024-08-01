#pragma version 0.3.10
# used to send ETH to payable functions on other contracts
# reverts if the contract attempts to send any ETH back

@payable
@external
def receive_eth():
    pass
