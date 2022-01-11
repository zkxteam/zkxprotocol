"""Command to deploy StarkNet smart contracts."""
import os
import re
import subprocess
import json

CONTRACTS_DIRECTORY = "../contracts"
BUILD_DIRECTORY = "../artifacts"
ABIS_DIRECTORY = f"{BUILD_DIRECTORY}/abis"
NODE_FILENAME = "node.json"

def _get_gateway():
    """Get the StarkNet node details."""
    try:
        with open(NODE_FILENAME, "r") as f:
            gateway = json.load(f)
            return gateway

    except FileNotFoundError:
        with open(NODE_FILENAME, "w") as f:
            f.write('{"localhost": "http://localhost:5000/"}')


GATEWAYS = _get_gateway()

def deploy_command(contract_name, arguments, network, alias, overriding_path=None):
    """Deploy StarkNet smart contracts."""
    print(f"Deploying {contract_name}")

    base_path = (
        overriding_path if overriding_path else (BUILD_DIRECTORY, ABIS_DIRECTORY)
    )
    contract = f"{base_path[0]}/{contract_name}.json"
    abi = f"{base_path[1]}/{contract_name}.json"

    command = ["starknet", "deploy", "--contract", contract]

    if len(arguments) > 0:
        command.append("--inputs")
        command.extend([argument for argument in arguments])

    if network == "mainnet":
        os.environ["STARKNET_NETWORK"] = "alpha-mainnet"
    elif network == "goerli":
        os.environ["STARKNET_NETWORK"] = "alpha-goerli"
    else:
        command.append(f"--gateway_url={GATEWAYS.get(network)}")

    output = subprocess.check_output(command)
    address, tx_hash = parse_deployment(output)
    print(f"Deployment of {contract_name} successfully sent at {address}")
    print(f"Transaction hash: {tx_hash}\n")

    return address
    # deployments.register(address, abi, network, alias)


def parse_deployment(x):
    """Extract information from deployment command."""
    # address is 64, tx_hash is 64 chars long
    address, tx_hash = re.findall("0x[\\da-f]{1,64}", str(x))
    return address, tx_hash
