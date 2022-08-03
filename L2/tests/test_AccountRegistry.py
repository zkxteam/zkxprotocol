import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)

L1_dummy_address = 0x01234567899876543210
L1_ZKX_dummy_address = 0x98765432100123456789


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, L1_dummy_address, 0, 1, L1_ZKX_dummy_address]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, L1_dummy_address, 0, 1, L1_ZKX_dummy_address]
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

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    return adminAuth, account_registry, admin1, admin2

@pytest.mark.asyncio
async def test_remove_address_from_account_registry_empty(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await assert_revert(signer1.send_transaction(admin1, account_registry.contract_address, 'remove_from_account_registry', [0]))

@pytest.mark.asyncio
async def test_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x12345])
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x98765])

    array_length = await account_registry.get_registry_len().call()
    fetched_account_registry = await account_registry.get_account_registry(0, array_length.result.len).call()

    assert fetched_account_registry.result.account_registry[0] == 0x12345
    assert fetched_account_registry.result.account_registry[1] == 0x98765

    isPresent = await account_registry.is_registered_user(0x12345).call()
    assert isPresent.result.present == 1
    isPresent = await account_registry.is_registered_user(0x98765).call()
    assert isPresent.result.present == 1


@pytest.mark.asyncio
async def test_remove_address_from_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(admin1, account_registry.contract_address, 'remove_from_account_registry', [-2])
    )

    array_length_before = await account_registry.get_registry_len().call()

    await assert_revert(
        signer1.send_transaction(admin1, account_registry.contract_address, 'remove_from_account_registry', [array_length_before.result.len + 1])
    )

    await signer1.send_transaction(admin1, account_registry.contract_address, 'remove_from_account_registry', [0])
    array_length_after = await account_registry.get_registry_len().call()
    
    assert array_length_after.result.len == array_length_before.result.len - 1

    fetched_account_registry = await account_registry.get_account_registry(0, array_length_after.result.len).call()
    assert fetched_account_registry.result.account_registry[0] == 0x98765

    isPresent = await account_registry.is_registered_user(0x12345).call()
    assert isPresent.result.present == 0


@pytest.mark.asyncio
async def test__unauthorized_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await assert_revert(signer2.send_transaction(
        admin2, account_registry.contract_address, 'add_to_account_registry', [0x12345]))


@pytest.mark.asyncio
async def test_add_address_to_account_registry_duplicate(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    array_length_before = await account_registry.get_registry_len().call()
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x98765])
    array_length_after = await account_registry.get_registry_len().call()

    assert array_length_after.result.len == array_length_before.result.len 
    fetched_account_registry = await account_registry.get_account_registry(0, array_length_after.result.len).call()
    assert fetched_account_registry.result.account_registry == [0x98765]

@pytest.mark.asyncio
async def test_get_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory
    
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x12345])
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x67891])
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x23565])
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x98383])
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [0x31231])

    array_length = await account_registry.get_registry_len().call()
    assert array_length.result.len == 6

    await assert_revert(
        account_registry.get_account_registry(-1, 1).call()
    )

    await assert_revert(
        account_registry.get_account_registry(0, 0).call()
    )

    await assert_revert(
        account_registry.get_account_registry(0, -1).call()
    )

    fetched_account_registry_1 = await account_registry.get_account_registry(0, 1).call()
    assert fetched_account_registry_1.result.account_registry == [0x98765]

    fetched_account_registry_2 = await account_registry.get_account_registry(1, 1).call()
    assert fetched_account_registry_2.result.account_registry == [0x12345]

    fetched_account_registry_3 = await account_registry.get_account_registry(1, 3).call()
    assert fetched_account_registry_3.result.account_registry == [0x12345, 0x67891, 0x23565]

    fetched_account_registry_4 = await account_registry.get_account_registry(3, 3).call()
    assert fetched_account_registry_4.result.account_registry == [0x23565, 0x98383, 0x31231]

    fetched_account_registry_5 = await account_registry.get_account_registry(5, 1).call()
    assert fetched_account_registry_5.result.account_registry == [0x31231]

    fetched_account_registry_6 = await account_registry.get_account_registry(0, 6).call()
    assert fetched_account_registry_6.result.account_registry == [0x98765, 0x12345, 0x67891, 0x23565, 0x98383, 0x31231]



    




    


