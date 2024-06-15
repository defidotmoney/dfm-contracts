# convert between human-readable APY and `rate0` for use in monetary policy


def apy_to_rate0(apy):
    """
    Convert a human-readable APY into a `rate0` value for use within a
    monetary policy deployment.
    """
    rate0 = 10**18 * ((apy + 1) ** (1 / 31536000) - 1)
    return int(rate0)


def rate0_to_apy(rate0):
    """
    Convert a `rate0` value from a monetary policy deployment into a
    human-readable APY.
    """
    apy = (1 + rate0 / 10**18) ** 31536000 - 1
    return apy
