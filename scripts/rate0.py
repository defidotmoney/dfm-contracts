# convert between human-readable APR and `rate0` for use in monetary policy


def apr_to_rate0(apr):
    rate0 = 10**18 * ((apr + 1) ** (1 / 31536000) - 1)
    return int(rate0)


def rate0_to_apr(rate0):
    apr = (1 + rate0 / 10**18) ** 31536000 - 1
    return apr
