from brownie import network


class ConnectionManager:
    """
    Context manager to simplify switching between networks in brownie.
    """

    def __init__(self, network_name):
        self.previous_network = network.show_active()
        self.new_network = network_name

    def __enter__(self):
        self.reconnect(self.new_network)

    def __exit__(self, exc_type, exc_value, traceback):
        self.reconnect(self.previous_network)

    def reconnect(self, network_name):
        if network.show_active() != network_name:
            if network.is_connected():
                network.disconnect()
            if network_name:
                network.connect(network_name)
