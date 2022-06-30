from copyreg import constructor
from starknet_py.net.client import Client
from starknet_py.contract import Contract
from starknet_py.net.networks import TESTNET
from starknet_py.net import AccountClient
from starknet_py.net.models import StarknetChainId
import requests
import asyncio
import os

localhost_url = "http://127.0.0.1:5000/"


async def first_call(contract):
    try:
        await contract.functions["calc_abr"].invoke(max_fee=5000)
        print("Succesfully called the contract the first time")
    except:
        print("Error in calling the contract the first time")


async def second_call(contract):
    try:
        result = await contract.functions["calc_abr"].invoke(max_fee=5000)
        print(result)
        print("Succesfully called the contract the second time")
    except:
        print("Error in calling the contract before 8 hours")


async def third_call(contract):
    try:
        await contract.functions["calc_abr"].invoke(max_fee=5000)
        print("Succesfully called the contract the third time")
    except:
        print("Error in calling the contract after 8 hours")


async def forward_time():
    try:
        requests.post(localhost_url+"increase_time",
                      json={"time": 28800})
        print("Successfully forwarded the time by 8 hours")
    except:
        print("Couldn't forward the time")


async def main():
    os.chdir('./contracts')
    with open("Test.cairo", 'r') as f:
        test_file_code = f.read()

    acc_client = await AccountClient.create_account(private_key=0x2b52bcda21ba4462b45159fd908e7dc5, net=TESTNET, chain=StarknetChainId.TESTNET)

    test_contract_result = await Contract.deploy(
        client=acc_client, compilation_source=test_file_code
    )

    await test_contract_result.wait_for_acceptance()

    test_contract = test_contract_result.deployed_contract

    result = await test_contract.functions["calc_abr"].invoke(5, auto_estimate=True)
    await result.wait_for_acceptance()
    # result1 = await test_contract.functions["calc_abr"].invoke(1, max_fee=5000)
    # await result1.wait_for_acceptance()
    # await first_call(test_contract)
    # await second_call(test_contract)
    # await forward_time()
    # await third_call(test_contract)

asyncio.run(main())
