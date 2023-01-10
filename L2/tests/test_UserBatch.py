import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import ContractIndex, ManagerAction, assert_revert
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2

base_user_pub_key = 0x1111111111


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
    test_user_batch = await starknet_service.deploy(ContractType.TestUserBatch, [registry.contract_address, 1])

    # Give necessary permissions
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageMarkets, True])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])

    # Add contracts to registry
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountDeployer, 1, admin1.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountRegistry, 1, account_registry.contract_address])

    return adminAuth, test_user_batch, account_registry, admin1, admin2


@pytest.mark.asyncio
async def test_add_address_to_account_registry(adminAuth_factory):
    _, _, account_registry, admin1, _ = adminAuth_factory

    for i in range(16):
        await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [base_user_pub_key + i])


async def test_fetch_batches(adminAuth_factory):
    _, test_user_batch, _, admin1, _ = adminAuth_factory

    await signer1.send_transaction(admin1, test_user_batch.contract_address, 'begin_batch_calls', [])

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 5
    assert res.call_info.retdata[2:] == [
        x+base_user_pub_key for x in range(5)]

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 5
    assert res.call_info.retdata[2:] == [
        x+5+base_user_pub_key for x in range(5)]

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 5
    assert res.call_info.retdata[2:] == [
        x+10+base_user_pub_key for x in range(5)]

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 1
    assert res.call_info.retdata[2:] == [15+base_user_pub_key]

    await assert_revert(
        signer1.send_transaction(
            admin1, test_user_batch.contract_address, 'get_current_batch', []),
        "TestUserBatch: Invalid batch id"
    )


async def test_fetch_batches_2(adminAuth_factory):
    _, test_user_batch, _, admin1, _ = adminAuth_factory

    await signer1.send_transaction(admin1, test_user_batch.contract_address, 'set_no_of_users_per_batch', [7])

    current_no_of_users_per_batch_query = await test_user_batch.get_no_of_users_per_batch().call()
    assert current_no_of_users_per_batch_query.result.no_of_users == 7

    await signer1.send_transaction(admin1, test_user_batch.contract_address, 'begin_batch_calls', [])

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 7
    assert res.call_info.retdata[2:] == [
        x+base_user_pub_key for x in range(7)]

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 7
    assert res.call_info.retdata[2:] == [
        x+7+base_user_pub_key for x in range(7)]

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 2
    assert res.call_info.retdata[2:] == [
        x+14+base_user_pub_key for x in range(2)]

    await assert_revert(
        signer1.send_transaction(
            admin1, test_user_batch.contract_address, 'get_current_batch', []),
        "TestUserBatch: Invalid batch id"
    )


async def test_fetch_batches_3(adminAuth_factory):
    _, test_user_batch, account_registry, admin1, _ = adminAuth_factory

    for i in range(3):
        await signer1.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [base_user_pub_key + i + 16])

    await signer1.send_transaction(admin1, test_user_batch.contract_address, 'set_no_of_users_per_batch', [8])

    current_no_of_users_per_batch_query = await test_user_batch.get_no_of_users_per_batch().call()
    assert current_no_of_users_per_batch_query.result.no_of_users == 8

    await signer1.send_transaction(admin1, test_user_batch.contract_address, 'begin_batch_calls', [])

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 8
    assert res.call_info.retdata[2:] == [
        x+base_user_pub_key for x in range(8)]

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 8
    assert res.call_info.retdata[2:] == [
        x+8+base_user_pub_key for x in range(8)]

    res = await signer1.send_transaction(admin1, test_user_batch.contract_address, 'get_current_batch', [])
    assert res.call_info.retdata[1] == 3
    assert res.call_info.retdata[2:] == [
        x+16+base_user_pub_key for x in range(3)]

    await assert_revert(
        signer1.send_transaction(
            admin1, test_user_batch.contract_address, 'get_current_batch', []),
        "TestUserBatch: Invalid batch id"
    )
