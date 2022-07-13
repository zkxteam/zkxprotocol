from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, convertList

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
liquidator_signer = Signer(123456789987654326)
daniel_signer = Signer(123456789987654327)
eduard_signer = Signer(123456789987654328)

maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_ID = str_to_felt("32f0406jz7qj8")
ETH_ID = str_to_felt("65ksgn23nv")
USDC_ID = str_to_felt("fghj3am52qpzsib")
UST_ID = str_to_felt("yjk45lvmasopq")
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
DOGE_ID = str_to_felt("jdi2i8621hzmnc7324o")
TSLA_ID = str_to_felt("i39sk1nxlqlzcee")


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

    charlie = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            charlie_signer.public_key,
            registry.contract_address,
            1,
            0
        ]
    )

    daniel = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            daniel_signer.public_key,
            registry.contract_address,
            1,
            0
        ]
    )

    eduard = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            eduard_signer.public_key,
            registry.contract_address,
            1,
            0
        ]
    )

    liquidator = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            liquidator_signer.public_key,
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

    liquidityFund = await starknet.deploy(
        "contracts/LiquidityFund.cairo",
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

    liquidate = await starknet.deploy(
        "contracts/Liquidate.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    insuranceFund = await starknet.deploy(
        "contracts/InsuranceFund.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    feeDiscount = await starknet.deploy(
        "contracts/FeeDiscount.cairo",
        constructor_calldata=[]
    )

    marketPrices = await starknet.deploy(
        "contracts/MarketPrices.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    timestamp = int(time.time())

    starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet.state.state.block_info.gas_price,
        sequencer_address=starknet.state.state.block_info.sequencer_address
    )

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
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
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [9, 1, liquidityFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [10, 1, insuranceFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [11, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [21, 1, marketPrices.contract_address])

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
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [BTC_ID, 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ETH_ID, 0, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [UST_ID, 0, str_to_felt("UST"), str_to_felt("UST"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])

    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [BTC_USD_ID, BTC_ID, USDC_ID, 0, 1, 10])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [ETH_USD_ID, ETH_ID, USDC_ID, 0, 1, 10])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Fund the Liquidity fund contract
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Set the balance of admin1 and admin2
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

    alice_usdc = to64x61(5500)
    alice_ust = to64x61(1000)
    bob_usdc = to64x61(6000)
    bob_ust = to64x61(5500)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_usdc])
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [UST_ID, alice_ust])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_usdc])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [UST_ID, bob_ust])

    ####### Opening of Orders 1#######
    size = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("343uofdsjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(2)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(2)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("wer4iljemn")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(5000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(2)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        position1,
        orderType1,
        direction1,
        to64x61(2),
        2,
        to64x61(5000),
        to64x61(5000),
        leverage1
    ]

    orderState2 = await bob.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        to64x61(2),
        2,
        to64x61(5000),
        to64x61(5000),
        leverage2
    ]

    alice_list = await alice.return_array_positions().call()
    alice_list_parsed = list(alice_list.result.array_list)

    print("Alice Positions ", alice_list_parsed)

    bob_list = await bob.return_array_positions().call()
    bob_list_parsed = list(bob_list.result.array_list)

    print("Bob Positions ", bob_list_parsed)

    alice_list_collaterals = await alice.return_array_collaterals().call()
    alice_list_collaterals_parsed = list(
        alice_list_collaterals.result.array_list)

    print("Alice collaterals :", alice_list_collaterals_parsed)

    bob_list_collaterals = await bob.return_array_collaterals().call()
    bob_list_collaterals_parsed = list(
        bob_list_collaterals.result.array_list)

    print("Bob collaterals :", bob_list_collaterals_parsed)

    ##############################################
    ######## Alice's liquidation result 1 ##########
    ##############################################

    liquidate_result_alice = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        alice.contract_address,
        # 1 Position + 2 Collaterals
        3,
        # Position 1 - BTC short
        BTC_ID,
        USDC_ID,
        to64x61(5000),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        UST_ID,
        0,
        to64x61(0.05)
    ])
    print("liquidation resul...", liquidate_result_alice.result.response[0], " ",
          liquidate_result_alice.result.response[1])

    assert liquidate_result_alice.result.response[1] == order_id_1

    alice_balance_usdc = await alice.get_balance(USDC_ID).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    assert from64x61(alice_balance_usdc.result.res) == 495.15

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 787.5

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == 5819.9075

    ##############################################
    ######## Bob's liquidation result 1 ##########
    ##############################################

    liquidate_result_bob = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        bob.contract_address,
        # 1 Position + 2 Collaterals
        3,
        # Position 1 - BTC long
        BTC_ID,
        USDC_ID,
        to64x61(5000),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        UST_ID,
        0,
        to64x61(0.05)
    ])

    print("liquidation resul...", liquidate_result_bob.result.response[0],
          liquidate_result_bob.result.response[1])

    assert liquidate_result_bob.result.response[0] == 0
    assert liquidate_result_bob.result.response[1] == order_id_2

    bob_balance_usdc = await bob.get_balance(USDC_ID).call()
    print("Bob usdc balance is...", from64x61(bob_balance_usdc.result.res))

    assert from64x61(bob_balance_usdc.result.res) == 998.0600000000001

    bob_balance_ust = await bob.get_balance(UST_ID).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintenance = await liquidate.return_maintenance().call()
    print("Bob maintenance requirement:",
          from64x61(bob_maintenance.result.res))

    assert from64x61(bob_maintenance.result.res) == 787.5

    bob_acc_value = await liquidate.return_acc_value().call()
    print("bob acc value:", from64x61(bob_acc_value.result.res))

    assert from64x61(bob_acc_value.result.res) == 6572.963000000001

    ###### Opening of Orders 2 #######
    size2 = to64x61(3)
    marketID_2 = ETH_USD_ID

    order_id_3 = str_to_felt("erwf6s2jxz")
    assetID_3 = ETH_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(100)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(3)
    direction3 = 0
    closeOrder3 = 0
    parentOrder3 = 0
    leverage3 = to64x61(3)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("rfdgljemn")
    assetID_4 = ETH_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(100)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(3)
    direction4 = 1
    closeOrder4 = 0
    parentOrder4 = 0
    leverage4 = to64x61(3)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(100)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, parentOrder3, 1, 
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, parentOrder4, 0,
    ])

    orderState3 = await alice.get_order_data(orderID_=order_id_3).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3,
        collateralID_3,
        price3,
        execution_price2,
        position3,
        orderType3,
        direction3,
        to64x61(3),
        2,
        to64x61(100),
        to64x61(200),
        leverage3
    ]

    orderState4 = await bob.get_order_data(orderID_=order_id_4).call()
    res4 = list(orderState4.result.res)

    assert res4 == [
        assetID_4,
        collateralID_4,
        price4,
        execution_price2,
        position4,
        orderType4,
        direction4,
        to64x61(3),
        2,
        to64x61(100),
        to64x61(200),
        leverage4
    ]

    alice_list = await alice.return_array_positions().call()
    alice_list_parsed = list(alice_list.result.array_list)

    print("Alice Positions ", alice_list_parsed)

    bob_list = await bob.return_array_positions().call()
    bob_list_parsed = list(bob_list.result.array_list)

    print("Bob Positions ", bob_list_parsed)

    ##############################################
    ######## Alice's liquidation result 2 ##########
    ##############################################

    liquidate_result_alice = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        alice.contract_address,
        # 2 Position + 2 Collaterals
        4,
        # Position 1 - BTC short
        BTC_ID,
        USDC_ID,
        to64x61(5000),
        to64x61(1.05),
        # Position 2 - ETH short
        ETH_ID,
        USDC_ID,
        to64x61(100),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        UST_ID,
        0,
        to64x61(0.05)
    ])
    print("liquidation resul...", liquidate_result_alice.result.response[0], " ",
          liquidate_result_alice.result.response[1])

    assert liquidate_result_alice.result.response[0] == 0
    assert liquidate_result_alice.result.response[1] == order_id_3

    alice_balance_usdc = await alice.get_balance(USDC_ID).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    assert from64x61(alice_balance_usdc.result.res) == 395.0045

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == 5819.754725000001

    ##############################################
    ######## Bob's liquidation result 2 ##########
    ##############################################
    liquidate_result_bob = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        bob.contract_address,
        # 2 Position + 2 Collaterals
        4,
        # Position 1 - BTC long
        BTC_ID,
        USDC_ID,
        to64x61(5000),
        to64x61(1.05),
        # Position 2 - ETH long
        ETH_ID,
        USDC_ID,
        to64x61(100),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        UST_ID,
        0,
        to64x61(0.05)
    ])

    print("liquidation resul...", liquidate_result_bob.result.response[0],
          liquidate_result_bob.result.response[1])

    assert liquidate_result_bob.result.response[0] == 0
    assert liquidate_result_bob.result.response[1] == order_id_4

    bob_balance_usdc = await bob.get_balance(USDC_ID).call()
    print("Bob usdc balance is...", from64x61(bob_balance_usdc.result.res))

    assert from64x61(bob_balance_usdc.result.res) == 898.0018

    bob_balance_ust = await bob.get_balance(UST_ID).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintenance = await liquidate.return_maintenance().call()
    print("Bob maintenance requirement:",
          from64x61(bob_maintenance.result.res))

    assert from64x61(bob_maintenance.result.res) == 811.125

    bob_acc_value = await liquidate.return_acc_value().call()
    print("bob acc value:", from64x61(bob_acc_value.result.res))

    assert from64x61(bob_acc_value.result.res) == 6572.90189


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory
    ##############################################
    ######## Alice's liquidation result 3 ##########
    ##############################################

    liquidate_result_alice = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        alice.contract_address,
        # 2 Position + 2 Collaterals
        4,
        # Position 1 - BTC short
        BTC_ID,
        USDC_ID,
        to64x61(8000.5),
        to64x61(1.05),
        # Position 2 - ETH short
        ETH_ID,
        USDC_ID,
        to64x61(100),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        UST_ID,
        0,
        to64x61(0.05)
    ])
    print("liquidation result alice liquidated...", liquidate_result_alice.result.response[0], " ",
          liquidate_result_alice.result.response[1])

    assert liquidate_result_alice.result.response[1] == str_to_felt(
        "343uofdsjxz")
    assert liquidate_result_alice.result.response[0] == 1

    alice_balance_usdc = await alice.get_balance(USDC_ID).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    assert from64x61(alice_balance_usdc.result.res) == 395.0045

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == -481.295275

    order_state = await alice.get_order_data(orderID_=liquidate_result_alice.result.response[1]).call()
    res4 = list(order_state.result.res)
    print(res4)

@pytest.mark.asyncio
async def test_liquidation_flow(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

    charlie_usdc = to64x61(8000)
    await admin2_signer.send_transaction(admin2, charlie.contract_address, 'set_balance', [USDC_ID, charlie_usdc])

    insurance_balance_before = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance before:", from64x61(
        insurance_balance_before.result.amount))

    alice_curr_balance_before = await alice.get_balance(USDC_ID).call()
    print("alice balance before:", from64x61(
        alice_curr_balance_before.result.res))

    ####### Liquidation Order 1#######
    size = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("0jfds78324sjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(7357.5)
    stopPrice1 = 0
    orderType1 = 3
    position1 = to64x61(2)
    direction1 = 1
    closeOrder1 = 1
    parentOrder1 = str_to_felt("343uofdsjxz")
    leverage1 = to64x61(2)
    liquidatorAddress1 = liquidator.contract_address

    order_id_2 = str_to_felt("sadfjkh2178")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(7357.5)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(2)
    direction2 = 0
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(7357.5)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = liquidator_signer.sign(hash_computed1)
    signed_message2 = charlie_signer.sign(hash_computed2)

    diff1 = to64x61(5000) - execution_price1

    pnl1 = await fixed_math.Math64x61_mul(diff1, size).call()
    net_acc_value = pnl1.result.res + to64x61(5000)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1,
        charlie.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ])

    orderState1 = await alice.get_order_data(orderID_=parentOrder1).call()
    res1 = list(orderState1.result.res)
    print(res1)
    print(from64x61(res1[2]))

    assert res1 == [
        assetID_1,
        collateralID_1,
        to64x61(5000),
        to64x61(5000),
        0,
        0,
        0,
        to64x61(0),
        7,
        to64x61(0),
        to64x61(0),
        leverage1
    ]

    orderState2 = await charlie.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)
    print(res2)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        to64x61(2),
        2,
        to64x61(7357.5),
        to64x61(7357.5),
        leverage2
    ]

    insurance_balance = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance after:", from64x61(
        insurance_balance.result.amount))

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    print("alice balance after", from64x61(alice_curr_balance.result.res))

    account_value = await trading.return_net_acc().call()
    print("account value:", from64x61(account_value.result.res))

    assert from64x61(insurance_balance.result.amount) == from64x61(
        net_acc_value)
    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res


@pytest.mark.asyncio
async def test_liquidation_flow_underwater(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

    ##############################################
    ######## Charlie's liquidation result 1 ##########
    ##############################################

    liquidate_result_charlie = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        charlie.contract_address,
        # 1 Position + 1 Collateral
        2,
        # Position 1 - BTC short
        BTC_ID,
        USDC_ID,
        to64x61(11500),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
    ])
    print("liquidation result of charlie...",
          liquidate_result_charlie.result.response[0], " ", liquidate_result_charlie.result.response[1])

    assert liquidate_result_charlie.result.response[0] == 1
    assert liquidate_result_charlie.result.response[1] == str_to_felt(
        "sadfjkh2178")

    charlie_balance_usdc = await charlie.get_balance(USDC_ID).call()
    print("Charlie usdc balance is...", from64x61(
        charlie_balance_usdc.result.res))

    assert from64x61(charlie_balance_usdc.result.res) == 639.64529

    charlie_maintenance = await liquidate.return_maintenance().call()
    print("Charlie maintenance requirement:",
          from64x61(charlie_maintenance.result.res))

    assert from64x61(charlie_maintenance.result.res) == 1158.80625

    charlie_acc_value = await liquidate.return_acc_value().call()
    print("Charlie acc value:", from64x61(charlie_acc_value.result.res))

    assert from64x61(charlie_acc_value.result.res) == -302.2474455

    ###################

    alice_usdc = to64x61(13000)
    await admin2_signer.send_transaction(admin2, alice.contract_address, 'set_balance', [USDC_ID, alice_usdc])

    await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    
    insurance_balance_before = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance before:", from64x61(
        insurance_balance_before.result.amount))

    charlie_curr_balance_before = await charlie.get_balance(USDC_ID).call()
    print("charlie balance before:", from64x61(
        charlie_curr_balance_before.result.res))

    ####### Liquidation Order 2#######
    size = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("3j432gsd8324sjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(11500)
    stopPrice1 = 0
    orderType1 = 3
    position1 = to64x61(2)
    direction1 = 1
    closeOrder1 = 1
    parentOrder1 = str_to_felt("sadfjkh2178")
    leverage1 = to64x61(2)
    liquidatorAddress1 = liquidator.contract_address

    order_id_2 = str_to_felt("5489sdksjkh2178")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(11500)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(2)
    direction2 = 0
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(11500)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = liquidator_signer.sign(hash_computed1)
    signed_message2 = alice_signer.sign(hash_computed2)

    diff1 = to64x61(7357.5) - execution_price1

    adjusted_price1 = to64x61(7357.5 + from64x61(diff1))
    leveraged_amount_out1 = await fixed_math.Math64x61_mul(adjusted_price1, size).call()
    value_to_be_returned1 = to64x61(7357.5) - leveraged_amount_out1.result.res


    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        charlie.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        alice.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ])

    orderState1 = await charlie.get_order_data(orderID_=parentOrder1).call()
    res1 = list(orderState1.result.res)
    print(res1)
    print(from64x61(res1[2]))

    assert res1 == [
        assetID_1,
        collateralID_1,
        to64x61(7357.5),
        to64x61(7357.5),
        0,
        0,
        0,
        to64x61(0),
        7,
        to64x61(0),
        to64x61(0),
        leverage1
    ]

    orderState2 = await alice.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)
    print(res2)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        to64x61(2),
        2,
        to64x61(11500),
        to64x61(11500),
        leverage2
    ]

    insurance_balance = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance after:", from64x61(
        insurance_balance.result.amount))

    charlie_curr_balance = await charlie.get_balance(USDC_ID).call()
    print("charlie balance after", from64x61(charlie_curr_balance.result.res))

    account_value = await trading.return_net_acc().call()
    print("account value:", from64x61(account_value.result.res))

    assert charlie_curr_balance.result.res == to64x61(0)



@pytest.mark.asyncio
async def test_should_not_allow_non_liquidators(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory
    ##############################################
    ######## Bob's liquidation result 3 ##########
    ##############################################
    assert_revert(lambda: charlie_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        bob.contract_address,
        # 2 Position + 2 Collaterals
        4,
        # Position 1 - BTC long
        BTC_ID,
        USDC_ID,
        to64x61(6000),
        to64x61(1.05),
        # Position 2 -
        #  ETH long
        ETH_ID,
        USDC_ID,
        to64x61(86),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        UST_ID,
        0,
        to64x61(0.05)
    ]))


@pytest.mark.asyncio
async def test_deleveraging_flow(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

    await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    
    eduard_usdc = to64x61(1500)
    await admin2_signer.send_transaction(admin2, eduard.contract_address, 'set_balance', [USDC_ID, eduard_usdc])

    daniel_usdc = to64x61(5500)
    await admin2_signer.send_transaction(admin2, daniel.contract_address, 'set_balance', [USDC_ID, daniel_usdc])

    insurance_balance_before = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance before:", from64x61(
        insurance_balance_before.result.amount))

    ####### Opening of Orders #######
    size = to64x61(5)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("343uofdsjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(5)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(5)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("wer4iljemn")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(5)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = eduard_signer.sign(hash_computed1)
    signed_message2 = daniel_signer.sign(hash_computed2)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        eduard.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 0, 
        daniel.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 1,
    ])

    orderState1 = await eduard.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        position1,
        orderType1,
        direction1,
        to64x61(5),
        2,
        to64x61(1000),
        to64x61(4000),
        leverage1
    ]

    orderState2 = await daniel.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        to64x61(5),
        2,
        to64x61(5000),
        to64x61(0),
        leverage2
    ]

    eduard_list = await eduard.return_array_positions().call()
    eduard_list_parsed = list(eduard_list.result.array_list)

    print("eduard Positions ", eduard_list_parsed)

    daniel_list = await daniel.return_array_positions().call()
    daniel_list_parsed = list(daniel_list.result.array_list)

    print("Daniel Positions ", daniel_list_parsed)

    eduard_list_collaterals = await eduard.return_array_collaterals().call()
    eduard_list_collaterals_parsed = list(
        eduard_list_collaterals.result.array_list)

    print("eduard collaterals :", eduard_list_collaterals_parsed)

    daniel_list_collaterals = await daniel.return_array_collaterals().call()
    daniel_list_collaterals_parsed = list(
        daniel_list_collaterals.result.array_list)

    print("Daniel collaterals :", daniel_list_collaterals_parsed)

    eduard_balance_usdc = await eduard.get_balance(USDC_ID).call()
    print("eduard usdc balance is...", from64x61(
        eduard_balance_usdc.result.res))

    assert from64x61(eduard_balance_usdc.result.res) == 499.03000000000003

    daniel_balance_usdc = await daniel.get_balance(USDC_ID).call()
    print("Daniel usdc balance is...", from64x61(
        daniel_balance_usdc.result.res))

    assert from64x61(daniel_balance_usdc.result.res) == 497.575


    ##############################################
    ######## Check for deleveraging ##########
    ##############################################

    liquidate_result_eduard = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        eduard.contract_address,
        # 1 Position + 1 Collateral
        2,
        # Position 1 - BTC short
        BTC_ID,
        USDC_ID,
        to64x61(1250),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
    ])
    print("liquidation result of eduard...",
          liquidate_result_eduard.result.response[0], " ", liquidate_result_eduard.result.response[1])

    assert liquidate_result_eduard.result.response[0] == 1
    assert liquidate_result_eduard.result.response[1] == str_to_felt(
        "343uofdsjxz")

    eduard_maintenance = await liquidate.return_maintenance().call()
    print("eduard maintenance requirement:",
          from64x61(eduard_maintenance.result.res))

    assert from64x61(eduard_maintenance.result.res) == 393.75

    eduard_acc_value = await liquidate.return_acc_value().call()
    print("eduard acc value:", from64x61(eduard_acc_value.result.res))

    assert from64x61(eduard_acc_value.result.res) == 261.48150000000004

    eduard_amount_to_be_sold = await eduard.get_deleveraged_or_liquidatable_position().call()
    print(eduard_amount_to_be_sold.result)
    print("eduard amount to be sold is...", from64x61(
        eduard_amount_to_be_sold.result.amount_to_be_sold))
    print("eduard amount to be sold is...", eduard_amount_to_be_sold.result.amount_to_be_sold)
    assert from64x61(eduard_amount_to_be_sold.result.amount_to_be_sold) == 1.9454545454545453

    print("eduard Position to be deleveraged is...",
        eduard_amount_to_be_sold.result.order_id)
    assert eduard_amount_to_be_sold.result.order_id == str_to_felt(
        "343uofdsjxz")

    ####### Opening of Deleveraged Order #######
    size2 = to64x61(1.9454545454545453)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("343uofdsswa")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(1250)
    stopPrice3 = 0
    orderType3 = 4
    position3 = to64x61(1.9454545454545453)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1
    leverage3 = to64x61(5)
    liquidatorAddress3 = liquidator.contract_address

    order_id_4 = str_to_felt("rfdgljthi")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(1250)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(1.9454545454545453)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(1250)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = liquidator_signer.sign(hash_computed3)
    signed_message4 = daniel_signer.sign(hash_computed4)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        eduard.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, parentOrder3, 1, 
        daniel.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, parentOrder4, 0,
    ])

    orderState3 = await eduard.get_order_data(orderID_=order_id_1).call()
    res3 = list(orderState3.result.res)
    print("eduard result:", res3)

    assert res3 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        to64x61(5 - 1.9454545454545453),
        orderType1,
        direction1,
        to64x61(5 - 1.9454545454545453),
        5,
        to64x61(1000),
        5858937464320249856000,
        to64x61(3.540909090909091)
    ]

    orderState4 = await daniel.get_order_data(orderID_=order_id_2).call()
    res4 = list(orderState4.result.res)
    print("Daniel result:", res4)

    assert res4 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        to64x61(5 - 1.9454545454545453),
        orderType2,
        direction2,
        to64x61(5 - 1.9454545454545453),
        3,
        7043302282689101825000,
        to64x61(0),
        leverage4
    ]

    eduard_list = await eduard.return_array_positions().call()
    eduard_list_parsed = list(eduard_list.result.array_list)

    print("eduard Positions ", eduard_list_parsed)

    daniel_list = await daniel.return_array_positions().call()
    daniel_list_parsed = list(daniel_list.result.array_list)

    print("Daniel Positions ", daniel_list_parsed)

    eduard_balance_usdc = await eduard.get_balance(USDC_ID).call()
    print("eduard usdc balance is...", from64x61(
        eduard_balance_usdc.result.res))

    assert from64x61(eduard_balance_usdc.result.res) == 499.03000000000003

    daniel_balance_usdc = await daniel.get_balance(USDC_ID).call()
    print("Daniel usdc balance is...", from64x61(
        daniel_balance_usdc.result.res))

    assert from64x61(daniel_balance_usdc.result.res) == 2929.393181818182

    amount_to_be_sold = await eduard.get_amount_to_be_sold(order_id_=order_id_1).call()
    print("Amount to be sold after deleveraging:", from64x61(amount_to_be_sold.result.res))
    assert from64x61(amount_to_be_sold.result.res) == 0


@pytest.mark.asyncio
async def test_liquidation_after_deleveraging_flow(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

    await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [USDC_ID, to64x61(1000000)])

    insurance_balance_before = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance before:", from64x61(
        insurance_balance_before.result.amount))

    eduard_curr_balance_before = await eduard.get_balance(USDC_ID).call()
    print("eduard usdc balance before:", from64x61(
        eduard_curr_balance_before.result.res))

    daniel_curr_balance_before = await daniel.get_balance(USDC_ID).call()
    print("Daniel usdc balance before...", from64x61(
        daniel_curr_balance_before.result.res))

    ##############################################
    ######## Check for liquidation ##########
    ##############################################
    liquidate_result_eduard = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        eduard.contract_address,
        # 1 Position + 1 Collateral
        2,
        # Position 1 - BTC short
        BTC_ID,
        USDC_ID,
        to64x61(1800),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        USDC_ID,
        0,
        to64x61(1.05),
    ])
    print("liquidation result of eduard...",
          liquidate_result_eduard.result.response[0], " ", liquidate_result_eduard.result.response[1])

    assert liquidate_result_eduard.result.response[0] == 1
    assert liquidate_result_eduard.result.response[1] == str_to_felt(
        "343uofdsjxz")

    eduard_maintenance = await liquidate.return_maintenance().call()
    print("eduard maintenance requirement:",
          from64x61(eduard_maintenance.result.res))

    assert from64x61(eduard_maintenance.result.res) == 240.54545454545456

    eduard_acc_value = await liquidate.return_acc_value().call()
    print("eduard acc value:", from64x61(eduard_acc_value.result.res))

    assert from64x61(eduard_acc_value.result.res) == -1502.5185000000001

    eduard_amount_to_be_sold = await eduard.get_deleveraged_or_liquidatable_position().call()
    print(eduard_amount_to_be_sold.result)
    print("eduard amount to be sold is...", from64x61(
        eduard_amount_to_be_sold.result.amount_to_be_sold))
    assert from64x61(eduard_amount_to_be_sold.result.amount_to_be_sold) == 0

    print("eduard Position to be liquidated is...",
        eduard_amount_to_be_sold.result.order_id)
    assert eduard_amount_to_be_sold.result.order_id == str_to_felt("343uofdsjxz")

    eduard_order_data = await eduard.get_order_data(orderID_=str_to_felt("343uofdsjxz")).call()
    res3 = list(eduard_order_data.result.res)
    print("eduard order data:", res3)

    ####### Liquidation Order #######
    size = to64x61(5 - 1.9454545454545453)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("0jfds78324sjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1800)
    stopPrice1 = 0
    orderType1 = 3
    position1 = to64x61(5 - 1.9454545454545453)
    direction1 = 1
    closeOrder1 = 1
    parentOrder1 = str_to_felt("343uofdsjxz")
    leverage1 = to64x61(3.540909090909091)
    liquidatorAddress1 = liquidator.contract_address

    order_id_2 = str_to_felt("sadfjkh2178")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1800)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(5 - 1.9454545454545453)
    direction2 = 0
    closeOrder2 = 1
    parentOrder2 = str_to_felt("wer4iljemn")
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1800)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = liquidator_signer.sign(hash_computed1)
    signed_message2 = daniel_signer.sign(hash_computed2)

    diff1 = to64x61(1000) - execution_price1

    pnl1 = await fixed_math.Math64x61_mul(diff1, size).call()
    net_acc_value = pnl1.result.res + to64x61(1000)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        eduard.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1,
        daniel.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ])

    orderState1 = await eduard.get_order_data(orderID_=parentOrder1).call()
    res1 = list(orderState1.result.res)
    print(res1)
    print(from64x61(res1[2]))

    assert res1 == [
        assetID_1,
        collateralID_1,
        to64x61(1000),
        to64x61(1000),
        to64x61(0),
        0,
        0,
        to64x61(0),
        7,
        to64x61(0),
        to64x61(0),
        leverage1
    ]

    orderState2 = await daniel.get_order_data(orderID_=parentOrder2).call()
    res2 = list(orderState2.result.res)
    print(res2)

    assert res2 == [
        assetID_2,
        collateralID_2,
        to64x61(1000),
        to64x61(1000),
        to64x61(0),
        orderType2,
        1,
        to64x61(0),
        4,
        to64x61(0),
        to64x61(0),
        leverage2
    ]

    insurance_balance = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance after:", from64x61(
        insurance_balance.result.amount))

    eduard_curr_balance = await eduard.get_balance(USDC_ID).call()
    print("eduard balance after", from64x61(eduard_curr_balance.result.res))

    account_value = await trading.return_net_acc().call()
    print("account value after:", from64x61(account_value.result.res))
