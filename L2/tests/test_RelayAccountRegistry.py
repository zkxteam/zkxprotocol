import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()

# give admin1 permission to modify registry
# add underling contract to registry
# deploy relay registry addr, version, index (using what was added in registry)

AccountRegistry_INDEX=14

@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    
    #print(starknet.state.general_config.chain_id.value)

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0, 1]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0, 1]
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



    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address,3,1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address,3,1])
    await signer1.send_transaction(admin1, 
                                registry.contract_address,
                                 'update_contract_registry', [AccountRegistry_INDEX,1, account_registry.contract_address])

    relay_account_registry = await starknet.deploy(
        "contracts/relay_contracts/RelayAccountRegistry.cairo",
        constructor_calldata=[
            registry.contract_address,
            1,
            AccountRegistry_INDEX
        ]
    )

    await signer1.send_transaction(admin1, 
    adminAuth.contract_address, 'update_admin_mapping', [relay_account_registry.contract_address,0,1])


    return adminAuth, account_registry, relay_account_registry, admin1, admin2, registry


@pytest.mark.asyncio
async def test_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, relay_account_registry, admin1, admin2, registry = adminAuth_factory

    await signer1.send_transaction(
        admin1, relay_account_registry.contract_address, 'add_to_account_registry', [str_to_felt("123")])
    #print(ex_info)

    hash_transaction_1=signer1.current_hash
    print(hash_transaction_1)
    await signer1.send_transaction(admin1, 
    relay_account_registry.contract_address, 'add_to_account_registry', [str_to_felt("456")])

    hash_transaction_2=signer1.current_hash
    print(hash_transaction_2)

    fetched_account_registry = await account_registry.get_account_registry().call()
    fetched_account_registry1 = await relay_account_registry.get_account_registry().call()
    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('add_to_account_registry')).call()
    
    print(call_counter.result)
    hash_status=await relay_account_registry.get_caller_hash_status(admin1.contract_address,signer1.current_hash).call()
    print(hash_status.result)
    hash_list=await relay_account_registry.get_caller_hash_list(admin1.contract_address).call()
    print(hash_list.result)
    
    assert call_counter.result.count == 2
    assert hash_status.result.res == 1 # 2nd transaction seen i.e. status is 1
    assert hash_list.result.hash_list[0]== hash_transaction_1 
    assert hash_list.result.hash_list[1]== hash_transaction_2

    assert fetched_account_registry1.result.account_registry[0] == str_to_felt("123")
    assert fetched_account_registry1.result.account_registry[1] == str_to_felt("456")

    # verify by calling underlying contract directly
    assert fetched_account_registry.result.account_registry[0] == str_to_felt("123")
    assert fetched_account_registry.result.account_registry[1] == str_to_felt("456")

@pytest.mark.asyncio
async def test_remove_address_from_account_registry(adminAuth_factory):
    adminAuth, account_registry, relay_account_registry, admin1, admin2, registry = adminAuth_factory

    fetched_account_registry1 = await relay_account_registry.get_account_registry().call()
    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('add_to_account_registry')).call()
    print(fetched_account_registry1.result)
    print(call_counter.result)
    call_counter = await relay_account_registry.get_call_counter(
        admin1.contract_address,str_to_felt('remove_from_account_registry')).call()
    
    assert call_counter.result.count == 0
    await signer1.send_transaction(admin1, relay_account_registry.contract_address, 'remove_from_account_registry', [0])

    fetched_account_registry = await account_registry.get_account_registry().call()
    relay_fetched_account_registry = await relay_account_registry.get_account_registry().call()
    print(fetched_account_registry.result.account_registry)
    assert fetched_account_registry.result.account_registry[0] == str_to_felt("456")
    assert relay_fetched_account_registry.result.account_registry[0] == str_to_felt("456")


@pytest.mark.asyncio
async def test_authorized_actions_in_relay(adminAuth_factory):
    adminAuth, account_registry, relay_account_registry, admin1, admin2, registry = adminAuth_factory

    await signer1.send_transaction(admin1, 
    relay_account_registry.contract_address, 'add_to_account_registry', [str_to_felt("789")])
    add_hash = signer1.current_hash
    hash_status=await relay_account_registry.get_caller_hash_status(admin1.contract_address,signer1.current_hash).call()

    assert hash_status.result.res == 1

    await signer1.send_transaction(
        admin1, relay_account_registry.contract_address, 'mark_caller_hash_paid', [admin1.contract_address,add_hash])
    
    hash_status=await relay_account_registry.get_caller_hash_status(admin1.contract_address,add_hash).call()

    assert hash_status.result.res == 2

    

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

    assert call_counter.result.count == 0

    index = await relay_account_registry.get_self_index().call()
    assert index.result.index == AccountRegistry_INDEX

    await signer1.send_transaction(admin1, relay_account_registry.contract_address, 'set_self_index', [100])

    index = await relay_account_registry.get_self_index().call()
    assert index.result.index == 100

    registry_address = await relay_account_registry.get_registry_address_at_relay().call()

    assert registry_address.result.address == registry.contract_address

    version = await relay_account_registry.get_current_version().call()

    assert version.result.res == 1

    await signer1.send_transaction(admin1, relay_account_registry.contract_address, 'set_current_version', [2])

    version = await relay_account_registry.get_current_version().call()

    assert version.result.res == 2