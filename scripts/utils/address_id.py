def get_address_identifier(id_string: str) -> bytes:
    """
    Generate a bytes32 identifier for use with `DFMProtocolCore.getAddress`.
    """
    return id_string.encode().hex().ljust(64, "0")
