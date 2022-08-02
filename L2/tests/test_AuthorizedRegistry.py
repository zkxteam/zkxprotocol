import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType, AccountFactory

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)

L1_dummy_address = 0x01234567899876543210
L1_ZKX_dummy_address = 0x98765432100123456789


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1, L1_ZKX_dummy_address)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    user1 = await account_factory.deploy_account(signer3.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

    return adminAuth, registry, admin1, admin2, user1


@pytest.mark.asyncio
async def test_get_admin_mapping(adminAuth_factory):
    adminAuth, _, admin1, admin2, user1 = adminAuth_factory

    execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 3).call()
    assert execution_info.result.allowed == 1

    execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 3).call()
    assert execution_info1.result.allowed == 0


@pytest.mark.asyncio
async def test_modify_registry_by_admin(adminAuth_factory):
    adminAuth, registry, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, 123])

    execution_info = await registry.get_contract_address(1, 1).call()
    result = execution_info.result.address

    assert result == 123


@pytest.mark.asyncio
async def test_modify_registry_by_unauthorized(adminAuth_factory):
    adminAuth, registry, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer3.send_transaction(
        user1, registry.contract_address, 'update_contract_registry', [2, 1, 123]))

@pytest.mark.asyncio
async def test_modify_registry_by_admin_already_updated(adminAuth_factory):
    adminAuth, registry, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, 1234])

    execution_info = await registry.get_contract_address(1, 1).call()
    result = execution_info.result.address

    assert result == 123
