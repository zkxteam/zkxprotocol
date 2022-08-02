import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address, L1_ZKX_dummy_address
from dummy_signers import signer1, signer2, signer3


@pytest.fixture
def global_var():
    pytest.user1 = None


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def holding_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1, L1_ZKX_dummy_address)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    pytest.user1 = await account_factory.deploy_account(signer3.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    insurance = await starknet_service.deploy(ContractType.InsuranceFund, [registry.contract_address, 1])

    # Access 2 allows adding trusted contracts to the registry
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])

    return adminAuth, insurance, admin1, admin2


@pytest.mark.asyncio
async def test_fund_admin(holding_factory):
    _, insurance, admin1, _ = holding_factory

    await signer1.send_transaction(admin1, insurance.contract_address, 'fund', [str_to_felt("USDC"), 100])

    execution_info = await insurance.balance(str_to_felt("USDC")).call()
    assert execution_info.result.amount == 100


@pytest.mark.asyncio
async def test_fund_reject(holding_factory):
    _, insurance, _, _ = holding_factory

    assert_revert(lambda: signer3.send_transaction(
        pytest.user1, insurance.contract_address, 'fund', [str_to_felt("USDC"), 100]))


@pytest.mark.asyncio
async def test_defund_admin(holding_factory):
    _, insurance, admin1, _ = holding_factory

    await signer1.send_transaction(admin1, insurance.contract_address, 'defund', [str_to_felt("USDC"), 100])

    execution_info = await insurance.balance(str_to_felt("USDC")).call()
    assert execution_info.result.amount == 0

@pytest.mark.asyncio
async def test_defund_more_than_available(holding_factory):
    _, insurance, _, _ = holding_factory

    assert_revert(lambda: signer1.send_transaction(
        admin1, insurance.contract_address, 'defund', [str_to_felt("USDC"), 200]))

@pytest.mark.asyncio
async def test_defund_reject(holding_factory):
    _, insurance, _, _ = holding_factory

    assert_revert(lambda: signer3.send_transaction(
        pytest.user1, insurance.contract_address, 'defund', [str_to_felt("USDC"), 100]))
