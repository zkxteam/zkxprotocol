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
bob_signer = Signer(123456789987654323)
charlie_signer = Signer(123456789987654323)
dave_signer = Signer(123456789987654323)

long_trading_fees = to64x61(0.012)
short_trading_fees = to64x61(0.008)

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
            adminAuth.contract_address
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

    trading = await starknet.deploy(
        "contracts/Trading.cairo",
        constructor_calldata=[
            asset.contract_address,
            fees.contract_address,
            holding.contract_address,
            feeBalance.contract_address
        ]
    )

    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    # Admin1 gets the access to update the Authorized Registry Contract
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_registry', [ trading.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [str_to_felt("32f0406jz7qj8"), to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [str_to_felt("65ksgn23nv"), to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'update_trading_address', [trading.contract_address])
    await admin1_signer.send_transaction(admin1, feeBalance.contract_address, 'update_caller_address', [trading.contract_address])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), str_to_felt("BTC"), str_to_felt("Bitcoin"), 1])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ str_to_felt("65ksgn23nv"), str_to_felt("ETH"), str_to_felt("Etherum"), 1])
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [to64x61(1000000)]) 
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [to64x61(1000000)]) 
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance

@pytest.mark.asyncio
async def test_set_balance_for_testing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

 
    assert alice_curr_balance.result.res == alice_balance
    assert bob_curr_balance.result.res == bob_balance

async def test_set_allowance_for_testing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(1000000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(100000)
    bob_approved = to64x61(100000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

@pytest.mark.asyncio
async def test_revert_approved_amount_low(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(100)
    bob_approved = to64x61(100)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(2)

    order_id_1 = str_to_felt("pqlkzc3434")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(10789)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("p21pdfs12mfd")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(10789)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()

    assert_revert( lambda: dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(100000)
    bob_approved = to64x61(100000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(2)

    order_id_1 = str_to_felt("kzwerl2kfsm")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(1000)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("asl19uxkzck")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(1000)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1021)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()

    await assert_revert(dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 


@pytest.mark.asyncio
async def test_revert_if_bad_limit_order_long(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(100000)
    bob_approved = to64x61(100000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(2)

    order_id_1 = str_to_felt("ls23ksfl2fd")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(1000)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("sdfk23kdfsl1")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(1000)
    orderType2 = 1
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1001)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()

    await assert_revert(dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(100000)
    bob_approved = to64x61(100000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(2)

    order_id_1 = str_to_felt("kmzm2ms62fds")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(1000)
    orderType1 = 1
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("9sk2nsk2llj")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(1000)
    orderType2 = 1
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(999)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()

    await assert_revert(dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(1000000)
    bob_approved = to64x61(1000000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(2)

    order_id_1 = str_to_felt("jciow4k234")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(1078)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("sdfk32lvfl")
    ticker2 = str_to_felt("mbds324gsbsbs")
    price2 = to64x61(1078)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()


    await assert_revert( dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(1000000)
    bob_approved = to64x61(1000000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(2)

    order_id_1 = str_to_felt("w3godgvx323af")
    ticker1 = str_to_felt("qwekvio234kjdfs")
    price1 = to64x61(1078)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("fj45g324dfsg")
    ticker2 = str_to_felt("qwekvio234kjdfs")
    price2 = to64x61(1078)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()

    await assert_revert( dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res 
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res 
    assert holdingBalance.result.amount == holdingBalance_before.result.amount 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee 
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee 
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee 

@pytest.mark.asyncio
async def test_revert_if_asset_mismatch(adminAuth_factory):
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(1000000)
    bob_approved = to64x61(1000000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(2)

    order_id_1 = str_to_felt("wqelvqwe23")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(1078)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("34ksdfmvcv")
    ticker2 = str_to_felt("65ksgn23nv")
    price2 = to64x61(1078)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size1).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()


    await assert_revert( dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(1000000)
    bob_approved = to64x61(1000000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size = to64x61(2)

    order_id_1 = str_to_felt("y7hi83kjhr")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(10789)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("329dsfjvcx9u")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(10789)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()
    

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

    orderState1 = await alice.get_order_data(order_ID = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        ticker1, 
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size, 
        1
    ]

    orderState2 = await bob.get_order_data(order_ID = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert list(res2) == [
        ticker2, 
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        size, 
        1
    ]

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + total_amount1 + total_amount2 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee + fees1.result.res
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee + fees2.result.res
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee + fees1.result.res + fees2.result.res 

    ##### Closing Of Orders ########
    size2 = to64x61(2)

    order_id_3 = str_to_felt("jd7yhu21")
    ticker3 = str_to_felt("32f0406jz7qj8")
    price3 = to64x61(11000)
    orderType3 = 0
    position3 = to64x61(4)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1

    order_id_4 = str_to_felt("xzkw9212")
    ticker4 = str_to_felt("32f0406jz7qj8")
    price4 = to64x61(11000)
    orderType4 = 0
    position4 = to64x61(3)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2

    execution_price2 = to64x61(11000)

    hash_computed3 = hash_order(order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3)
    hash_computed4 = hash_order(order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4)
  
    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    assert_revert( lambda: dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message3[0], signed_message3[1], order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ]))

    orderState3 = await alice.get_order_data(order_ID = order_id_1).call()
    res3 = list(orderState3.result.res)
    assert res3 == res1


    orderState4 = await bob.get_order_data(order_ID = order_id_2).call()
    res4 = list(orderState4.result.res)
    assert res4 == res2

    alice_curr_balance_after = await alice.get_balance().call()
    bob_curr_balance_after = await bob.get_balance().call()
    holdingBalance_after = await holding.balance(ticker = ticker1).call()
    feeBalance_after = await feeBalance.get_total_fee().call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address).call()
    
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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(5500)
    bob_approved = to64x61(5500)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size = to64x61(1)

    order_id_1 = str_to_felt("343uofdsjnv")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(5000)
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("wer4iljerw")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(5000)
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, size).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()


    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])

    orderState1 = await alice.get_order_data(order_ID = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        ticker1,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size, 
        2
    ]

    orderState2 = await bob.get_order_data(order_ID = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        ticker2, 
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        size, 
        2
    ]

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + total_amount1 + total_amount2 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee + fees1.result.res
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee + fees2.result.res
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee + fees1.result.res + fees2.result.res 
    
    #### Closing Of Orders ########
    size2 = to64x61(1)

    order_id_3 = str_to_felt("rlbrj4hd")
    ticker3 = str_to_felt("32f0406jz7qj8")
    price3 = to64x61(6000)
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1

    order_id_4 = str_to_felt("tew2334")
    ticker4 = str_to_felt("32f0406jz7qj8")
    price4 = to64x61(6000)
    orderType4 = 0
    position4 = to64x61(1)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3)
    hash_computed4 = hash_order(order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4)
    
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
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message4[0], signed_message4[1], order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ])



    orderState3 = await alice.get_order_data(order_ID = order_id_1).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        ticker1, 
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        0, 
        4
    ]

    orderState4 = await bob.get_order_data(order_ID = order_id_2).call()
    res4 = list(orderState4.result.res)

    alice_curr_balance_after = await alice.get_balance().call()
    bob_curr_balance_after = await bob.get_balance().call()


    assert res4 == [
        ticker2, 
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        0, 
        4
    ]

    alice_curr_balance_after = await alice.get_balance().call()
    bob_curr_balance_after = await bob.get_balance().call()
    holdingBalance_after = await holding.balance(ticker = ticker1).call()
    feeBalance_after = await feeBalance.get_total_fee().call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address).call()
    
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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = to64x61(5500)
    bob_approved = to64x61(5500)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()

    ####### Opening of Orders #######
    size = to64x61(0.3)

    order_id_1 = str_to_felt("gfdg324fdsjnv")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(5000)
    orderType1 = 0
    position1 = to64x61(0.5)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("ert8vckj34rw")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(5000)
    orderType2 = 0
    position2 = to64x61(0.3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    amount1 = await fixed_math.mul_fp(execution_price1, size).call()
    fees1 = await fixed_math.mul_fp(amount1.result.res, short_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.mul_fp(execution_price1, position2).call()
    fees2 = await fixed_math.mul_fp(amount2.result.res, long_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2

    orderState1 = await alice.get_order_data(order_ID = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        ticker1,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size, 
        1
    ]

    orderState2 = await bob.get_order_data(order_ID = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        ticker2, 
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        position2, 
        2
    ]

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()
    

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert bob_curr_balance.result.res == bob_curr_balance_before.result.res - total_amount2
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + total_amount1 + total_amount2 
    assert alice_total_fees.result.fee == alice_total_fees_before.result.fee + fees1.result.res
    assert bob_total_fees.result.fee == bob_total_fees_before.result.fee + fees2.result.res
    assert feeBalance_curr.result.fee  == feeBalance_before.result.fee + fees1.result.res + fees2.result.res 
    
    #### Closing Of Orders ########
    size2 = to64x61(0.3)

    order_id_3 = str_to_felt("314df3ghd")
    ticker3 = str_to_felt("32f0406jz7qj8")
    price3 = to64x61(6000)
    orderType3 = 0
    position3 = to64x61(0.3)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1

    order_id_4 = str_to_felt("fdswrf4tdsag")
    ticker4 = str_to_felt("32f0406jz7qj8")
    price4 = to64x61(6000)
    orderType4 = 0
    position4 = to64x61(0.3)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3)
    hash_computed4 = hash_order(order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4)
    
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
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message4[0], signed_message4[1], order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ])



    orderState3 = await alice.get_order_data(order_ID = order_id_1).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        ticker1, 
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        0, 
        4
    ]

    orderState4 = await bob.get_order_data(order_ID = order_id_2).call()
    res4 = list(orderState4.result.res)

    assert res4 == [
        ticker2, 
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        0, 
        4
    ]

    alice_curr_balance_after = await alice.get_balance().call()
    bob_curr_balance_after = await bob.get_balance().call()
    holdingBalance_after = await holding.balance(ticker = ticker1).call()
    feeBalance_after = await feeBalance.get_total_fee().call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address).call()
    
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

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 
    await admin2_signer.send_transaction(admin2, charlie.contract_address, 'set_balance', [charlie_balance]) 

    alice_approved = to64x61(50000)
    bob_approved = to64x61(50000)
    charlie_approved = to64x61(50000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])
    await charlie_signer.send_transaction(charlie, charlie.contract_address, 'approve', [trading.contract_address, charlie_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()
    charlie_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved
    assert charlie_curr_approved.result.res == charlie_approved

    alice_curr_balance_before = await alice.get_balance().call()
    bob_curr_balance_before = await bob.get_balance().call()
    charlie_curr_balance_before = await charlie.get_balance().call()

    ####### Opening of Orders #######
    size1 = to64x61(4)

    order_id_1 = str_to_felt("asdlfkjaf")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(9325.2432042)
    orderType1 = 0
    position1 = to64x61(5)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("fdser34iu45g")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(9325.03424)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    order_id_3 = str_to_felt("3dfw32423rv")
    ticker3 = str_to_felt("32f0406jz7qj8")
    price3 = to64x61(9324.43)
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 0
    parentOrder3 = 0

    execution_price1 = to64x61(9325)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)
    hash_computed3 = hash_order(order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3)

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
    
    holdingBalance_before = await holding.balance(ticker = ticker1).call()
    feeBalance_before = await feeBalance.get_total_fee().call()
    alice_total_fees_before = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address = bob.contract_address).call()
    charlie_total_fees_before = await feeBalance.get_user_fee(address = charlie.contract_address).call()


    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        3,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2,
        charlie.contract_address, signed_message3[0], signed_message3[1], order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3
    ])

    orderState1 = await alice.get_order_data(order_ID = order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        ticker1,
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        size1, 
        1
    ]

    orderState2 = await bob.get_order_data(order_ID = order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        ticker2, 
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        position2, 
        2
    ]

    orderState3 = await charlie.get_order_data(order_ID = order_id_3).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        ticker3, 
        price3, 
        execution_price1, 
        position3,
        orderType3,
        direction3, 
        position3, 
        2
    ]

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()
    charlie_curr_balance = await charlie.get_balance().call()
    holdingBalance = await holding.balance(ticker = ticker1).call()
    feeBalance_curr = await feeBalance.get_total_fee().call()
    alice_total_fees = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees = await feeBalance.get_user_fee(address = bob.contract_address).call()
    charlie_total_fees = await feeBalance.get_user_fee(address = charlie.contract_address).call()

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

    order_id_4 = str_to_felt("er8u324hj4hd")
    ticker4 = str_to_felt("32f0406jz7qj8")
    price4 = to64x61(12000.2432042)
    orderType4 = 0
    position4 = to64x61(4)
    direction4 = 1
    closeOrder4 = 1
    parentOrder4 = order_id_1

    order_id_5 = str_to_felt("5324k34")
    ticker5 = str_to_felt("32f0406jz7qj8")
    price5 = to64x61(12032.9803)
    orderType5 = 0
    position5 = to64x61(3)
    direction5 = 0
    closeOrder5 = 1
    parentOrder5 = order_id_2

    order_id_6 = str_to_felt("3df324gds34")
    ticker6 = str_to_felt("32f0406jz7qj8")
    price6 = to64x61(12010.2610396)
    orderType6 = 0
    position6 = to64x61(1)
    direction6 = 0
    closeOrder6 = 1
    parentOrder6 = order_id_3

    execution_price2 = to64x61(12025.432)

    hash_computed4 = hash_order(order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4)
    hash_computed5 = hash_order(order_id_5, ticker5, price5, orderType5, position5, direction5, closeOrder5)
    hash_computed6 = hash_order(order_id_6, ticker6, price6, orderType6, position6, direction6, closeOrder6)

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
        3,
        alice.contract_address, signed_message4[0], signed_message4[1], order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4,
        bob.contract_address, signed_message5[0], signed_message5[1], order_id_5, ticker5, price5, orderType5, position5, direction5, closeOrder5, parentOrder5,
        charlie.contract_address, signed_message6[0], signed_message6[1], order_id_6, ticker6, price6, orderType6, position6, direction6, closeOrder6, parentOrder6
    ])

    orderState4 = await alice.get_order_data(order_ID = order_id_1).call()
    res4 = list(orderState4.result.res)
    assert res4 == [
        ticker1, 
        price1, 
        execution_price1, 
        position1,
        orderType1,
        direction1, 
        0, 
        4
    ]

    orderState5 = await bob.get_order_data(order_ID = order_id_2).call()
    res5 = list(orderState5.result.res)
    assert res5 == [
        ticker2, 
        price2, 
        execution_price1, 
        position2,
        orderType2,
        direction2, 
        0, 
        4
    ]

    orderState6 = await charlie.get_order_data(order_ID = order_id_3).call()
    res6 = list(orderState6.result.res)
    assert res6 == [
        ticker3, 
        price3, 
        execution_price1, 
        position3,
        orderType3,
        direction3, 
        0, 
        4
    ]

    alice_curr_balance_after = await alice.get_balance().call()
    bob_curr_balance_after = await bob.get_balance().call()
    charlie_curr_balance_after = await charlie.get_balance().call()
    holdingBalance_after = await holding.balance(ticker = ticker1).call()
    feeBalance_after = await feeBalance.get_total_fee().call()
    alice_total_fees_after = await feeBalance.get_user_fee(address = alice.contract_address).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address = bob.contract_address).call()
    charlie_total_fees_after= await feeBalance.get_user_fee(address = charlie.contract_address).call()

    assert holdingBalance_after.result.amount == holdingBalance.result.amount - total_amount1 - total_amount2 - total_amount3
    assert alice_curr_balance_after.result.res ==  alice_curr_balance.result.res + total_amount1
    assert bob_curr_balance_after.result.res == bob_curr_balance.result.res + total_amount2
    assert charlie_curr_balance_after.result.res == charlie_curr_balance.result.res + total_amount3
    assert alice_total_fees_after.result.fee == alice_total_fees.result.fee  + fees1.result.res
    assert bob_total_fees_after.result.fee == bob_total_fees.result.fee  + fees2.result.res
    assert charlie_total_fees_after.result.fee == charlie_total_fees.result.fee  + fees3.result.res
    assert feeBalance_after.result.fee  == feeBalance_curr.result.fee  + fees1.result.res + fees2.result.res + fees3.result.res
    
    