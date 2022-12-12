import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import DeclaredClass
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, from64x61, to64x61
from helpers import StarknetService, ContractType
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy accounts
    admin1 = await starknet_service.deploy(ContractType.Account, [
        signer1.public_key
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        signer2.public_key
    ])
    user1 = await starknet_service.deploy(ContractType.Account, [
        signer3.public_key
    ])
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    
    # ZKX Deployer
    zkxDeployer = await starknet_service.deploy(ContractType.ZKXDeployer, [registry.contract_address, 1])

    # a contract definition has to be declared before we can use class hash
    # can declare directly using state for tests
    contract_class_trading = starknet_service.contracts_holder.get_contract_class(ContractType.Trading)
    contract_class_liquidate = starknet_service.contracts_holder.get_contract_class(ContractType.Liquidate)
    contract_class_abr = starknet_service.contracts_holder.get_contract_class(ContractType.ABR)

    class_hash_trading_, _ = await starknet_service.starknet.state.declare(contract_class_trading)
    class_hash_liquidate_, _ = await starknet_service.starknet.state.declare(contract_class_liquidate)
    class_hash_abr_, _ = await starknet_service.starknet.state.declare(contract_class_abr)

    class_hash_trading = int.from_bytes(class_hash_trading_,'big')
    class_hash_liquidate =  int.from_bytes(class_hash_liquidate_,'big')
    class_hash_abr =  int.from_bytes(class_hash_abr_,'big')

    print(class_hash_trading, class_hash_liquidate, class_hash_abr)

    return admin1, admin2, user1, zkxDeployer, class_hash_trading, class_hash_liquidate, class_hash_abr


@pytest.mark.asyncio
async def test_deploy_non_admin(adminAuth_factory):
    admin1, admin2, user1, zkxDeployer, class_hash_trading, class_hash_liquidate, class_hash_abr = adminAuth_factory

    await assert_revert(
        signer3.send_transaction(user1, zkxDeployer.contract_address, 'deploy_contracts', [2, class_hash_trading, class_hash_liquidate])
    )


@pytest.mark.asyncio
async def test_deploy_admin(adminAuth_factory):
    admin1, admin2, user1, zkxDeployer, class_hash_trading, class_hash_liquidate, class_hash_abr = adminAuth_factory
    print(class_hash_trading, class_hash_liquidate)
    await signer1.send_transaction(admin1, zkxDeployer.contract_address, 'deploy_contracts', [2, class_hash_trading, class_hash_liquidate])

    res_deployed = await zkxDeployer.populate_deployed_addresses().call()
    assert len(res_deployed.result.array) == 2


@pytest.mark.asyncio
async def test_salt(adminAuth_factory):
    admin1, admin2, user1, zkxDeployer, class_hash_trading, class_hash_liquidate, class_hash_abr = adminAuth_factory

    res_deployed_before = await zkxDeployer.populate_deployed_addresses().call()

    await signer1.send_transaction(admin1, zkxDeployer.contract_address, 'deploy_contracts', [3, class_hash_trading, class_hash_liquidate, class_hash_abr])

    res_deployed_after = await zkxDeployer.populate_deployed_addresses().call()
    assert len(res_deployed_after.result.array) == 3

    assert res_deployed_before.result.array[0] != res_deployed_after.result.array[0]
    assert res_deployed_before.result.array[1] != res_deployed_after.result.array[1]



