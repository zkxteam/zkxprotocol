from copyreg import constructor
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, convertList

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
liquidator_signer = Signer(123456789987654326)

long_trading_fees = to64x61(0.012)
short_trading_fees = to64x61(0.008)

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
        constructor_calldata=[admin1_signer.public_key, 0, 1]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin2_signer.public_key, 0, 1]
    )

    adminAuth = await starknet.deploy(
        "contracts/AdminAuth.cairo",
        constructor_calldata=[
            admin1.contract_address,
            admin2.contract_address
        ]
    )

    fees = await starknet.deploy(
        "contracts/TradingFees.cairo",
        constructor_calldata=[
            long_trading_fees,
            short_trading_fees,
            adminAuth.contract_address,
            0, 0, 1,
            100, 100, 3,
            500, 500, 4,
            1, 0, 0,
            1, 1, 0,
            1, 1, 1
        ]
    )

    registry = await starknet.deploy(
        "contracts/AuthorizedRegistry.cairo",
        constructor_calldata=[
            adminAuth.contract_address
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
            1
        ]
    )

    bob = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            bob_signer.public_key,
            registry.contract_address,
            1
        ]
    )

    charlie = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            charlie_signer.public_key,
            registry.contract_address,
            1
        ]
    )

    liquidator = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            liquidator_signer.public_key,
            registry.contract_address,
            1
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

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [4, 1, fees.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [5, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [6, 1, feeBalance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [7, 1, holding.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [9, 1, liquidityFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [10, 1, insuranceFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [11, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [13, 1, liquidator.contract_address])

    # Add assets
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [BTC_ID, 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ETH_ID, 0, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [UST_ID, 0, str_to_felt("UST"), str_to_felt("UST"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])

    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [BTC_USD_ID, BTC_ID, USDC_ID, 0, 1])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [ETH_USD_ID, ETH_ID, USDC_ID, 0, 1])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Fund the Liquidity fund contract
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Set the balance of admin1 and admin2
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

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
    orderType1 = 0
    position1 = to64x61(2)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(2)
    isLiquidation1 = 0
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("wer4iljemn")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(5000)
    orderType2 = 0
    position2 = to64x61(2)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    isLiquidation2 = 0
    liquidatorAddress2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, orderType1, position1, direction1, closeOrder1, leverage1, isLiquidation1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, orderType2, position2, direction2, closeOrder2, leverage2, isLiquidation2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1, leverage1, isLiquidation1, liquidatorAddress1,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2, leverage2, isLiquidation2, liquidatorAddress2,
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
        to64x61(5000)
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
        to64x61(5000)
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

    assert from64x61(alice_balance_usdc.result.res) == 420

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 787.5

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == 5741

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

    assert from64x61(bob_balance_usdc.result.res) == 880

    bob_balance_ust = await bob.get_balance(UST_ID).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintenance = await liquidate.return_maintenance().call()
    print("Bob maintenance requirement:",
          from64x61(bob_maintenance.result.res))

    assert from64x61(bob_maintenance.result.res) == 787.5

    bob_acc_value = await liquidate.return_acc_value().call()
    print("bob acc value:", from64x61(bob_acc_value.result.res))

    assert from64x61(bob_acc_value.result.res) == 6449

    ###### Opening of Orders 2 #######
    size2 = to64x61(3)
    marketID_2 = ETH_USD_ID

    order_id_3 = str_to_felt("erwf6s2jxz")
    assetID_3 = ETH_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(100)
    orderType3 = 0
    position3 = to64x61(3)
    direction3 = 0
    closeOrder3 = 0
    parentOrder3 = 0
    leverage3 = to64x61(3)
    isLiquidation3 = 0
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("rfdgljemn")
    assetID_4 = ETH_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(100)
    orderType4 = 0
    position4 = to64x61(3)
    direction4 = 1
    closeOrder4 = 0
    parentOrder4 = 0
    leverage4 = to64x61(3)
    isLiquidation4 = 0
    liquidatorAddress4 = 0

    execution_price2 = to64x61(100)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, orderType3, position3, direction3, closeOrder3, leverage3, isLiquidation3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, orderType4, position4, direction4, closeOrder4, leverage4, isLiquidation4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3, leverage3, isLiquidation3, liquidatorAddress3,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4, leverage4, isLiquidation4, liquidatorAddress4,
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
        to64x61(200)
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
        to64x61(200)
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

    assert from64x61(alice_balance_usdc.result.res) == 317.6

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == 5738.4800000000005

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

    assert from64x61(bob_balance_usdc.result.res) == 776.4

    bob_balance_ust = await bob.get_balance(UST_ID).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintenance = await liquidate.return_maintenance().call()
    print("Bob maintenance requirement:",
          from64x61(bob_maintenance.result.res))

    assert from64x61(bob_maintenance.result.res) == 811.125

    bob_acc_value = await liquidate.return_acc_value().call()
    print("bob acc value:", from64x61(bob_acc_value.result.res))

    assert from64x61(bob_acc_value.result.res) == 6445.22


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory
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
        to64x61(7357.5),
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

    assert from64x61(alice_balance_usdc.result.res) == 317.6

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == 787.73

    order_state = await alice.get_order_data(orderID_=liquidate_result_alice.result.response[1]).call()
    res4 = list(order_state.result.res)

    print(res4)


@pytest.mark.asyncio
async def test_liquidation_flow(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

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
    orderType1 = 0
    position1 = to64x61(2)
    direction1 = 1
    closeOrder1 = 1
    parentOrder1 = str_to_felt("343uofdsjxz")
    leverage1 = to64x61(2)
    isLiquidation1 = 1
    liquidatorAddress1 = liquidator.contract_address

    order_id_2 = str_to_felt("sadfjkh2178")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(7357.5)
    orderType2 = 0
    position2 = to64x61(2)
    direction2 = 0
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    isLiquidation2 = 0
    liquidatorAddress2 = 0

    execution_price1 = to64x61(7357.5)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, orderType1, position1, direction1, closeOrder1, leverage1, isLiquidation1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, orderType2, position2, direction2, closeOrder2, leverage2, isLiquidation2)

    signed_message1 = liquidator_signer.sign(hash_computed1)
    signed_message2 = charlie_signer.sign(hash_computed2)

    diff1 = to64x61(5000) - execution_price1

    pnl1 = await fixed_math.mul_fp(diff1, size).call()
    net_acc_value = pnl1.result.res + to64x61(5000)

    size_without_leverage2 = await fixed_math.div_fp(size, leverage2).call()
    amount2 = await fixed_math.mul_fp(execution_price1, size_without_leverage2.result.res).call()
    amount_for_fee2 = await fixed_math.mul_fp(execution_price1, size).call()
    fees2 = await fixed_math.mul_fp(amount_for_fee2.result.res, short_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1, leverage1, isLiquidation1, liquidatorAddress1,
        charlie.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2, leverage2, isLiquidation2, liquidatorAddress2,
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
        orderType1,
        0,
        to64x61(0),
        6,
        to64x61(0),
        to64x61(0)
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
        to64x61(7357.5)
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
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

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

    assert from64x61(charlie_balance_usdc.result.res) == 524.78

    charlie_maintenance = await liquidate.return_maintenance().call()
    print("Charlie maintenance requirement:",
          from64x61(charlie_maintenance.result.res))

    assert from64x61(charlie_maintenance.result.res) == 1158.80625

    charlie_acc_value = await liquidate.return_acc_value().call()
    print("Charlie acc value:", from64x61(charlie_acc_value.result.res))

    assert from64x61(charlie_acc_value.result.res) == -422.856

    ###################

    alice_usdc = to64x61(13000)
    await admin2_signer.send_transaction(admin2, alice.contract_address, 'set_balance', [USDC_ID, alice_usdc])

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
    orderType1 = 0
    position1 = to64x61(2)
    direction1 = 1
    closeOrder1 = 1
    parentOrder1 = str_to_felt("sadfjkh2178")
    leverage1 = to64x61(2)
    isLiquidation1 = 1
    liquidatorAddress1 = liquidator.contract_address

    order_id_2 = str_to_felt("5489sdksjkh2178")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(11500)
    orderType2 = 0
    position2 = to64x61(2)
    direction2 = 0
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    isLiquidation2 = 0
    liquidatorAddress2 = 0

    execution_price1 = to64x61(11500)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, orderType1, position1, direction1, closeOrder1, leverage1, isLiquidation1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, orderType2, position2, direction2, closeOrder2, leverage2, isLiquidation2)

    signed_message1 = liquidator_signer.sign(hash_computed1)
    signed_message2 = alice_signer.sign(hash_computed2)

    diff1 = to64x61(7357.5) - execution_price1

    adjusted_price1 = to64x61(7357.5 + from64x61(diff1))
    leveraged_amount_out1 = await fixed_math.mul_fp(adjusted_price1, size).call()
    value_to_be_returned1 = to64x61(7357.5) - leveraged_amount_out1.result.res


    res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        charlie.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1, leverage1, isLiquidation1, liquidatorAddress1,
        alice.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2, leverage2, isLiquidation2, liquidatorAddress2,
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
        orderType1,
        0,
        to64x61(0),
        6,
        to64x61(0),
        to64x61(0)
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
        to64x61(11500)
    ]

    insurance_balance = await insuranceFund.balance(asset_id_=USDC_ID).call()
    print("insurance balance after:", from64x61(
        insurance_balance.result.amount))

    charlie_curr_balance = await charlie.get_balance(USDC_ID).call()
    print("charlie balance after", from64x61(charlie_curr_balance.result.res))

    account_value = await trading.return_net_acc().call()
    print("account value:", from64x61(account_value.result.res))

    assert from64x61(insurance_balance.result.amount) == from64x61(
        insurance_balance_before.result.amount - value_to_be_returned1)
    assert charlie_curr_balance.result.res == to64x61(0)



@pytest.mark.asyncio
async def test_should_not_allow_non_liquidators(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory
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