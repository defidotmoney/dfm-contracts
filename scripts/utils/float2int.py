from brownie import Fixed


def to_int(value, precision=18):
    value = Fixed(str(value))
    return int(value * 10**precision)
