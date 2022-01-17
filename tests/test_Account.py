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


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key]
    )
    return admin1, admin2


@pytest.mark.asyncio
async def test_adding_order(adminAuth_factory):
    admin1, admin2 = adminAuth_factory

    await signer2.send_transaction(admin2, admin1.contract_address, 'addOrder', [ str_to_felt("32f0406jz7qj8"), str_to_felt("ETH"), str_to_felt("long"), str_to_felt("01-01-2022"), 100, 1, str_to_felt(""), 0, str_to_felt("PartiallyExecuted")])

    execution_info = await admin1.getOrder(str_to_felt("32f0406jz7qj8")).call()
    fetched_order = execution_info.result.order

    assert fetched_order.ticker == str_to_felt("ETH")
    assert fetched_order.orderType == str_to_felt("long")
    assert fetched_order.openingTimestamp == str_to_felt("01-01-2022")
    assert fetched_order.openingPrice == 100
    assert fetched_order.assetQuantity == 1
    assert fetched_order.closingTimestamp == str_to_felt("")
    assert fetched_order.closingPrice == 0 
    assert fetched_order.orderStatus == str_to_felt("PartiallyExecuted")

    execution_info1 = await admin1.getAssetDetails(str_to_felt("ETH")).call()
    assetQuantity = execution_info1.result.assetQuantity

    assert assetQuantity == 1



@pytest.mark.asyncio
async def test_modifying_order(adminAuth_factory):
    admin1, admin2 = adminAuth_factory

    await signer2.send_transaction(admin2, admin1.contract_address, 'addOrder', [ str_to_felt("32f0406jz7qj8"), str_to_felt("ETH"), str_to_felt("long"), str_to_felt("01-01-2022"), 100, 1, str_to_felt(""), 0, str_to_felt("PartiallyExecuted")])

    execution_info = await admin1.getOrder(str_to_felt("32f0406jz7qj8")).call()
    fetched_order = execution_info.result.order

    assert fetched_order.ticker == str_to_felt("ETH")
    assert fetched_order.orderType == str_to_felt("long")
    assert fetched_order.openingTimestamp == str_to_felt("01-01-2022")
    assert fetched_order.openingPrice == 100
    assert fetched_order.assetQuantity == 1
    assert fetched_order.closingTimestamp == str_to_felt("")
    assert fetched_order.closingPrice == 0 
    assert fetched_order.orderStatus == str_to_felt("PartiallyExecuted")

    await signer1.send_transaction(admin1,admin1.contract_address, 'modifyOrder', [ str_to_felt("32f0406jz7qj8"), str_to_felt("ETH"), str_to_felt("long"), str_to_felt("01-01-2022"), 100, 1, str_to_felt("17-01-2022"), 90, str_to_felt("Executed")])

    execution_info1 = await admin1.getOrder(str_to_felt("32f0406jz7qj8")).call()
    fetched_order1 = execution_info1.result.order

    assert fetched_order1.ticker == str_to_felt("ETH")
    assert fetched_order1.orderType == str_to_felt("long")
    assert fetched_order1.openingTimestamp == str_to_felt("01-01-2022")
    assert fetched_order1.openingPrice == 100
    assert fetched_order1.assetQuantity == 1
    assert fetched_order1.closingTimestamp == str_to_felt("17-01-2022")
    assert fetched_order1.closingPrice == 90 
    assert fetched_order1.orderStatus == str_to_felt("Executed")




