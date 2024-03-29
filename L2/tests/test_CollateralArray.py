from copyreg import constructor
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, str_to_felt, MAX_UINT256, from64x61, to64x61
from helpers import StarknetService, ContractType, AccountFactory
from dummy_signers import signer1, signer2, signer3

BTC_ID = str_to_felt("32f0406jz7qj8")
ETH_ID = str_to_felt("65ksgn23nv")
USDC_ID = str_to_felt("fghj3am52qpzsib")
UST_ID = str_to_felt("yjk45lvmasopq")
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
DOGE_ID = str_to_felt("jdi2i8621hzmnc7324o")
TSLA_ID = str_to_felt("i39sk1nxlqlzcee")

L1_dummy_address = 0x01234567899876543210


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
    admin1 = await starknet_service.deploy(ContractType.Account, [
        signer1.public_key
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        signer2.public_key
    ])

    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])

    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )
    alice = await account_factory.deploy_ZKX_account(signer3.public_key)

    return alice, admin1


@pytest.mark.asyncio
async def test_should_set_collaterals(adminAuth_factory):
    alice, admin1 = adminAuth_factory

    alice_balance_usdc = to64x61(5500)
    alice_balance_ust = to64x61(100)

    await signer1.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance_usdc])
    await signer1.send_transaction(admin1, alice.contract_address, 'set_balance', [UST_ID, alice_balance_ust])

    alice_curr_balance_usdc_before = await alice.get_balance(USDC_ID).call()
    alice_curr_balance_ust_before = await alice.get_balance(UST_ID).call()
    assert from64x61(alice_curr_balance_usdc_before.result.res) == 5500
    assert from64x61(alice_curr_balance_ust_before.result.res) == 100

    alice_list = await alice.return_array_collaterals().call()
    assert from64x61(
        alice_list.result.array_list[1].balance) == from64x61(alice_balance_usdc)
    assert from64x61(
        alice_list.result.array_list[2].balance) == from64x61(alice_balance_ust)
