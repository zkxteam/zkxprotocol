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

    ### Deploy infrastructure (Part 2)
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    withdrawal_request = await starknet_service.deploy(ContractType.WithdrawalRequest, [registry.contract_address, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[admin1.contract_address])
    
    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[admin2.contract_address])
    
    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[alice.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry',[bob.contract_address])

    return adminAuth, admin1, admin2, alice, bob, account_registry, withdrawal_request


@pytest.mark.asyncio
async def test_add_to_withdrawal_request(adminAuth_factory):
    adminAuth, admin1, admin2, alice, bob, account_registry, withdrawal_request = adminAuth_factory

    request_id_1 = 1
    l1_wallet_address_1 = alice.contract_address
    collateral_id_1 = str_to_felt("fghj3am52qpzsib")
    amount_1 = to64x61(10)

    request_id_2 = 2
    l1_wallet_address_2 = bob.contract_address
    collateral_id_2 = str_to_felt("yjk45lvmasopq")
    amount_2 = to64x61(20)

    await alice_signer.send_transaction(alice, withdrawal_request.contract_address, 'add_withdrawal_request', [request_id_1, l1_wallet_address_1, collateral_id_1, amount_1])
    await bob_signer.send_transaction(bob, withdrawal_request.contract_address, 'add_withdrawal_request', [request_id_2, l1_wallet_address_2, collateral_id_2, amount_2])

    fetched_withdrawal_request_1 = await withdrawal_request.get_withdrawal_request_data(request_id_1).call()
    print(fetched_withdrawal_request_1.result.withdrawal_request)
    res1 = fetched_withdrawal_request_1.result.withdrawal_request

    assert res1.user_l1_address == alice.contract_address
    assert res1.ticker == collateral_id_1
    assert res1.amount == amount_1

    fetched_withdrawal_request_2 = await withdrawal_request.get_withdrawal_request_data(request_id_2).call()
    print(fetched_withdrawal_request_2.result.withdrawal_request)
    res2 = fetched_withdrawal_request_2.result.withdrawal_request

    assert res2.user_l1_address == bob.contract_address
    assert res2.ticker == collateral_id_2
    assert res2.amount == amount_2
