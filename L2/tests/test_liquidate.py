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
dave_signer = Signer(123456789987654326)

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
    print("In 64x61", to64x61(0.041891891891891894))
    print("In decimal", from64x61(172938225691027040))
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin1_signer.public_key, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin2_signer.public_key, 0]
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

    asset = await starknet.deploy(
        "contracts/Asset.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
            0
        ]
    )

    registry = await starknet.deploy(
        "contracts/AuthorizedRegistry.cairo",
        constructor_calldata=[
            adminAuth.contract_address
        ]
    )

    alice = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            alice_signer.public_key,
            registry.contract_address
        ]
    )

    bob = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            bob_signer.public_key,
            registry.contract_address
        ]
    )

    charlie = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            charlie_signer.public_key,
            registry.contract_address
        ]
    )

    dave = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            dave_signer.public_key,
            registry.contract_address
        ]
    )

    fixed_math = await starknet.deploy(
        "contracts/Math_64x61.cairo",
        constructor_calldata=[
        ]
    )

    holding = await starknet.deploy(
        "contracts/Holding.cairo",
        constructor_calldata=[adminAuth.contract_address]
    )

    feeBalance = await starknet.deploy(
        "contracts/FeeBalance.cairo",
        constructor_calldata=[adminAuth.contract_address]
    )

    market = await starknet.deploy(
        "contracts/Markets.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
            asset.contract_address
        ]
    )

    liquidityFund = await starknet.deploy(
        "contracts/LiquidityFund.cairo",
        constructor_calldata=[
            adminAuth.contract_address
        ]
    )

    trading = await starknet.deploy(
        "contracts/Trading.cairo",
        constructor_calldata=[
            asset.contract_address,
            fees.contract_address,
            holding.contract_address,
            feeBalance.contract_address,
            market.contract_address,
            liquidityFund.contract_address
        ]
    )

    liquidate = await starknet.deploy(
        "contracts/Liquidate.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
            asset.contract_address
        ]
    )

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Add assets
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [BTC_ID, 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ETH_ID, 0, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [UST_ID, 0, str_to_felt("UST"), str_to_felt("UST"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000])

    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [BTC_USD_ID, BTC_ID, USDC_ID, 0, 1])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [ETH_USD_ID, ETH_ID, USDC_ID, 0, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

    # Add the deployed trading contract to the list of trusted contracts in the registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_registry', [trading.contract_address, 3, 1])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Authorize the deployed trading contract to add/remove funds from Holding
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'update_trading_address', [trading.contract_address])

    # Authorize the deployed trading contract to add/remove funds from Liquidity fund
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'update_trading_address', [trading.contract_address])

    # Fund the Liquidity fund contract
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Authorize the deployed trading contract to add trading fees of each order in FeeBalance Contract
    await admin1_signer.send_transaction(admin1, feeBalance.contract_address, 'update_caller_address', [trading.contract_address])

    # Set the balance of admin1 and admin2
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, liquidate


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, liquidate = adminAuth_factory

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

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1, leverage1,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2, leverage2
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

    ##############################################
    ######## Alice's liquidation result 1 ##########
    ##############################################

    liquidate_result_alice = await dave_signer.send_transaction(dave, liquidate.contract_address, "check_liquidation", [
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

    alice_maintanence = await liquidate.return_maintanence().call()
    print("Alice maintanence requirement:",
          from64x61(alice_maintanence.result.res))

    assert from64x61(alice_maintanence.result.res) == 787.5

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == 5741

    ##############################################
    ######## Bob's liquidation result 1 ##########
    ##############################################

    liquidate_result_bob = await dave_signer.send_transaction(dave, liquidate.contract_address, "check_liquidation", [
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

    assert liquidate_result_bob.result.response[1] == order_id_2

    bob_balance_usdc = await bob.get_balance(USDC_ID).call()
    print("Bob usdc balance is...", from64x61(bob_balance_usdc.result.res))

    assert from64x61(bob_balance_usdc.result.res) == 880

    bob_balance_ust = await bob.get_balance(UST_ID).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintanence = await liquidate.return_maintanence().call()
    print("Bob maintanence requirement:",
          from64x61(bob_maintanence.result.res))

    assert from64x61(bob_maintanence.result.res) == 787.5

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

    execution_price2 = to64x61(100)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3, leverage3,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4, leverage4
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

    liquidate_result_alice = await dave_signer.send_transaction(dave, liquidate.contract_address, "check_liquidation", [
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

    assert liquidate_result_alice.result.response[1] == order_id_3

    alice_balance_usdc = await alice.get_balance(USDC_ID).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    assert from64x61(alice_balance_usdc.result.res) == 317.6

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintanence = await liquidate.return_maintanence().call()
    print("Alice maintanence requirement:",
          from64x61(alice_maintanence.result.res))

    assert from64x61(alice_maintanence.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    assert from64x61(alice_acc_value.result.res) == 5738.4800000000005

    ##############################################
    ######## Bob's liquidation result 2 ##########
    ##############################################
    liquidate_result_bob = await dave_signer.send_transaction(dave, liquidate.contract_address, "check_liquidation", [
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

    assert liquidate_result_bob.result.response[1] == order_id_4

    bob_balance_usdc = await bob.get_balance(USDC_ID).call()
    print("Bob usdc balance is...", from64x61(bob_balance_usdc.result.res))

    assert from64x61(bob_balance_usdc.result.res) == 776.4

    bob_balance_ust = await bob.get_balance(UST_ID).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintanence = await liquidate.return_maintanence().call()
    print("Bob maintanence requirement:",
          from64x61(bob_maintanence.result.res))

    assert from64x61(bob_maintanence.result.res) == 811.125

    bob_acc_value = await liquidate.return_acc_value().call()
    print("bob acc value:", from64x61(bob_acc_value.result.res))

    assert from64x61(bob_acc_value.result.res) == 6445.22


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, liquidate = adminAuth_factory
    ##############################################
    ######## Alice's liquidation result 3 ##########
    ##############################################

    liquidate_result_alice = await dave_signer.send_transaction(dave, liquidate.contract_address, "check_liquidation", [
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
    print("liquidation resul...", liquidate_result_alice.result.response[0], " ",
          liquidate_result_alice.result.response[1])

    # assert liquidate_result_alice.result.response[1] == order_id_3

    alice_balance_usdc = await alice.get_balance(USDC_ID).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    # assert from64x61(alice_balance_usdc.result.res) == 317.6

    alice_balance_ust = await alice.get_balance(UST_ID).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    # assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintanence = await liquidate.return_maintanence().call()
    print("Alice maintanence requirement:",
          from64x61(alice_maintanence.result.res))

    # assert from64x61(alice_maintanence.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    order_state = await alice.get_order_data(orderID_=liquidate_result_alice.result.response[1]).call()
    res4 = list(order_state.result.res)

    print(res4)
