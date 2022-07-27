import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import DeclaredClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.testing.contract import StarknetContract
signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(12345)
signer4 = Signer(56789)
class_hash=0

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()

    

    # a contract definition has to be declared before we can use class hash
    dec_class = await starknet.declare("contracts/Account.cairo")

    global class_hash
    class_hash=dec_class.class_hash

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 123, 0, 1, 1]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 123, 0, 1, 1]
    )

    user4 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer4.public_key, 123, 0, 1, 1]
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

    account_deployer = await starknet.deploy(
        "contracts/AccountDeployer.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    print(registry.contract_address)

    #await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, 
    registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])
    await signer1.send_transaction(admin1, 
    registry.contract_address, 'update_contract_registry', [20, 1, account_deployer.contract_address])
    return adminAuth, registry, account_registry, admin1, admin2, user4, account_deployer

@pytest.mark.asyncio
async def test_deploy_account_contract_with_zero_hash(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory
    pubkey = signer3.public_key

    # this call should revert since class_hash is not yet set and deploy cannot happen with class_hash as 0
    await assert_revert(signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey, 123456]))



@pytest.mark.asyncio
async def test_deploy_account_contract(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory
    pubkey = signer3.public_key

    # this call should revert since class_hash is not yet set and deploy cannot happen with class_hash as 0
    await assert_revert(signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey, 123456]))

    #print(pubkey)
    await signer1.send_transaction(admin1, 
                                   account_deployer.contract_address,
                                   'set_account_class_hash',
                                   [class_hash])
    await signer1.send_transaction(admin1, 
                                   account_deployer.contract_address,
                                   'set_L1_ZKX_address',
                                   [12345])

    await signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey, 123456])

    # get address of deployed contract
    deployed_address = await account_deployer.get_pubkey_L1_to_address(pubkey, 123456).call()
    #print(deployed_address.result)
    print(hex(deployed_address.result.address))
    deployed_address=deployed_address.result.address
    result = await account_registry.is_registered_user(deployed_address).call()

    # check whether newly deployed contract address is present in the account registry
    assert result.result.present == 1

    abi = get_contract_class(source="contracts/Account.cairo").abi

    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi, 
                                            contract_address=deployed_address,
                                            deploy_execution_info=None)

    # check that the account contract is deployed with the public key used in the deploy call
    result = await new_account_contract.get_public_key().call()

    #print(result)

    assert result.result.res == pubkey

    # check that the account contract has the correct L1 address stored that was used during deployment

    result = await new_account_contract.get_L1_address().call()

    assert result.result.res == 123456

    
    fetched_account_registry = await account_registry.get_account_registry().call()
    assert fetched_account_registry.result.account_registry[0] == deployed_address
   


@pytest.mark.asyncio
async def test_unauthorized_changes_to_config(adminAuth_factory):
    adminAuth, auth_registry, account_registry, admin1, admin2, user4, account_deployer = adminAuth_factory

    await assert_revert(signer4.send_transaction(
        user4, account_deployer.contract_address, 'set_account_class_hash', [12345]))

    await assert_revert(signer4.send_transaction(
        user4, account_deployer.contract_address, 'set_L1_ZKX_address', [123456]))

    await assert_revert(signer4.send_transaction(
        user4, account_deployer.contract_address, 'set_version', [123456]))
    
    result = await account_deployer.get_account_class_hash().call()
    assert result.result.class_hash == class_hash

    result = await account_deployer.get_L1_ZKX_address().call()

    assert result.result.address == 12345

    result = await account_deployer.get_registry_address().call()

    assert result.result.address == auth_registry.contract_address


