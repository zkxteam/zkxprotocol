from copyreg import constructor
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654327)

USDC_ID = str_to_felt("fghj3am52qpzsib")
UST_ID = str_to_felt("yjk45lvmasopq")

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
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])

    ### Deploy user accounts
    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )
    alice = await account_factory.deploy_account(alice_signer.public_key)
    bob = await account_factory.deploy_account(bob_signer.public_key)
    charlie = await account_factory.deploy_account(charlie_signer.public_key)

    ### Deploy infrastructure (Part 2)
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    withdrawal_request = await starknet_service.deploy(ContractType.WithdrawalRequest, [registry.contract_address, 1])
    trading = await starknet_service.deploy(ContractType.Trading, [registry.contract_address, 1])
    
    # Access 3 allows adding trusted contracts to the registry and 1 for adding assets
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [5, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [16, 1, withdrawal_request.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[admin1.contract_address])
    
    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[admin2.contract_address])
    
    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[alice.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[bob.contract_address])
    
    # Add asset
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [UST_ID, 0, str_to_felt("UST"), str_to_felt("UST"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    return adminAuth, admin1, admin2, alice, bob, charlie, account_registry, asset, withdrawal_request

@pytest.mark.asyncio
async def test_revert_unregistered_user_access(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, charlie, account_registry, asset, withdrawal_request = adminAuth_factory

    request_id_1 = 1
    ticker_1 = str_to_felt("USDC")
    amount_1 = to64x61(10)

    await assert_revert(charlie_signer.send_transaction(alice, withdrawal_request.contract_address, 'add_withdrawal_request', [request_id_1, ticker_1, amount_1]))

@pytest.mark.asyncio
async def test_revert_withdrawal_request_due_to_insufficient_balance(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, charlie, account_registry, asset, withdrawal_request = adminAuth_factory

    request_id_1 = 1
    ticker_1 = str_to_felt("USDC")
    amount_1 = to64x61(10)

    await assert_revert(alice_signer.send_transaction(alice, withdrawal_request.contract_address, 'add_withdrawal_request', [request_id_1, ticker_1, amount_1]))

@pytest.mark.asyncio
async def test_add_to_withdrawal_request(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, charlie, account_registry, asset, withdrawal_request = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [UST_ID, bob_balance])

    alice_l1_address = await alice.get_L1_address().call()
    bob_l1_address = await bob.get_L1_address().call()

    request_id_1 = 1
    l1_wallet_address_1 = alice_l1_address.result.res
    ticker_1 = str_to_felt("USDC")
    amount_1 = to64x61(10)

    request_id_2 = 2
    l1_wallet_address_2 = bob_l1_address.result.res
    ticker_2 = str_to_felt("UST")
    amount_2 = to64x61(20)

    await alice_signer.send_transaction(alice, withdrawal_request.contract_address, 'add_withdrawal_request', [request_id_1, ticker_1, amount_1])
    await bob_signer.send_transaction(bob, withdrawal_request.contract_address, 'add_withdrawal_request', [request_id_2, ticker_2, amount_2])

    fetched_withdrawal_request_1 = await withdrawal_request.get_withdrawal_request_data(request_id_1).call()
    print(fetched_withdrawal_request_1.result.withdrawal_request)
    res1 = fetched_withdrawal_request_1.result.withdrawal_request

    assert res1.user_l1_address == l1_wallet_address_1
    assert res1.ticker == ticker_1
    assert res1.amount == amount_1

    fetched_withdrawal_request_2 = await withdrawal_request.get_withdrawal_request_data(request_id_2).call()
    print(fetched_withdrawal_request_2.result.withdrawal_request)
    res2 = fetched_withdrawal_request_2.result.withdrawal_request

    assert res2.user_l1_address == l1_wallet_address_2
    assert res2.ticker == ticker_2
    assert res2.amount == amount_2
