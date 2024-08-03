import brownie
import pytest


def test_on_flashloan_caller(zap, stable, alice):
    with brownie.reverts("DFM: Invalid caller"):
        zap.onFlashLoan(zap, stable, 0, 0, b"", {"from": alice})


def test_on_flashloan_initiator(zap, stable, alice):
    with brownie.reverts("DFM: Invalid initiator"):
        zap.onFlashLoan(alice, stable, 0, 0, b"", {"from": stable})
