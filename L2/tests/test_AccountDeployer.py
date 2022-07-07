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
class_hash=0

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()

    


    dec_class = await starknet.declare("contracts/Account.cairo")

    print(dec_class.class_hash)
    print(hex(dec_class.class_hash))
    global class_hash
    class_hash=dec_class.class_hash

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0, 1, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0, 1, 0]
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

    #await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, 
    registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])
    await signer1.send_transaction(admin1, 
    registry.contract_address, 'update_contract_registry', [20, 1, account_deployer.contract_address])
    return adminAuth, account_registry, admin1, admin2, account_deployer


@pytest.mark.asyncio
async def test_deploy_account_contract(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2, account_deployer = adminAuth_factory
    pubkey = signer3.public_key
    print(pubkey)
    await signer1.send_transaction(admin1, 
                                   account_deployer.contract_address,
                                   'set_account_class_hash',
                                   [class_hash])
    await signer1.send_transaction(admin1, 
                                   account_deployer.contract_address,
                                   'set_L1_ZKX_address',
                                   [12345])

    await signer1.send_transaction(admin1, account_deployer.contract_address, 'deploy_account', [pubkey])

    deployed_address = await account_deployer.get_pubkey_to_address(pubkey).call()
    print(deployed_address.result)
    print(hex(deployed_address.result.address))
    deployed_address=deployed_address.result.address
    result = await account_registry.is_registered_user(deployed_address).call()
    assert result.result.present == 1

    abi = get_contract_class(source="contracts/Account.cairo").abi

    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi, 
                                            contract_address=deployed_address,
                                            deploy_execution_info=None)
    result = await new_account_contract.get_public_key().call()

    print(result)

    assert result.result.res == pubkey
    fetched_account_registry = await account_registry.get_account_registry().call()
    assert fetched_account_registry.result.account_registry[0] == deployed_address
   

@pytest.mark.asyncio
async def test_remove_address_from_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2, account_deployer= adminAuth_factory

    await signer1.send_transaction(admin1, account_registry.contract_address, 'remove_from_account_registry', [0])

    fetched_account_registry = await account_registry.get_account_registry().call()
    assert fetched_account_registry.result.account_registry[0] == str_to_felt("456")

    isPresent = await account_registry.is_registered_user(str_to_felt("123")).call()
    assert isPresent.result.present == 0

@pytest.mark.asyncio
async def test__unauthorized_add_address_to_account_registry(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2, callFeeBalance = adminAuth_factory

    assert_revert(lambda: signer1.send_transaction(admin1, admin1.contract_address, 'add_to_account_registry', [str_to_felt("1234")]))

@pytest.mark.asyncio
async def test_add_address_to_account_registry_duplicate(adminAuth_factory):
    adminAuth, account_registry, admin1, admin2, callFeeBalance = adminAuth_factory

    await signer1.send_transaction(admin1, callFeeBalance.contract_address, 'add_to_registry', [str_to_felt("456")])
    fetched_account_registry = await account_registry.get_account_registry().call()
    assert fetched_account_registry.result.account_registry == [3421494]