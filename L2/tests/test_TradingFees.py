import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

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

    feeDiscount = await starknet.deploy(
        "contracts/FeeDiscount.cairo",
        constructor_calldata=[]
    )

    fees = await starknet.deploy(
        "contracts/TradingFees.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
            feeDiscount.contract_address
        ]
    )

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])

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

    await signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [1, 0, 46116860184273880, 115292150460684704])

    execution_info = await fees.get_base_fees(1).call()
    result = execution_info.result.base_fee

    assert result.numberOfTokens == 0
    assert result.makerFee == 46116860184273880
    assert result.takerFee == 115292150460684704

    await signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [2, 1000, 34587645138205408, 92233720368547760])

    execution_info = await fees.get_base_fees(2).call()
    result = execution_info.result.base_fee

    assert result.numberOfTokens == 1000
    assert result.makerFee == 34587645138205408
    assert result.takerFee == 92233720368547760

    await signer1.send_transaction(admin1, fees.contract_address, 'update_base_fees', [3, 5000, 23058430092136940, 80704505322479296])

    execution_info = await fees.get_base_fees(3).call()
    result = execution_info.result.base_fee

    assert result.numberOfTokens == 5000
    assert result.makerFee == 23058430092136940
    assert result.takerFee == 80704505322479296


@pytest.mark.asyncio
async def test_update_discount(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [1, 0, 6917529027641081856])

    execution_info = await fees.get_discount(1).call()
    result = execution_info.result.discount

    assert result.numberOfTokens == 0
    assert result.discount == 6917529027641081856

    await signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [2, 1000, 11529215046068469760])

    execution_info = await fees.get_discount(2).call()
    result = execution_info.result.discount

    assert result.numberOfTokens == 1000
    assert result.discount == 11529215046068469760

    await signer1.send_transaction(admin1, fees.contract_address, 'update_discount', [3, 5000, 23058430092136939520])

    execution_info = await fees.get_discount(3).call()
    result = execution_info.result.discount

    assert result.numberOfTokens == 5000
    assert result.discount == 23058430092136939520

@pytest.mark.asyncio
async def test_get_fee_and_discount_tier1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 0).call()
    result = execution_info.result
    assert result.base_fee == 46116860184273880
    assert result.discount == 6917529027641081856

    execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 1).call()
    result = execution_info.result
    assert result.base_fee == 115292150460684704
    assert result.discount == 6917529027641081856

@pytest.mark.asyncio
async def test_get_fee_and_discount_tier2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, feeDiscount = adminAuth_factory

    await signer1.send_transaction(admin1, feeDiscount.contract_address, 'add_user_tokens', [user1.contract_address, 1000])

    execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 0).call()
    result = execution_info.result
    assert result.base_fee == 34587645138205408
    assert result.discount == 11529215046068469760

    execution_info = await fees.get_user_fee_and_discount(user1.contract_address, 1).call()
    result = execution_info.result
    assert result.base_fee == 92233720368547760
    assert result.discount == 11529215046068469760

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