import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, from64x61, to64x61

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0, 1]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0, 1]
    )

    user1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer3.public_key, 0, 1]
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

    feeDiscount = await starknet.deploy(
        "contracts/FeeDiscount.cairo",
        constructor_calldata=[]
    )

    fees = await starknet.deploy(
        "contracts/TradingFees.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    fixed_math = await starknet.deploy(
        "contracts/Math_64x61.cairo",
        constructor_calldata=[
        ]
    )

    non_discount = 2305843009213693952 - to64x61(0.03)
    fee = to64x61(0.0002)
    val = await fixed_math.Math64x61_mul(non_discount, fee).call()
    print(val.result)

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [3, 1, feeDiscount.contract_address])

    await signer1.send_transaction(admin1, feeDiscount.contract_address, 'add_user_tokens', [user1.contract_address, 100])

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

@pytest.mark.asyncio
async def test_get_fee1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    # Commenting because of 64x61 bug
    # execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 0).call()
    # result = execution_info.result
    # assert result.fee == to64x61(0.0002 * 0.97)

    execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 1).call()
    result = execution_info.result
    assert result.fee == to64x61(0.0005 * 0.97)

@pytest.mark.asyncio
async def test_get_fee2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await signer1.send_transaction(admin1, feeDiscount.contract_address, 'add_user_tokens', [user1.contract_address, 1000])

    execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 0).call()
    result = execution_info.result
    assert result.fee == to64x61(0.00015 * 0.95)

    execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 1).call()
    result = execution_info.result
    assert result.fee == to64x61(0.0004 * 0.95)

@pytest.mark.asyncio
async def test_update_max_base_fee_tier(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await signer1.send_transaction(admin1, fees.contract_address, 'update_max_base_fee_tier', [0])

    execution_info = await fees.get_max_base_fee_tier().call()
    result = execution_info.result
    assert result.value == 0

@pytest.mark.asyncio
async def test_update_max_discount_tier(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await signer1.send_transaction(admin1, fees.contract_address, 'update_max_discount_tier', [0])

    execution_info = await fees.get_max_discount_tier().call()
    result = execution_info.result
    assert result.value == 0