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

    trading = await starknet.deploy(
        "contracts/Trading.cairo",
        constructor_calldata=[
            asset.contract_address,
            fees.contract_address,
            holding.contract_address,
            feeBalance.contract_address,
            market.contract_address
        ]
    )

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Add assets
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ BTC_ID, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ ETH_ID, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ USDC_ID, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ UST_ID, str_to_felt("UST"), str_to_felt("UST"), 0, 1, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ DOGE_ID, str_to_felt("DOGE"), str_to_felt("DOGECOIN"), 0, 0, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ TSLA_ID, str_to_felt("TESLA"), str_to_felt("TESLA MOTORS"), 1, 0, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [ BTC_USD_ID, BTC_ID, USDC_ID, 0, 1])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [ ETH_USD_ID, ETH_ID, USDC_ID, 0, 1])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [ TSLA_USD_ID, TSLA_ID, USDC_ID, 0, 0])

    
    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

    # Add the deployed trading contract to the list of trusted contracts in the registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_registry', [ trading.contract_address, 3, 1])

    # Fund the Holding contract 
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Authorize the deployed trading contract to add/remove funds from Holding
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'update_trading_address', [trading.contract_address])

    # Authorize the deployed trading contract to add trading fees of each order in FeeBalance Contract
    await admin1_signer.send_transaction(admin1, feeBalance.contract_address, 'update_caller_address', [trading.contract_address])
    
    # Set the balance of admin1 and admin2 
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)]) 
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)]) 
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance

@pytest.mark.asyncio
async def test_set_balance_for_testing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    bob_curr_balance = await bob.get_balance(USDC_ID).call()

    assert alice_curr_balance.result.res == alice_balance
    assert bob_curr_balance.result.res == bob_balance


@pytest.mark.asyncio
async def test_revert_balance_low(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100)
    bob_balance = to64x61(100)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("pqlkzc3434")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(10789)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("p21pdfs12mfd")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(10789)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,  price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,  price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert_revert( lambda: dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 

@pytest.mark.asyncio
async def test_revert_if_market_order_2percent_deviation(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("kzwerl2kfsm")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1000)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("asl19uxkzck")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1000)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1021)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    await assert_revert(dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 


@pytest.mark.asyncio
async def test_revert_if_bad_limit_order_long(adminAuth_factory):
    AdminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("ls23ksfl2fd")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1000)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("sdfk23kdfsl1")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1000)
    orderType2 = 1
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1001)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    await assert_revert(dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 


@pytest.mark.asyncio
async def test_revert_if_bad_limit_order_short(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("kmzm2ms62fds")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1000)
    orderType1 = 1
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("9sk2nsk2llj")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1000)
    orderType2 = 1
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(999)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    await assert_revert(dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 

@pytest.mark.asyncio
async def test_revert_if_order_mismatch(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("jciow4k234")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("sdfk32lvfl")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1078)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 0
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()


    await assert_revert( dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 


@pytest.mark.asyncio
async def test_revert_if_asset_not_tradable(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = TSLA_USD_ID

    order_id_1 = str_to_felt("w3godgvx323af")
    assetID_1 = TSLA_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("fj45g324dfsg")
    assetID_2 = TSLA_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1078)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    await assert_revert( dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 

@pytest.mark.asyncio
async def test_revert_if_collateral_mismatch(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [UST_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_UST_before = await bob.get_balance(assetID_ = UST_ID).call()

    

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("wqelvqwe23")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("34ksdfmvcv")
    assetID_2 = BTC_ID
    collateralID_2 = UST_ID
    price2 = to64x61(1078)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,  price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,  price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()


    await assert_revert( dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_UST = await bob.get_balance(assetID_ = UST_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert bob_curr_balance_UST.result.res == bob_curr_balance_UST_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee
   

@pytest.mark.asyncio
async def test_revert_if_asset_mismatch(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("wqelvqwe23")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("34ksdfmvcv")
    assetID_2 = ETH_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1078)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,  price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,  price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()


    await assert_revert( dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee
   
@pytest.mark.asyncio
async def test_revert_wrong_signature(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(1000000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("y7hi83kjhr")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(10789)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("329dsfjvcx9u")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(10789)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()

    orderState1 = await alice.get_order_data(orderID_ = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size, 
        1
    ]

    orderState2 = await bob.get_order_data(orderID_ = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert list(res2) == [
        assetID_2,
        collateralID_2,
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        size, 
        1
    ]

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + total_amount1 + total_amount2 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee + fees1.result.res
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee + fees2.result.res
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee + fees1.result.res + fees2.result.res 

    ##### Closing Of Orders ########
    size2 = to64x61(2)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("jd7yhu21")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(11000)
    orderType3 = 0
    position3 = to64x61(4)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1

    order_id_4 = str_to_felt("xzkw9212")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(11000)
    orderType4 = 0
    position4 = to64x61(3)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2

    execution_price2 = to64x61(11000)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4)
  
    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    assert_revert( lambda: dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message3[0], signed_message3[1], order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ]))

    orderState3 = await alice.get_order_data(orderID_ = order_id_1).call()
    res3 = list(orderState3.result.res)
    assert res3 == res1


    orderState4 = await bob.get_order_data(orderID_ = order_id_2).call()
    res4 = list(orderState4.result.res)
    assert res4 == res2

    alice_curr_balance_after = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_after = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance_after = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    
    assert holdingBalance_after.result.amount == holdingBalance.result.amount 
    assert alice_curr_balance_after.result.res ==  alice_curr_balance.result.res 
    assert bob_curr_balance_after.result.res == bob_curr_balance.result.res 
    assert alice_total_fees_after.result.fee  == alice_total_fees.result.fee  
    assert bob_total_fees_after.result.fee  == bob_total_fees.result.fee  
    assert feeBalance_after.result.fee  == feeBalance_curr.result.fee  




@pytest.mark.asyncio
async def test_opening_and_closing_full_orders(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(USDC_ID).call()

    ####### Opening of Orders #######
    size = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("343uofdsjnv")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("wer4iljerw")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(5000)
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()


    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_1, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])

    orderState1 = await alice.get_order_data(orderID_ = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size, 
        2
    ]

    orderState2 = await bob.get_order_data(orderID_ = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        size, 
        2
    ]

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    bob_curr_balance = await bob.get_balance(USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + total_amount1 + total_amount2 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee + fees1.result.res
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee + fees2.result.res
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee + fees1.result.res + fees2.result.res 
    
    #### Closing Of Orders ########
    size2 = to64x61(1)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("rlbrj4hd")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(6000)
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1

    order_id_4 = str_to_felt("tew2334")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(6000)
    orderType4 = 0
    position4 = to64x61(1)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4)
    
    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    amount2 = await fixed_math.mul_fp(execution_price2, size).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, short_trading_fees).call()
    total_amount2 = amount2.result.res - fees2.result.res

    pnl = execution_price2 - execution_price1
    adjusted_price = execution_price1 - pnl
    amount1 = await fixed_math.mul_fp(adjusted_price, size).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, long_trading_fees).call()
    total_amount1 = amount1.result.res - fees1.result.res

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message4[0], signed_message4[1], order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ])



    orderState3 = await alice.get_order_data(orderID_ = order_id_1).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3,
        collateralID_3,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        0, 
        4
    ]

    orderState4 = await bob.get_order_data(orderID_ = order_id_2).call()
    res4 = list(orderState4.result.res)


    assert res4 == [
        assetID_4,
        collateralID_4,
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        0, 
        4
    ]

    alice_curr_balance_after = await alice.get_balance(collateralID_3).call()
    bob_curr_balance_after = await bob.get_balance(collateralID_4).call()
    holdingBalance_after = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    
    assert holdingBalance_after.result.amount == holdingBalance.result.amount - total_amount1 - total_amount2 
    assert alice_curr_balance_after.result.res ==  alice_curr_balance.result.res + total_amount1
    assert bob_curr_balance_after.result.res == bob_curr_balance.result.res + total_amount2
    assert alice_total_fees_after.result.fee  == alice_total_fees.result.fee  + fees1.result.res
    assert bob_total_fees_after.result.fee  == bob_total_fees.result.fee  + fees2.result.res
    assert feeBalance_after.result.fee  == feeBalance_curr.result.fee  + fees1.result.res + fees2.result.res 



@pytest.mark.asyncio
async def test_opening_and_closing_partial_orders(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance   = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size = to64x61(0.3)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("gfdg324fdsjnv")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    orderType1 = 0
    position1 = to64x61(0.5)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("ert8vckj34rw")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(5000)
    orderType2 = 0
    position2 = to64x61(0.3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, position2).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2

    orderState1 = await alice.get_order_data(orderID_ = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size, 
        1
    ]

    orderState2 = await bob.get_order_data(orderID_ = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        position2, 
        2
    ]

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + total_amount1 + total_amount2 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee + fees1.result.res
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee + fees2.result.res
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee + fees1.result.res + fees2.result.res 
    
    #### Closing Of Orders ########
    size2 = to64x61(0.3)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("314df3ghd")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(6000)
    orderType3 = 0
    position3 = to64x61(0.3)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1

    order_id_4 = str_to_felt("fdswrf4tdsag")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(6000)
    orderType4 = 0
    position4 = to64x61(0.3)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4)
    
    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    amount2 = await fixed_math.mul_fp(execution_price2, position4).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, short_trading_fees).call()
    total_amount2 = amount2.result.res - fees2.result.res

    pnl = execution_price2 - execution_price1
    adjusted_price = execution_price1 - pnl
    amount1 = await fixed_math.mul_fp(adjusted_price, position3).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, long_trading_fees).call()
    total_amount1 = amount1.result.res - fees1.result.res

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message4[0], signed_message4[1], order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ])



    orderState3 = await alice.get_order_data(orderID_ = order_id_1).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3,
        collateralID_3,
        price1,
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        0, 
        4
    ]

    orderState4 = await bob.get_order_data(orderID_ = order_id_2).call()
    res4 = list(orderState4.result.res)

    assert res4 == [
        assetID_4,
        collateralID_4,
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        0, 
        4
    ]

    alice_curr_balance_after = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_after = await bob.get_balance(assetID_ = USDC_ID).call()
    holdingBalance_after = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    
    assert holdingBalance_after.result.amount == holdingBalance.result.amount - total_amount1 - total_amount2 
    assert alice_curr_balance_after.result.res ==  alice_curr_balance.result.res + total_amount1
    assert bob_curr_balance_after.result.res == bob_curr_balance.result.res + total_amount2
    assert alice_total_fees_after.result.fee  == alice_total_fees.result.fee  + fees1.result.res
    assert bob_total_fees_after.result.fee  == bob_total_fees.result.fee  + fees2.result.res
    assert feeBalance_after.result.fee  == feeBalance_curr.result.fee  + fees1.result.res + fees2.result.res 
    

  

@pytest.mark.asyncio
async def test_three_orders_in_a_batch(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)
    charlie_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance]) 
    await admin2_signer.send_transaction(admin2, charlie.contract_address, 'set_balance', [USDC_ID, charlie_balance]) 

    alice_curr_balance_before = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_ = USDC_ID).call()
    charlie_curr_balance_before = await charlie.get_balance(assetID_ = USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(4)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("asdlfkjaf")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(9325.2432042)
    orderType1 = 0
    position1 = to64x61(5)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("fdser34iu45g")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(9325.03424)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    order_id_3 = str_to_felt("3dfw32423rv")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(9324.43)
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 0
    parentOrder3 = 0

    execution_price1 = to64x61(9325)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2)
    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)
    signed_message3 = charlie_signer.sign(hash_computed3)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, position2).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    amount3 = await fixed_math.mul_fp(execution_price1, position3).call()
    fees3 = await fixed_math.mul_fp(amount3.result.res, long_trading_fees).call()
    total_amount3 = amount3.result.res + fees3.result.res
    
    holdingBalance_before = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    charlie_total_fees_before = await feeBalance.get_user_fee(address = charlie.contract_address, assetID_ = USDC_ID).call()


    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        3,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2,
        charlie.contract_address, signed_message3[0], signed_message3[1], order_id_3, assetID_3, collateralID_3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3
    ])

    orderState1 = await alice.get_order_data(orderID_ = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1, 
        collateralID_1,
        price1,
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size1, 
        1
    ]

    orderState2 = await bob.get_order_data(orderID_ = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2, 
        collateralID_2,
        price2,
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        position2, 
        2
    ]

    orderState3 = await charlie.get_order_data(orderID_ = order_id_3).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3, 
        collateralID_3,
        price3, 
        execution_price1, 
        position3,
        orderType3,
        direction3, 
        position3, 
        2
    ]

    alice_curr_balance = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_ = USDC_ID).call()
    charlie_curr_balance = await charlie.get_balance(assetID_ = USDC_ID).call()
    holdingBalance = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    charlie_total_fees = await feeBalance.get_user_fee(address = charlie.contract_address, assetID_ = USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2
    assert charlie_curr_balance.result.res == charlie_curr_balance_before.result.res - total_amount3
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + total_amount1 + total_amount2 + total_amount3
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee + fees1.result.res
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee + fees2.result.res
    assert charlie_total_fees.result.fee == charlie_total_fees_before.result.fee + fees3.result.res
    assert feeBalance_curr.result.fee == feeBalance_before.result.fee + fees1.result.res + fees2.result.res + fees3.result.res



    ##### Closing Of Orders ########
    size2 = to64x61(4)
    marketID_2 = BTC_USD_ID

    order_id_4 = str_to_felt("er8u324hj4hd")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(12000.2432042)
    orderType4 = 0
    position4 = to64x61(4)
    direction4 = 1
    closeOrder4 = 1
    parentOrder4 = order_id_1

    order_id_5 = str_to_felt("5324k34")
    assetID_5 = BTC_ID
    collateralID_5 = USDC_ID
    price5 = to64x61(12032.9803)
    orderType5 = 0
    position5 = to64x61(3)
    direction5 = 0
    closeOrder5 = 1
    parentOrder5 = order_id_2

    order_id_6 = str_to_felt("3df324gds34")
    assetID_6 = BTC_ID
    collateralID_6 = USDC_ID
    price6 = to64x61(12010.2610396)
    orderType6 = 0
    position6 = to64x61(1)
    direction6 = 0
    closeOrder6 = 1
    parentOrder6 = order_id_3

    execution_price2 = to64x61(12025.432)

    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4)
    hash_computed5 = hash_order(order_id_5, assetID_5, collateralID_5, price5, orderType5, position5, direction5, closeOrder5)
    hash_computed6 = hash_order(order_id_6, assetID_6, collateralID_6, price6, orderType6, position6, direction6, closeOrder6)

    signed_message4 = alice_signer.sign(hash_computed4)
    signed_message5 = bob_signer.sign(hash_computed5)
    signed_message6 = charlie_signer.sign(hash_computed6)

    pnl = execution_price2 - execution_price1
    adjusted_price = execution_price1 - pnl
    amount1 = await fixed_math.mul_fp(adjusted_price, position4).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, long_trading_fees).call()
    total_amount1 = amount1.result.res - fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price2, position5).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, short_trading_fees).call()
    total_amount2 = amount2.result.res - fees2.result.res

    amount3 = await fixed_math.mul_fp(execution_price2, position6).call()
    fees3 = await fixed_math.mul_fp(amount3.result.res, short_trading_fees).call()
    total_amount3 = amount3.result.res - fees3.result.res

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        3,
        alice.contract_address, signed_message4[0], signed_message4[1], order_id_4, assetID_4, collateralID_4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4,
        bob.contract_address, signed_message5[0], signed_message5[1], order_id_5, assetID_5, collateralID_5, price5, orderType5, position5, direction5, closeOrder5, parentOrder5,
        charlie.contract_address, signed_message6[0], signed_message6[1], order_id_6, assetID_6, collateralID_6, price6, orderType6, position6, direction6, closeOrder6, parentOrder6
    ])

    orderState4 = await alice.get_order_data(orderID_ = order_id_1).call()
    res4 = list(orderState4.result.res)
    assert res4 == [
        assetID_4,
        collateralID_4,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        0, 
        4
    ]

    orderState5 = await bob.get_order_data(orderID_ = order_id_2).call()
    res5 = list(orderState5.result.res)
    assert res5 == [
        assetID_5,
        collateralID_5,
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        0, 
        4
    ]

    orderState6 = await charlie.get_order_data(orderID_ = order_id_3).call()
    res6 = list(orderState6.result.res)
    assert res6 == [
        assetID_6,
        collateralID_6,
        price3, 
        execution_price1, 
        position3,
        orderType3,
        direction3, 
        0, 
        4
    ]

    alice_curr_balance_after = await alice.get_balance(assetID_ = USDC_ID).call()
    bob_curr_balance_after = await bob.get_balance(assetID_ = USDC_ID).call()
    charlie_curr_balance_after = await charlie.get_balance(assetID_ = USDC_ID).call()
    holdingBalance_after = await holding.balance(assetID_ = USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_ = USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address, assetID_ = USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address, assetID_ = USDC_ID).call()
    charlie_total_fees_after= await feeBalance.get_user_fee(address = charlie.contract_address, assetID_ = USDC_ID).call()

    assert holdingBalance_after.result.amount == holdingBalance.result.amount - total_amount1 - total_amount2 - total_amount3
    assert alice_curr_balance_after.result.res ==  alice_curr_balance.result.res + total_amount1
    assert bob_curr_balance_after.result.res == bob_curr_balance.result.res + total_amount2
    assert charlie_curr_balance_after.result.res == charlie_curr_balance.result.res + total_amount3
    assert alice_total_fees_after.result.fee == alice_total_fees.result.fee  + fees1.result.res
    assert bob_total_fees_after.result.fee == bob_total_fees.result.fee  + fees2.result.res
    assert charlie_total_fees_after.result.fee == charlie_total_fees.result.fee  + fees3.result.res
    assert feeBalance_after.result.fee  == feeBalance_curr.result.fee  + fees1.result.res + fees2.result.res + fees3.result.res
    
    