import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0, 1, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0, 1, 0]
    )

    adminAuth = await starknet.deploy(
        "contracts/AdminAuth.cairo",
        constructor_calldata=[
            admin1.contract_address,
            admin2.contract_address
        ]
    )

    registry = await starknet.deploy(
        "contracts/AuthorizedRegistry.cairo",
        constructor_calldata=[
            adminAuth.contract_address
        ]
    )

    account_registry = await starknet.deploy(
        "contracts/AccountRegistry.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    return adminAuth, account_registry, admin1, admin2


@pytest.mark.asyncio
async def test_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [str_to_felt("123")])
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [str_to_felt("456")])

    fetched_account_registry = await account_registry.get_account_registry().call()
    print(fetched_account_registry.result.account_registry)
    assert fetched_account_registry.result.account_registry[0] == str_to_felt("123")
    assert fetched_account_registry.result.account_registry[1] == str_to_felt("456")

    isPresent = await account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 1
    isPresent = await account_registry.is_registered_user(str_to_felt("456")).call()
    assert isPresent.result.present == 1

@pytest.mark.asyncio
async def test_remove_address_from_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, account_registry.contract_address, 'remove_from_account_registry', [0])

    fetched_account_registry = await account_registry.get_account_registry().call()
    print(fetched_account_registry.result.account_registry)
    assert fetched_account_registry.result.account_registry[0] == str_to_felt("456")

    isPresent = await account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 0