import pytest
import asyncio
from utils import ContractIndex, ManagerAction, assert_revert, to64x61
from helpers import StarknetService, ContractType, AccountFactory
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

    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [registry.contract_address, 1])
    fees = await starknet_service.deploy(ContractType.TradingFees, [registry.contract_address, 1])
    fixed_math = await starknet_service.deploy(ContractType.Math_64x61, [])
    account_factory = AccountFactory(
        starknet_service, L1_dummy_address, registry.contract_address, 1)
    user1 = await account_factory.deploy_ZKX_account(signer3.public_key)

    # Give necessary permissions to admin1
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFeeDetails, True])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageGovernanceToken, True])

    # Add contracts to registry
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.FeeDiscount, 1, feeDiscount.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.TradingFees, 1, fees.contract_address])

    await signer1.send_transaction(admin1, feeDiscount.contract_address, 'increment_governance_tokens', [user1.contract_address, 100])

    return adminAuth, fees, admin1, admin2, user1, feeDiscount


@pytest.mark.asyncio
async def test_get_admin_mapping(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 4).call()
    assert execution_info.result.allowed == 1

    execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 4).call()
    assert execution_info1.result.allowed == 0

    execution_info2 = await feeDiscount.get_user_tokens(user1.contract_address).call()
    assert execution_info2.result.value == 100


@pytest.mark.asyncio
async def test_update_base_fees(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    base_fee_maker1 = to64x61(0.0002)
    base_fee_taker1 = to64x61(0.0005)
    await signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [1, 0, base_fee_maker1, base_fee_taker1])

    execution_info = await fees.get_base_fees(1).call()
    result = execution_info.result.base_fee

    assert result.numberOfTokens == 0
    assert result.makerFee == base_fee_maker1
    assert result.takerFee == base_fee_taker1

    base_fee_maker2 = to64x61(0.00015)
    base_fee_taker2 = to64x61(0.0004)
    await signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [2, 1000, base_fee_maker2, base_fee_taker2])

    execution_info = await fees.get_base_fees(2).call()
    result = execution_info.result.base_fee

    assert result.numberOfTokens == 1000
    assert result.makerFee == base_fee_maker2
    assert result.takerFee == base_fee_taker2

    base_fee_maker3 = to64x61(0.0001)
    base_fee_taker3 = to64x61(0.00035)
    await signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [3, 5000, base_fee_maker3, base_fee_taker3])

    execution_info = await fees.get_base_fees(3).call()
    result = execution_info.result.base_fee

    assert result.numberOfTokens == 5000
    assert result.makerFee == base_fee_maker3
    assert result.takerFee == base_fee_taker3

    execution_info = await fees.get_max_base_fee_tier().call()
    result = execution_info.result.value
    assert result == 3

    # Get all tiers with base fess
    execution_info = await fees.get_all_tier_fees().call()
    parsed_list = list(execution_info.result.fee_tiers)[0]
    assert parsed_list.numberOfTokens == 0
    assert parsed_list.makerFee == base_fee_maker1
    assert parsed_list.takerFee == base_fee_taker1

    parsed_list = list(execution_info.result.fee_tiers)[1]
    assert parsed_list.numberOfTokens == 1000
    assert parsed_list.makerFee == base_fee_maker2
    assert parsed_list.takerFee == base_fee_taker2

    parsed_list = list(execution_info.result.fee_tiers)[2]
    assert parsed_list.numberOfTokens == 5000
    assert parsed_list.makerFee == base_fee_maker3
    assert parsed_list.takerFee == base_fee_taker3


@pytest.mark.asyncio
async def test_update_discount(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    discount1 = to64x61(0.03)
    await signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [1, 0, discount1])

    execution_info = await fees.get_discount(1).call()
    result = execution_info.result.discount

    assert result.numberOfTokens == 0
    assert result.discount == discount1

    discount2 = to64x61(0.05)
    await signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [2, 1000, discount2])

    execution_info = await fees.get_discount(2).call()
    result = execution_info.result.discount

    assert result.numberOfTokens == 1000
    assert result.discount == discount2

    discount3 = to64x61(0.1)
    await signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [3, 5000, discount3])

    execution_info = await fees.get_discount(3).call()
    result = execution_info.result.discount

    assert result.numberOfTokens == 5000
    assert result.discount == discount3

    execution_info = await fees.get_max_discount_tier().call()
    result = execution_info.result.value
    assert result == 3

    # Get all tiers with discounts
    execution_info = await fees.get_all_tier_discounts().call()
    parsed_list = list(execution_info.result.discount_tiers)[0]
    assert parsed_list.numberOfTokens == 0
    assert parsed_list.discount == discount1

    parsed_list = list(execution_info.result.discount_tiers)[1]
    assert parsed_list.numberOfTokens == 1000
    assert parsed_list.discount == discount2

    parsed_list = list(execution_info.result.discount_tiers)[2]
    assert parsed_list.numberOfTokens == 5000
    assert parsed_list.discount == discount3


@pytest.mark.asyncio
async def test_get_fee1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    execution_info = await fees.get_discounted_fee_rate_for_user(user1.contract_address, 2).call()
    result = execution_info.result
    assert result.discounted_base_fee_percent == to64x61(0.0005 * 0.97)
    assert result.base_fee_tier == 1
    assert result.discount_tier == 1

@pytest.mark.asyncio
async def test_get_fee2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await signer1.send_transaction(admin1, feeDiscount.contract_address, 'increment_governance_tokens', [user1.contract_address, 1000])

    execution_info = await fees.get_discounted_fee_rate_for_user(user1.contract_address, 1).call()
    result = execution_info.result
    assert result.discounted_base_fee_percent == to64x61(0.00015 * 0.95)
    assert result.base_fee_tier == 2
    assert result.discount_tier == 2

    execution_info = await fees.get_discounted_fee_rate_for_user(user1.contract_address, 2).call()
    result = execution_info.result
    assert result.discounted_base_fee_percent == to64x61(0.0004 * 0.95)
    assert result.base_fee_tier == 2
    assert result.discount_tier == 2


@pytest.mark.asyncio
async def test_update_base_fee_tier_to_higher_value(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    base_fee_maker3 = to64x61(0.0001)
    base_fee_taker3 = to64x61(0.00035)
    await assert_revert(
        signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [
                                 5, 5000, base_fee_maker3, base_fee_taker3]),
        reverted_with="TradingFees: Invalid tier"
    )


@pytest.mark.asyncio
async def test_update_discount_tier_to_higher_value(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    discount3 = to64x61(0.1)
    await assert_revert(
        signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [
                                 5, 5000, discount3]),
        reverted_with="TradingFees: Invalid tier"
    )


@pytest.mark.asyncio
async def test_update_base_fee_tier_with_incorrect_tier_and_details(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    base_fee_maker3 = to64x61(0.0002)
    base_fee_taker3 = to64x61(0.00035)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [4, 5000, base_fee_maker3, base_fee_taker3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting lower tiers")

    base_fee_maker3 = to64x61(0.00008)
    base_fee_taker3 = to64x61(0.00035)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [4, 5000, base_fee_maker3, base_fee_taker3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting lower tiers")

    base_fee_maker3 = to64x61(0.0001)
    base_fee_taker3 = to64x61(0.0004)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [2, 5000, base_fee_maker3, base_fee_taker3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting upper tiers")

    base_fee_maker3 = to64x61(0.00015)
    base_fee_taker3 = to64x61(0.00035)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [2, 5000, base_fee_maker3, base_fee_taker3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting upper tiers")

    base_fee_maker1 = to64x61(0.0002)
    base_fee_taker1 = to64x61(0.0005)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [0, 0, base_fee_maker1, base_fee_taker1]), reverted_with="TradingFees: Tier and fee details must be > 0")

    base_fee_maker1 = to64x61(0.00015)
    base_fee_taker1 = to64x61(0.0005)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [1, 0, base_fee_maker1, base_fee_taker1]), reverted_with="TradingFees: Invalid fees for the tier to exisiting upper tiers")

    base_fee_maker1 = to64x61(0.0002)
    base_fee_taker1 = to64x61(0.0004)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [1, 0, base_fee_maker1, base_fee_taker1]), reverted_with="TradingFees: Invalid fees for the tier to exisiting upper tiers")


@pytest.mark.asyncio
async def test_update_discount_tier_with_incorrect_tier_and_details(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    discount3 = to64x61(0.09)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [4, 5000, discount3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting lower tiers")

    discount3 = to64x61(0.02)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [2, 5000, discount3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting lower tiers")

    discount3 = to64x61(0.11)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [2, 5000, discount3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting upper tiers")

    discount3 = to64x61(0.11)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [0, 5000, discount3]), reverted_with="TradingFees: Tier and discount must be > 0")

    discount3 = to64x61(0.05)
    await assert_revert(signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [1, 5000, discount3]), reverted_with="TradingFees: Invalid fees for the tier to exisiting upper tiers")
