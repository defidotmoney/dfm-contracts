import brownie


def test_read_write_responses(chained_oracle, dummy_oracle, deployer):
    calldata_view = dummy_oracle.price.encode_input()
    calldata_write = dummy_oracle.price_w.encode_input()
    chained_oracle.addCallPath(
        [(dummy_oracle, 18, True, calldata_view, calldata_write)], {"from": deployer}
    )

    # diferent responses for `price` and `price_w` would be bad in prod, but for testing it's cool
    dummy_oracle.set_price_w(2000 * 10**18, {"from": deployer})

    assert chained_oracle.price() == 3000 * 10**18
    assert chained_oracle.price_w.call() == 2000 * 10**18


def test_read_write_responses_callpath_getters(chained_oracle, dummy_oracle, deployer):
    calldata_view = dummy_oracle.price.encode_input()
    calldata_write = dummy_oracle.price_w.encode_input()
    chained_oracle.addCallPath(
        [(dummy_oracle, 18, True, calldata_view, calldata_write)], {"from": deployer}
    )

    dummy_oracle.set_price_w(2000 * 10**18, {"from": deployer})

    assert chained_oracle.getCallPathResult(0) == 3000 * 10**18
    assert chained_oracle.getCallPathResultWrite.call(0) == 2000 * 10**18


def test_add_call_path_calls_write(chained_oracle, dummy_oracle, deployer):
    calldata_view = dummy_oracle.price.encode_input()
    calldata_write = dummy_oracle.price_w.encode_input()
    tx = chained_oracle.addCallPath(
        [(dummy_oracle, 18, True, calldata_view, calldata_write)], {"from": deployer}
    )

    assert "PriceWrite" in tx.events


def test_add_call_path_different_responses(chained_oracle, dummy_oracle, deployer):
    calldata_view = dummy_oracle.price.encode_input()
    calldata_write = dummy_oracle.price_w.encode_input()
    dummy_oracle.set_price_w(2000 * 10**18, {"from": deployer})

    with brownie.reverts("DFM: view != write"):
        chained_oracle.addCallPath(
            [(dummy_oracle, 18, True, calldata_view, calldata_write)], {"from": deployer}
        )
