# dfm-contracts

Smart contracts used within the Defi.Money protocol.

Core protocol based on Curve Finance's [crvUSD](https://github.com/curvefi/curve-stablecoin).

## Organization

* [`contracts/base/`](contracts/base): Shared libraries and abstract bases, and the core protocol ownership logic.
* [`contracts/bridge/`](contracts/bridge): Contracts related to cross-chain functionality (powered by LayerZero).
* [`contracts/cdp/`](contracts/cdp): Core protocol functionality, based on Curve Finance's crvUSD.
* [`contracts/periphery/`](contracts/periphery): Periphery contracts such as hooks, zaps and combined views.
* [`contracts/testing/`](contracts/testing): Contracts used for unit testing. Not a part of the protocol.

## Setup

#### Requirements

- python version 3.10 or later, `python3-venv`, `python3-dev`
- npm version 7 or later

#### Installation

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

## Deploying to a Local Network

To run [`scripts/deploy_local.py`](scripts/deploy_local.py) and deploy all contracts on a local hardhat network:

```bash
brownie run deploy_local -i
```

The brownie console will open once deployment has finished. The hardhat session will persist as long as brownie remains open.

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

Components of this codebase have undergone multiple audits by different firms. Audit reports are published on [Github](https://github.com/defidotmoney/audits) as they are completed.

## License

Unless otherwise noted, code in this repository is copyrighted (c) by Curve.Fi, 2020-2024 - [All rights reserved](LICENSE). Used by Defi.Money with permission.
