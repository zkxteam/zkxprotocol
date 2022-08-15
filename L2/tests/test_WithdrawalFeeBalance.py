from copyreg import constructor
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, str_to_felt, assert_revert, to64x61, assert_event_emitted
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
dave_signer = Signer(123456789987654326)

ETH_ID = str_to_felt("65ksgn23nv")
USDC_ID = str_to_felt("fghj3am52qpzsib")

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    ### Deploy infrastructure (Part 1)
    admin1 = await starknet_service.deploy(ContractType.Account, [
        admin1_signer.public_key, 
        L1_dummy_address, 
        0, 
        1
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        admin2_signer.public_key, 
        L1_dummy_address, 
        0, 
        1
    ])
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])

    ### Deploy user accounts
    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )
    alice = await account_factory.deploy_account(alice_signer.public_key)
    bob = await account_factory.deploy_account(bob_signer.public_key)
    dave = await account_factory.deploy_account(dave_signer.public_key)

    ### Deploy infrastructure (Part 2)
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    withdrawFeeBalance = await starknet_service.deploy(ContractType.WithdrawalFeeBalance, [registry.contract_address, 1])

    # Access 1 allows adding assets
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # Add assets
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ETH_ID, 0, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[admin1.contract_address])
    
    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[admin2.contract_address])
    
    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[alice.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[bob.contract_address])

    return adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance

@pytest.mark.asyncio
async def test_update_withdrawal_fee_mapping(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory

    tx_exec_info=await alice_signer.send_transaction(alice, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [USDC_ID, 10])

    execution_info = await withdrawFeeBalance.get_total_withdrawal_fee(USDC_ID).call()
    assert execution_info.result.fee == 10

    assert_event_emitted(
        tx_exec_info,
        from_address = withdrawFeeBalance.contract_address,
        name = 'update_withdrawal_fee_mapping_called',
        data=[
            USDC_ID,
            10
        ]
    )

@pytest.mark.asyncio
async def test_update_withdrawal_fee_mapping_unauthorized(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory

    await assert_revert(dave_signer.send_transaction(dave, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [USDC_ID, 10]))


@pytest.mark.asyncio
async def test_update_withdrawal_fee_mapping_different_user(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory
    await alice_signer.send_transaction(alice, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [USDC_ID, 10])

    execution_info = await withdrawFeeBalance.get_total_withdrawal_fee(USDC_ID).call()
    assert execution_info.result.fee == 20

    await bob_signer.send_transaction(bob, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [USDC_ID, 10])

    execution_info = await withdrawFeeBalance.get_total_withdrawal_fee(USDC_ID).call()
    assert execution_info.result.fee == 30

@pytest.mark.asyncio
async def test_set_standard_fee(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory
    tx_exec_info=await admin1_signer.send_transaction(admin1, withdrawFeeBalance.contract_address, 'set_standard_withdraw_fee', [46116860184273880, USDC_ID])

    assert_event_emitted(
        tx_exec_info,
        from_address = withdrawFeeBalance.contract_address,
        name = 'set_standard_withdraw_fee_called',
        data=[
            46116860184273880,
            USDC_ID
        ]
    )

@pytest.mark.asyncio
async def test_set_standard_fee_non_collateral_system(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory
    await assert_revert(admin1_signer.send_transaction(admin1, withdrawFeeBalance.contract_address, 'set_standard_withdraw_fee', [0, ETH_ID]))

@pytest.mark.asyncio
async def test_withdraw(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory

    tx_exec_info=await admin1_signer.send_transaction(admin1, withdrawFeeBalance.contract_address, 'withdraw', [USDC_ID, 10])

    execution_info = await withdrawFeeBalance.get_total_withdrawal_fee(USDC_ID).call()
    assert execution_info.result.fee == 20

    assert_event_emitted(
        tx_exec_info,
        from_address = withdrawFeeBalance.contract_address,
        name = 'WithdrawalFeeBalance_withdraw_called',
        data=[
            USDC_ID,
            10
        ]
    )

@pytest.mark.asyncio
async def test_withdraw_unauthorized(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory

    await assert_revert(alice_signer.send_transaction(alice, withdrawFeeBalance.contract_address, 'withdraw', [USDC_ID, 10]))

@pytest.mark.asyncio
async def test_withdraw_more_than_available(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, dave, account_registry, withdrawFeeBalance = adminAuth_factory

    await assert_revert(admin1_signer.send_transaction(admin1, withdrawFeeBalance.contract_address, 'withdraw', [USDC_ID, 100]))
