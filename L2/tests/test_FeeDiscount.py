import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, from64x61, to64x61, assert_event_emitted
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    user1 = await account_factory.deploy_ZKX_account(signer3.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 6, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [3, 1, feeDiscount.contract_address])

    return adminAuth, admin1, admin2, user1, feeDiscount

@pytest.mark.asyncio
async def test_add_token(adminAuth_factory):
    adminAuth, admin1, admin2, user1, feeDiscount = adminAuth_factory

    tx_exec_info=await signer1.send_transaction(admin1, feeDiscount.contract_address, 'increment_governance_tokens', [user1.contract_address, 10])

    execution_info = await feeDiscount.get_user_tokens(user1.contract_address).call()
    result = execution_info.result.value
    assert result == 10

    assert_event_emitted(
        tx_exec_info,
        from_address = feeDiscount.contract_address,
        name = 'tokens_added',
        data=[
            user1.contract_address,
            10,
            0
        ]
    )

@pytest.mark.asyncio
async def test_add_token_unauthorized(adminAuth_factory):
    adminAuth, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await assert_revert(signer2.send_transaction(admin2, feeDiscount.contract_address, 'increment_governance_tokens', [user1.contract_address, 10]))

@pytest.mark.asyncio
async def test_remove_token(adminAuth_factory):
    adminAuth, admin1, admin2, user1, feeDiscount = adminAuth_factory

    tx_exec_info=await signer1.send_transaction(admin1, feeDiscount.contract_address, 'decrement_governance_tokens', [user1.contract_address, 5])

    execution_info = await feeDiscount.get_user_tokens(user1.contract_address).call()
    result = execution_info.result.value
    assert result == 5

    assert_event_emitted(
        tx_exec_info,
        from_address = feeDiscount.contract_address,
        name = 'tokens_removed',
        data=[
            user1.contract_address,
            5,
            10
        ]
    )

@pytest.mark.asyncio
async def test_remove_token_unauthorized(adminAuth_factory):
    adminAuth, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await assert_revert(signer2.send_transaction(admin2, feeDiscount.contract_address, 'decrement_governance_tokens', [user1.contract_address, 10]))

@pytest.mark.asyncio
async def test_remove_token_more_than_balance(adminAuth_factory):
    adminAuth, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await assert_revert(signer1.send_transaction(admin1, feeDiscount.contract_address, 'decrement_governance_tokens', [user1.contract_address, 20]))