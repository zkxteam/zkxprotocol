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
signer4 = Signer(123456789987654324)
signer5 = Signer(123456789987654325)

L1_dummy_address = 0x01234567899876543210
PRIME = 3618502788666131213697322783095070105623107215331596699973092056135872020481


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    user1 = await account_factory.deploy_account(signer3.public_key)
    user2 = await account_factory.deploy_account(signer4.public_key)
    user3 = await account_factory.deploy_account(signer5.public_key) 
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])


    return adminAuth, admin1, admin2, user1, user2, user3


@pytest.mark.asyncio
async def test_get_admin_mapping(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 0).call()
    assert execution_info.result.allowed == 1

    execution_info1 = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info1.result.allowed == 0


@pytest.mark.asyncio
async def test_get_min_num_admins(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory
    result = await adminAuth.get_min_num_admins().call()
    assert result.result.res == 2


@pytest.mark.asyncio
async def test_set_min_num_admins(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory
    # cannot set negative number for min admins
    await assert_revert(signer1.send_transaction(admin1, adminAuth.contract_address, 'set_min_num_admins', [-1%PRIME]), reverted_with="AdminAuth: Number of min admin should be >=2")
    # cannot set any number less than 2
    await assert_revert(signer1.send_transaction(admin1, adminAuth.contract_address, 'set_min_num_admins', [1]), reverted_with="AdminAuth: Number of min admin should be >=2")
    # only admin can call this function
    await assert_revert(signer3.send_transaction(user1, adminAuth.contract_address, 'set_min_num_admins', [2]), reverted_with="AdminAuth: Unauthorized call for set_min_num_admins")

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'set_min_num_admins', [3])

    result = await adminAuth.get_min_num_admins().call()
    assert result.result.res == 3

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'set_min_num_admins', [2])

    result = await adminAuth.get_min_num_admins().call()
    assert result.result.res == 2


@pytest.mark.asyncio
async def test_update_admin_mapping_non_admin(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 1, 1])

    execution_info = await adminAuth.get_admin_mapping(user1.contract_address, 1).call()
    assert execution_info.result.allowed == 1

    # setting permission which is same as existing permission should also work - no processing done internally
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 1, 1])

    execution_info = await adminAuth.get_admin_mapping(user1.contract_address, 1).call()
    assert execution_info.result.allowed == 1

    # user1 should not have been granted any other permission
    execution_info = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info.result.allowed == 0


@pytest.mark.asyncio
async def test_update_admin_mapping_same_approval(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user2.contract_address, 0, 1])

    execution_info1 = await adminAuth.get_admin_mapping(user2.contract_address, 0).call()
    assert execution_info1.result.allowed == 0

    # if same admin gives another approval then transaction will revert
    await assert_revert(signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user2.contract_address, 0, 1]), reverted_with="AdminAuth: Both approvers cannot be the same")

    execution_info1 = await adminAuth.get_admin_mapping(user2.contract_address, 0).call()
    assert execution_info1.result.allowed == 0


@pytest.mark.asyncio
async def test_update_admin_mapping_no_permission(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    # non-admins cannot update admin mapping
    await assert_revert(signer3.send_transaction(user1, adminAuth.contract_address,
                                                 'update_admin_mapping', [user1.contract_address, 0, 1]), reverted_with="AdminAuth: Unauthorized call for admin mapping updation")


@pytest.mark.asyncio
async def test_update_admin_mapping_incorrect_value(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    # only value of 0/1 can be used as value for permission
    await assert_revert(signer1.send_transaction(admin1, adminAuth.contract_address,
                                                 'update_admin_mapping', [user1.contract_address, 2, 2]))


@pytest.mark.asyncio
async def test_add_admin_mapping_admin(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 2
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 0, 1])

    execution_info1 = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info1.result.allowed == 0

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 2

    await signer2.send_transaction(admin2, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 0, 1])

    execution_info2 = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info2.result.allowed == 1

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 3


@pytest.mark.asyncio
async def test_remove_admin_mapping_admin(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 3
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 0, 0])

    execution_info1 = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info1.result.allowed == 1

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 3

    # if same admin gives 2 calls for removal then transaction will revert
    await assert_revert(signer1.send_transaction(admin1, adminAuth.contract_address,'update_admin_mapping',[user1.contract_address, 0, 0]), reverted_with="AdminAuth: Admin cannot approve twice")

    await signer2.send_transaction(admin2, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 0, 0])

    execution_info2 = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info2.result.allowed == 0

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 2


@pytest.mark.asyncio
async def test_min_admin_threshold_breach(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 2

    # if removal results in less than min num of admins then transaction will revert
    await assert_revert(signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin2.contract_address, 0, 0]), reverted_with="AdminAuth: Minimum number of admins not satisfied")


@pytest.mark.asyncio
async def test_update_admin_mapping_revoke(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user3.contract_address, 1, 1])

    execution_info1 = await adminAuth.get_admin_mapping(user3.contract_address, 1).call()
    assert execution_info1.result.allowed == 1

    await signer2.send_transaction(admin2, adminAuth.contract_address, 'update_admin_mapping', [user3.contract_address, 1, 0])

    execution_info2 = await adminAuth.get_admin_mapping(user3.contract_address, 1).call()
    assert execution_info2.result.allowed == 0


@pytest.mark.asyncio
async def test_readd_admin_mapping_admin(adminAuth_factory):
    adminAuth, admin1, admin2, user1, user2, user3 = adminAuth_factory

    # re-adding a removed admin will still require 2 approvals to update admin mapping
    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 2
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 0, 1])

    execution_info1 = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info1.result.allowed == 0

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 2

    await signer2.send_transaction(admin2, adminAuth.contract_address, 'update_admin_mapping', [user1.contract_address, 0, 1])

    execution_info2 = await adminAuth.get_admin_mapping(user1.contract_address, 0).call()
    assert execution_info2.result.allowed == 1

    result = await adminAuth.get_current_total_admins().call()
    assert result.result.res == 3
