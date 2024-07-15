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
