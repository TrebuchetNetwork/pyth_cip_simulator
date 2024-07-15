# Trebuchet Validator - Pyth CIP Simulator

Welcome to the Trebuchet Validator repository! This project aims to enhance the pricing consensus protocol within the Pyth Network by enabling transparent and verifiable simulations accessible to all stakeholders, including data publishers.

## Overview

Our system leverages the Pyth Network's RPC to simulate price consensus and reward distribution among publishers. The initial implementation includes Python code designed to facilitate these simulations and support future development of a smart contract extension in Rust.

## Features

- **Data Handling**: Capture and store publisher data snapshots from the Pyth network.
- **Simulation Process**: Compare current and historical prices to simulate transactions.
- **Reward Distribution**: Handle incentive distributions using a centralized model.
- **Staking Mechanisms**: Propose a closed-loop delegated staking system for enhanced interaction.

## Getting Started

### Prerequisites

- Python 3.7+
- Pyth Client Library

### Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/TrebuchetNetwork/pyth_cip_simulator.git
cd pyth_cip_simulator
pip install -r requirements.txt
```

## Running the Simulator

To run the Pyth CIP simulator, execute the following command:



```bash
python trebuchet_validator.py
```

## Configuration Parameters
The script includes several configurable parameters:

tracking_length: Number of data points to track per publisher (default: 10).
interval_duration: Seconds between polls to the Pyth network (default: 4).
initial_stake: Initial stake amount for each publisher (default: 100).
symbol_for_observation: The symbol to observe (default: "Crypto.BTC/USD").


# Exponential Penalty Function
The penalty for prediction errors is calculated using an exponential function:

```python
def exponential_penalty_function(outlier_number, total_price_components):
    a = 0.0000001
    b = 10 ** (2 / total_price_components)
    y = a * (b ** (outlier_number - 1))
    return y
```

a: The base factor for the penalty (default: 0.0000001).
b: The exponential growth factor (default: 10 ** (2 / total_price_components)).


# Directional Deviation Forgiveness Factor
The system incorporates a forgiveness factor of 0.5, allowing for some leniency in cases where the predicted direction of price movement is correct but the magnitude is off.

# Transaction Logging
All stake adjustments are logged in a transaction file, providing a transparent record of changes. An example log entry is:



Transferred $X.XX from Publisher A to Publisher B. Max Bid at T0: $XX.XX, Min Bid at T0: $XX.XX. Current Aggregate Price: $XX.XX, Initial Aggregate Price: $XX.XX, Penalty Exponent X.XXXXXX

## Contribution
We welcome contributions from the community. Please fork the repository, make your changes, and submit a pull request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Feedback
We value your feedback and invite the community to engage with this project. Please open an issue or submit a pull request if you have any suggestions or improvements.
