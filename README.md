# dfm-core

Core protocol contracts for defi.money. Based on Curve Finance's crvUSD.

## Setup

#### Requirements

- python version 3.10 or later, `python3-venv`, `python3-dev`
- npm version 7 or later

#### Installation

1. Install the node.js dependencies this can be done in the `dfm-core` root directory

   ```bash
   npm install
   ```

2. Within the `dfm-core` root directory, create a [`venv`](https://docs.python.org/3/library/venv.html) and install the python dependencies:

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

To run [`scripts/deploy.py`](scripts/deploy.py) and deploy all contracts on a local hardhat network:

```bash
brownie run deploy deploy_local -i
```

The brownie console will open once deployment has finished. The hardhat session will persist as long as brownie remains open.

## Tests

To run the [`brownie`](https://github.com/eth-brownie/brownie) tests:

```bash
brownie test
```

To run the [`titanoboa`](https://github.com/vyperlang/titanoboa) tests:

```bash
pytest tests/titanoboa
```

Note that `brownie` and `titanoboa` do not play nicely together - attempting to run all tests at once might cause weirdness.
