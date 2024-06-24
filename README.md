# dfm-contracts

Smart contracts used within the Defi.Money protocol.

Core protocol based on Curve Finance's [crvUSD](https://github.com/curvefi/curve-stablecoin).

## Organization

### Smart Contracts
* [`contracts/base/`](contracts/base): Shared libraries and abstract bases, and the core protocol ownership logic.
* [`contracts/bridge/`](contracts/bridge): Contracts related to cross-chain functionality (powered by LayerZero).
* [`contracts/cdp/`](contracts/cdp): Core protocol functionality, based on Curve Finance's crvUSD.
* [`contracts/periphery/`](contracts/periphery): Periphery contracts such as hooks, zaps and combined views.
* [`contracts/testing/`](contracts/testing): Contracts used for unit testing. Not a part of the protocol.

### Deployment
* [`deployments/config`](deployments/config): Configuration files for deploying to different networks.
* [`deployments/logs`](deployments/logs): Log files containing addresses of completed deployments.

### Scripts
* [`scripts/deploy_local.py`](scripts/deploy_local.py): Script for deploying on a local hardhat network.
* [`scripts/deploy_mainnet.py`](scripts/deploy_mainnet.py): Script for deploying to a production network (or forked environment).

### Tests
* [`tests/brownie`](tests/brownie): Brownie test suite.
* [`tests/titanoboa`](tests/titanoboa): Titanoboa test suite.

## Setup

### Requirements

- python version 3.10 or later, `python3-venv`, `python3-dev`
- npm version 7 or later

### Installation

1. Install the node.js dependencies ( Hardhat and LayerZero contracts ). This should be done in the `dfm-contracts` root directory.

   ```bash
   npm install
   ```

2. Within the `dfm-contracts` root directory, create a [`venv`](https://docs.python.org/3/library/venv.html) and install the python dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Initialize the virtual environment to interact with the project. This must be done at the start of each new terminal session.

   ```bash
   source venv/bin/activate
   ```

## Deployment

### To a Local Network

To run [`scripts/deploy_local.py`](scripts/deploy_local.py) and deploy all contracts on a local hardhat network:

```bash
brownie run deploy_local -i
```

The brownie console will open once deployment has finished. The hardhat session will persist as long as brownie remains open.

### To Mainnet

Mainnet deployment configurations are handled by YAML files within [`deployments/config`](deployments/config). Common settings are first loaded from [`default.yaml`](deployments/config/default.yaml), and then network-specific settings are loaded over top. Each network's configuration filename is the same as it's brownie network name, e.g. for Fantom the filename would be `ftm-main.yaml`.

Before the actual deployment it is recommended to do a test run on a forked mainnet. If you deploy to a network ending in `-fork`, the related mainnet deploy config is used.

To run [`scripts/deploy_mainnet.py`](scripts/deploy_mainnet.py):


```bash
brownie run deploy_mainnet --network [network name] -i
```

The brownie console will open once deployment has finished.

Addresses of the core smart contracts will be written to a YAML file within [`deployments/logs`](deployments/logs). If this is the final deployment, remember to commit this log file to git.

Note that the script does not verify source codes with Etherscan (API source verification is not supported for Vyper). You must manually verify once deployment is finished.

## Tests

Unit testing is done with a mix of `brownie` and `titanoboa`.

To run the [`brownie`](https://github.com/eth-brownie/brownie) tests:

```bash
brownie test
```

To run the [`titanoboa`](https://github.com/vyperlang/titanoboa) tests:

```bash
pytest tests/titanoboa
```

Note that `brownie` and `titanoboa` do not play nicely together - attempting to run all tests at once will result in unexpected failures.

## Audits

Components of this codebase have undergone multiple audits by different firms. Audit reports are published on our [Github audit repo](https://github.com/defidotmoney/audits) as they are completed.

* `contracts/cdp/` : audited by [ChainSecurity](https://chainsecurity.com/), June 2024 - [view report](https://github.com/defidotmoney/audits/blob/main/audits/Core%20Protocol%20-%20ChainSecurity%20-%20June%202024.pdf)
* `contracts/cdp/` : audited by [MixBytes](https://mixbytes.io/), June 2024 - [view report](https://github.com/defidotmoney/audits/blob/main/audits/Core%20Protocol%20-%20MixBytes%20-%20June%202024.pdf)
* `contracts/cdp/oracles/ChainlinkEMA.sol` : audited by [Bail Security](https://bailsec.io/), June 2024 - [view report](https://github.com/defidotmoney/audits/blob/main/audits/ChainlinkEMA%20-%20BailSec%20-%20June%202024.pdf)

## License

Unless otherwise noted, code in this repository is copyrighted (c) by Curve.Fi, 2020-2024 - [All rights reserved](LICENSE). Used by Defi.Money with permission.
