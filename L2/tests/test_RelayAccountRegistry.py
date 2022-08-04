import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()

# give admin1 permission to modify registry
# add underling contract to registry
# deploy relay registry addr, version, index (using what was added in registry)

AccountRegistry_INDEX=14

@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy admins
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    admin3 = await account_factory.deploy_account(signer3.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address,2,1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address,3,1])

    # account registry contract has to be in index to be acceible by relay
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [AccountRegistry_INDEX,1, account_registry.contract_address])
    
    relay_account_registry = await starknet_service.deploy(ContractType.RelayAccountRegistry, [
        registry.contract_address,
        1,
        AccountRegistry_INDEX
    ])

    # spoof account deployer contract since add_to_account_registry only accepts calls from account deployer contract

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20,1, relay_account_registry.contract_address])

    # give relay master admin access for priviledged access
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_account_registry.contract_address, 0, 1])
    await signer2.send_transaction(admin2, adminAuth.contract_address, 'update_admin_mapping', [relay_account_registry.contract_address, 0, 1])

    return adminAuth, account_registry, relay_account_registry, admin1, admin2, admin3, registry


@pytest.mark.asyncio
async def test_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, relay_account_registry, admin1, admin2, admin3, registry = adminAuth_factory

    hash_list=await relay_account_registry.get_caller_hash_list(admin1.contract_address).call()
    print(hash_list.result)
    assert len(hash_list.result.hash_list) == 0 # no calls, hash list should be []
    await signer1.send_transaction(
        admin1, relay_account_registry.contract_address, 'add_to_account_registry', [str_to_felt("123")])
    #print(ex_info)

    hash_transaction_1=signer1.current_hash # hash of 1st transaction
    print(hash_transaction_1)
    await signer1.send_transaction(admin1, 
    relay_account_registry.contract_address, 'add_to_account_registry', [str_to_felt("456")])

    hash_transaction_2=signer1.current_hash # hash of 2nd transaction
    print(hash_transaction_2)

    array_length = await account_registry.get_registry_len().call()
    fetched_account_registry = await account_registry.get_account_registry(0, array_length.result.len).call()
    fetched_account_registry1 = await relay_account_registry.get_account_registry(0, array_length.result.len).call()
    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('add_to_account_registry')).call()
    
    print(call_counter.result)
    hash_status=await relay_account_registry.get_caller_hash_status(admin1.contract_address,signer1.current_hash).call()
    print(hash_status.result)
    hash_list=await relay_account_registry.get_caller_hash_list(admin1.contract_address).call()
    print(hash_list.result)
    
    assert call_counter.result.count == 2 # for 2 add transactions
    assert hash_status.result.res == 1 # 2nd transaction seen i.e. status is 1

    # verify contents of hash list for this caller
    assert hash_list.result.hash_list[0]== hash_transaction_1 
    assert hash_list.result.hash_list[1]== hash_transaction_2

    # verify object returned by relay
    assert fetched_account_registry1.result.account_registry[0] == str_to_felt("123")
    assert fetched_account_registry1.result.account_registry[1] == str_to_felt("456")

    # verify by calling underlying contract directly
    assert fetched_account_registry.result.account_registry[0] == str_to_felt("123")
    assert fetched_account_registry.result.account_registry[1] == str_to_felt("456")

    isPresent = await account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 1
    isPresent = await account_registry.is_registered_user(str_to_felt("456")).call()
    assert isPresent.result.present == 1

    isPresent = await relay_account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 1
    isPresent = await relay_account_registry.is_registered_user(str_to_felt("456")).call()
    assert isPresent.result.present == 1

@pytest.mark.asyncio
async def test_remove_address_from_account_registry(adminAuth_factory):
    adminAuth, account_registry, relay_account_registry, admin1, admin2, admin3, registry = adminAuth_factory

    array_length_before = await account_registry.get_registry_len().call()
    fetched_account_registry1 = await relay_account_registry.get_account_registry(0, array_length_before.result.len).call()
    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('add_to_account_registry')).call()
    
    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('remove_from_account_registry')).call()
    

    assert call_counter.result.count == 0 # call counter for remove is still 0
    await signer1.send_transaction(admin1, relay_account_registry.contract_address, 'remove_from_account_registry', [0])

    hash_list=await relay_account_registry.get_caller_hash_list(admin1.contract_address).call()
    print(hash_list.result)
    assert len(hash_list.result.hash_list) == 3 # total transactions = 2 add + 1 remove = 3

    array_length_after = await account_registry.get_registry_len().call()
    fetched_account_registry = await account_registry.get_account_registry(0, array_length_after.result.len).call()
    relay_fetched_account_registry = await relay_account_registry.get_account_registry(0, array_length_after.result.len).call()
    print(fetched_account_registry.result.account_registry)

    # verify through relay and direct to underlying contract

    assert fetched_account_registry.result.account_registry[0] == str_to_felt("456")
    assert relay_fetched_account_registry.result.account_registry[0] == str_to_felt("456")

    isPresent = await relay_account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 0


@pytest.mark.asyncio
async def test_authorized_actions_in_relay(adminAuth_factory):
    adminAuth, account_registry, relay_account_registry, admin1, admin2, admin3, registry = adminAuth_factory

    await signer1.send_transaction(admin1, 
    relay_account_registry.contract_address, 'add_to_account_registry', [str_to_felt("789")])
    add_hash = signer1.current_hash
    hash_status=await relay_account_registry.get_caller_hash_status(admin1.contract_address,signer1.current_hash).call()

    assert hash_status.result.res == 1

    # trying to mark unseen transaction hash as paid will revert
    await assert_revert(signer1.send_transaction(
        admin1, relay_account_registry.contract_address, 'mark_caller_hash_paid', [admin1.contract_address,123]))

    await signer1.send_transaction(
        admin1, relay_account_registry.contract_address, 'mark_caller_hash_paid', [admin1.contract_address,add_hash])
    
    hash_status=await relay_account_registry.get_caller_hash_status(admin1.contract_address,add_hash).call()

    assert hash_status.result.res == 2 # transaction hash status is 2 i.e. paid

    

    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('add_to_account_registry')).call()

    assert call_counter.result.count == 3

    await signer1.send_transaction(
        admin1, 
        relay_account_registry.contract_address,
        'reset_call_counter',
        [admin1.contract_address,str_to_felt('add_to_account_registry')])

    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('add_to_account_registry')).call()

    assert call_counter.result.count == 0 # counter should be 0 after resetting

    index = await relay_account_registry.get_self_index().call()
    assert index.result.index == AccountRegistry_INDEX

    # user with master admin access only can do priviledged actions - signer3 is not authorized
    await assert_revert(signer3.send_transaction(admin3, relay_account_registry.contract_address, 'set_self_index', [100]))

    # change and verify index
    await signer1.send_transaction(admin1, relay_account_registry.contract_address, 'set_self_index', [100])

    index = await relay_account_registry.get_self_index().call()
    assert index.result.index == 100 

    # check registry address
    
    registry_address = await relay_account_registry.get_registry_address_at_relay().call()

    assert registry_address.result.address == registry.contract_address

    version = await relay_account_registry.get_current_version().call()

    assert version.result.res == 1

    # change and verify version
    await signer1.send_transaction(admin1, relay_account_registry.contract_address, 'set_current_version', [2])

    version = await relay_account_registry.get_current_version().call()

    assert version.result.res == 2