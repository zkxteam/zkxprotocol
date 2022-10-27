import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import DeclaredClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, assert_event_emitted
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.testing.contract import StarknetContract
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_ZKX_dummy_address

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(12345)
signer4 = Signer(56789)
class_hash=0

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, 123, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    user4 = await account_factory.deploy_account(signer4.public_key)

    # a contract definition has to be declared before we can use class hash
    # can declare directly using state for tests
    contract_class = starknet_service.contracts_holder.get_contract_class(ContractType.AccountManager)
    global class_hash
    #class_hash = await signer1.send_declare_transaction(admin1, contract_class, starknet_service.starknet.state)
    class_hash, _ = await starknet_service.starknet.state.declare(contract_class)
    direct_class_hash = compute_class_hash(contract_class)
    class_hash = int.from_bytes(class_hash,'big')
    assert direct_class_hash == class_hash
    
    # Deploy contracts
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [
        admin1.contract_address,
        admin2.contract_address
    ])

    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    account_deployer = await starknet_service.deploy(ContractType.AccountDeployer, [registry.contract_address, 1])

    #await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, 
    registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, L1_ZKX_dummy_address])
    await signer1.send_transaction(admin1, 
    registry.contract_address, 'update_contract_registry', [20, 1, account_deployer.contract_address])

    return adminAuth, registry, account_registry, admin1, admin2, user4, account_deployer

@pytest.mark.asyncio
async def test_deploy_account_contract_with_zero_hash(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory
    pubkey = signer3.public_key

    # this call should revert since class_hash is not yet set and deploy cannot happen with class_hash as 0
    await assert_revert(signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey, 123456]), reverted_with="AccountDeploayer: Class hash cannot be 0")

@pytest.mark.asyncio
async def test_deploy_account_contract(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory
    pubkey = signer3.public_key

    # this call should revert since class_hash is not yet set and deploy cannot happen with class_hash as 0
    await assert_revert(signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey, 123456]), reverted_with="AccountDeploayer: Class hash cannot be 0")

    #print(pubkey)
    tx_exec_info=await signer1.send_transaction(admin1, 
                                   account_deployer.contract_address,
                                   'set_account_class_hash',
                                   [class_hash])
   
    assert_event_emitted(
        tx_exec_info,
        from_address = account_deployer.contract_address,
        name = 'class_hash_changed',
        data = [
            class_hash
        ]
    )
    tx_exec_info=await signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey, 123456])

    # get address of deployed contract
    deployed_address = await account_deployer.get_pubkey_L1_to_address(pubkey, 123456).call()
    #print(deployed_address.result)
   
    deployed_address=deployed_address.result.address

    assert_event_emitted(
        tx_exec_info,
        from_address = account_deployer.contract_address,
        name = 'account_deployed',
        data =[
            pubkey,
            123456,
            deployed_address
        ]
    )
    
    result = await account_registry.is_registered_user(deployed_address).call()

    # check whether newly deployed contract address is present in the account registry
    assert result.result.present == 1

    abi = get_contract_class(source="tests/testable/TestAccountManager.cairo").abi

    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi, 
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    # check that the account manager contract is deployed with the public key used in the deploy call
    result = await new_account_contract.get_public_key().call()

    #print(result)

    assert result.result.res == pubkey

    # check that the account contract has the correct L1 address stored that was used during deployment

    result = await new_account_contract.get_L1_address().call()

    assert result.result.res == 123456

    array_length = await account_registry.get_registry_len().call()
    fetched_account_registry = await account_registry.get_account_registry(0, array_length.result.len).call()
    
    assert fetched_account_registry.result.account_registry[0] == deployed_address
   
@pytest.mark.asyncio
async def test_unauthorized_changes_to_config(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory

    await assert_revert(signer4.send_transaction(
        user4, account_deployer.contract_address, 'set_account_class_hash', [12345]), reverted_with="Caller Check: Unauthorized caller")

    await assert_revert(signer4.send_transaction(
        user4, account_deployer.contract_address, 'set_contract_version', [123456]), reverted_with="Caller Check: Unauthorized caller")
    
    result = await account_deployer.get_account_class_hash().call()
    assert result.result.class_hash == class_hash

    result = await account_deployer.get_registry_address().call()

    assert result.result.registry_address == auth_registry.contract_address



@pytest.mark.asyncio
async def test_check_unknown_pubkey_L1_address(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory

    pubkey = signer3.public_key
    deployed_address = await account_deployer.get_pubkey_L1_to_address(pubkey, 456).call() #456 is not a known L1 address
    #print(deployed_address.result)
    deployed_address=deployed_address.result.address

    assert deployed_address == 0

    deployed_address = await account_deployer.get_pubkey_L1_to_address(123, 123456).call() #123 is not a known pubkey
   
    deployed_address=deployed_address.result.address

    assert deployed_address == 0


@pytest.mark.asyncio
async def test_redeploy_existing_account(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory
    pubkey = signer3.public_key

    # this pubkey, L1 address combination is already deployed and hence should revert
    await assert_revert(signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey, 123456]), reverted_with="AccountDeployer: Account exists")