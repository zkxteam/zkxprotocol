import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType, AccountFactory

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)

L1_dummy_address = 0x01234567899876543210


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)

    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    return adminAuth, account_registry, admin1, admin2


@pytest.mark.asyncio
async def test_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [str_to_felt("123")])
    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [str_to_felt("456")])

    fetched_account_registry = await account_registry.get_account_registry().call()
    assert fetched_account_registry.result.account_registry[0] == str_to_felt(
        "123")
    assert fetched_account_registry.result.account_registry[1] == str_to_felt(
        "456")

    isPresent = await account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 1
    isPresent = await account_registry.is_registered_user(str_to_felt("456")).call()
    assert isPresent.result.present == 1


@pytest.mark.asyncio
async def test_remove_address_from_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, account_registry.contract_address, 'remove_from_account_registry', [0])

    fetched_account_registry = await account_registry.get_account_registry().call()
    assert fetched_account_registry.result.account_registry[0] == str_to_felt(
        "456")

    isPresent = await account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 0


@pytest.mark.asyncio
async def test__unauthorized_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    assert_revert(lambda: signer2.send_transaction(
        admin2, account_registry.contract_address, 'add_to_account_registry', [str_to_felt("1234")]))


@pytest.mark.asyncio
async def test_add_address_to_account_registry_duplicate(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [str_to_felt("456")])
    fetched_account_registry = await account_registry.get_account_registry().call()
    assert fetched_account_registry.result.account_registry == [3421494]
