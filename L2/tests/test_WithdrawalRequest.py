from copyreg import constructor
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
dave_signer = Signer(123456789987654326)

maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_ID = str_to_felt("32f0406jz7qj8")
USDC_ID = str_to_felt("fghj3am52qpzsib")
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin1_signer.public_key, 0, 1, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin2_signer.public_key, 0, 1, 0]
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

    fees = await starknet.deploy(
        "contracts/TradingFees.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    asset = await starknet.deploy(
        "contracts/Asset.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    alice = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            alice_signer.public_key,
            registry.contract_address,
            1,
            0
        ]
    )

    bob = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            bob_signer.public_key,
            registry.contract_address,
            1,
            0
        ]
    )

    dave = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            dave_signer.public_key,
            registry.contract_address,
            1,
            0
        ]
    )

    fixed_math = await starknet.deploy(
        "contracts/Math_64x61.cairo",
        constructor_calldata=[
        ]
    )

    holding = await starknet.deploy(
        "contracts/Holding.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    feeBalance = await starknet.deploy(
        "contracts/FeeBalance.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    market = await starknet.deploy(
        "contracts/Markets.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    trading = await starknet.deploy(
        "contracts/Trading.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    feeDiscount = await starknet.deploy(
        "contracts/FeeDiscount.cairo",
        constructor_calldata=[]
    )

    accountRegistry = await starknet.deploy(
        "contracts/AccountRegistry.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    withdrawal_request = await starknet.deploy(
        "contracts/WithdrawalRequest.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Access 2 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [3, 1, feeDiscount.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [4, 1, fees.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [5, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [6, 1, feeBalance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [7, 1, holding.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, accountRegistry.contract_address])

    # Add base fee and discount in Trading Fee contract
    base_fee_maker1 = to64x61(0.0002)
    base_fee_taker1 = to64x61(0.0005)
    await admin1_signer.send_transaction(admin1, fees.contract_address, 'update_base_fees', [1, 0, base_fee_maker1, base_fee_taker1])
    base_fee_maker2 = to64x61(0.00015)
    base_fee_taker2 = to64x61(0.0004)
    await admin1_signer.send_transaction(admin1, fees.contract_address, 'update_base_fees', [2, 1000, base_fee_maker2, base_fee_taker2])
    base_fee_maker3 = to64x61(0.0001)
    base_fee_taker3 = to64x61(0.00035)
    await admin1_signer.send_transaction(admin1, fees.contract_address, 'update_base_fees', [3, 5000, base_fee_maker3, base_fee_taker3])
    discount1 = to64x61(0.03)
    await admin1_signer.send_transaction(admin1, fees.contract_address, 'update_discount', [1, 0, discount1])
    discount2 = to64x61(0.05)
    await admin1_signer.send_transaction(admin1, fees.contract_address, 'update_discount', [2, 1000, discount2])
    discount3 = to64x61(0.1)
    await admin1_signer.send_transaction(admin1, fees.contract_address, 'update_discount', [3, 5000, discount3])

    # Add assets
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [BTC_ID, 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [BTC_USD_ID, BTC_ID, USDC_ID, 0, 1])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])

    # Set the balance of admin1 and admin2
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawal_request


@pytest.mark.asyncio
async def test_registering_of_users(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawal_request = adminAuth_factory

    alice_balance = to64x61(1000)
    bob_balance = to64x61(1000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("pqlkzc3434")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(500)
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("p21pdfs12mfd")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(500)
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(500)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)
    print(res1)


@pytest.mark.asyncio
async def test_add_to_withdrawal_request(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawal_request = adminAuth_factory

    l1_wallet_address_1 = alice.contract_address
    collateral_id_1 = str_to_felt("fghj3am52qpzsib")
    amount_1 = to64x61(10)

    l1_wallet_address_2 = bob.contract_address
    collateral_id_2 = str_to_felt("yjk45lvmasopq")
    amount_2 = to64x61(20)

    await alice_signer.send_transaction(alice, withdrawal_request.contract_address, 'add_withdrawal_request', [l1_wallet_address_1, collateral_id_1, amount_1, 0])
    await bob_signer.send_transaction(bob, withdrawal_request.contract_address, 'add_withdrawal_request', [l1_wallet_address_2, collateral_id_2, amount_2, 0])

    fetched_withdrawal_request = await withdrawal_request.get_withdrawal_request_data().call()
    print(fetched_withdrawal_request.result.withdrawal_request_list)

    res1 = list(fetched_withdrawal_request.result.withdrawal_request_list[0])
    print(res1)

    assert res1[0] == alice.contract_address
    assert res1[2] == collateral_id_1
    assert res1[3] == amount_1
    assert res1[4] == 0
    assert res1[5] == 0
    
    res2 = list(fetched_withdrawal_request.result.withdrawal_request_list[1])
    print(res2)

    assert res2[0] == bob.contract_address
    assert res2[2] == collateral_id_2
    assert res2[3] == amount_2
    assert res2[4] == 0
    assert res2[5] == 0
