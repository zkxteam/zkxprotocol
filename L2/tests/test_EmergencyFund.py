import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3, signer4


@pytest.fixture
def global_var():
    pytest.user1 = None
    pytest.user2 = None


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def emergencyFund_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    pytest.user1 = await account_factory.deploy_account(signer3.public_key)
    pytest.user2 = await account_factory.deploy_account(signer4.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    holding = await starknet_service.deploy(ContractType.Holding, [registry.contract_address, 1])
    liquidity = await starknet_service.deploy(ContractType.LiquidityFund, [registry.contract_address, 1])
    insurance = await starknet_service.deploy(ContractType.InsuranceFund, [registry.contract_address, 1])
    emergencyFund = await starknet_service.deploy(ContractType.EmergencyFund, [registry.contract_address, 1])
    
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [9, 1, liquidity.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [10, 1, insurance.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [7, 1, holding.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [8, 1, emergencyFund.contract_address])

    return emergencyFund, holding, admin1, admin2, insurance, liquidity


@pytest.mark.asyncio
async def test_fund_invalid(emergencyFund_factory):
    emergencyFund, _, admin1, admin2, insurance, liquidity = emergencyFund_factory
    await assert_revert(signer3.send_transaction(
        pytest.user1, emergencyFund.contract_address, 'fund', [str_to_felt("TSLA"), 0]),
        reverted_with="FundLib: Unauthorized call to manage funds"
    )

@pytest.mark.asyncio
async def test_funding_flow(emergencyFund_factory):
    emergencyFund, _, admin1, admin2, insurance, liquidity = emergencyFund_factory

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'fund', [str_to_felt("TSLA"), 20])
    execution_info = await emergencyFund.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 20

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'defund', [str_to_felt("TSLA"), 3])
    execution_info = await emergencyFund.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 17

@pytest.mark.asyncio
async def test_fund_holding_through_funding_contract(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2, insurance, liquidity = emergencyFund_factory

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'fund_holding', [str_to_felt("TSLA"), 10])
    execution_info = await holding.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 10

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'defund_holding', [str_to_felt("TSLA"), 3])
    execution_info = await holding.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 7

@pytest.mark.asyncio
async def test_fund_holding_unauthorized(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2, insurance, liquidity = emergencyFund_factory

    await assert_revert(signer2.send_transaction(admin2, emergencyFund.contract_address, 'fund_holding', [str_to_felt("TSLA"), 10]), reverted_with="EmergencyFund: Unauthorized call to fund holding")

@pytest.mark.asyncio
async def test_defund_holding_more_than_balance(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2, insurance, liquidity = emergencyFund_factory

    await assert_revert(signer1.send_transaction(admin1, emergencyFund.contract_address, 'defund_holding', [str_to_felt("TSLA"), 10]), reverted_with="FundLib: Insufficient balance")

@pytest.mark.asyncio
async def test_fund_holding_more_than_balance(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2, insurance, liquidity = emergencyFund_factory

    await assert_revert(signer1.send_transaction(admin1, emergencyFund.contract_address, 'fund_holding', [str_to_felt("TSLA"), 20]), reverted_with="EmergencyFund: Insufficient balance")

@pytest.mark.asyncio
async def test_fund_insurance_through_funding_contract(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2, insurance, liquidity = emergencyFund_factory

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'fund_insurance', [str_to_felt("TSLA"), 10])
    execution_info = await insurance.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 10

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'defund_insurance', [str_to_felt("TSLA"), 3])
    execution_info = await insurance.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 7

@pytest.mark.asyncio
async def test_fund_liquidity_through_funding_contract(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2, insurance, liquidity = emergencyFund_factory

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'fund_liquidity', [str_to_felt("TSLA"), 3])
    execution_info = await liquidity.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 3

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'defund_liquidity', [str_to_felt("TSLA"), 3])
    execution_info = await liquidity.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 0