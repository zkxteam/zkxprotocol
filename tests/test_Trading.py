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

    trading = await starknet.deploy(
        "contracts/Trading.cairo",
        constructor_calldata=[
            asset.contract_address,
            fees.contract_address
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

    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    # Admin1 gets the access to update the Authorized Registry Contract
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_registry', [ trading.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), str_to_felt("BTC"), str_to_felt("Bitcoin"), 1])
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [to64x61(1000000)]) 
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [to64x61(1000000)]) 
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave

@pytest.mark.asyncio
async def test_set_balance_for_testing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

 
    assert alice_curr_balance.result.res == alice_balance
    assert bob_curr_balance.result.res == bob_balance

async def test_set_allowance_for_testing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

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
    dminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

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

    ####### Opening of Orders #######
    size = to64x61(2)

    order_id_1 = str_to_felt("wer323af")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(10789)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("f45g324dfsg")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(10789)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    assert_revert( lambda: dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ]))


   
@pytest.mark.asyncio
async def test_revert_wrong_signature(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

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

    ####### Opening of Orders #######
    size = to64x61(2)

    order_id_1 = str_to_felt("wer323af")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = to64x61(10789)
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0

    order_id_2 = str_to_felt("f45g324dfsg")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = to64x61(10789)
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0

    execution_price = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])
    print(res.result)

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

    print("1. Alice Balance after opening order: ", alice_curr_balance.result.res)
    print("2. Bob Balance after opening order: ", bob_curr_balance.result.res)

    orderState1 = await alice.get_order_data(order_ID = order_id_1).call()
    print("test revert open order 1: ", orderState1.result.res )
    res1 = list(orderState1.result.res)

    assert res1 == [
        ticker1, 
        price1, 
        execution_price, 
        position1,
        orderType1,
        direction1, 
        size, 
        1
    ]

    orderState2 = await bob.get_order_data(order_ID = order_id_2).call()
    print("test revert open order 2: ", orderState2.result.res)
    res2 =list(orderState2.result.res)
    print(res2)

    assert list(res2) == [
        ticker2, 
        price2, 
        execution_price, 
        position2,
        orderType2,
        direction2, 
        size, 
        1
    ]
    ##### Closing Of Orders ########
    size2 = to64x61(2)

    order_id_3 = str_to_felt("32gfds4hd")
    ticker3 = str_to_felt("32f0406jz7qj8")
    price3 = to64x61(11000)
    orderType3 = 0
    position3 = to64x61(4)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1

    order_id_4 = str_to_felt("3d5435gf4")
    ticker4 = str_to_felt("32f0406jz7qj8")
    price4 = to64x61(11000)
    orderType4 = 0
    position4 = to64x61(3)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2

    execution_price2 = to64x61(11000)

    hash_computed3 = hash_order(order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3)
    print(hash_computed3)

    hash_computed4 = hash_order(order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4)
    print(hash_computed4)
    
    signed_message3 = alice_signer.sign(hash_computed3)
    print(signed_message3)

    signed_message4 = bob_signer.sign(hash_computed4)
    print(signed_message4)


    assert_revert( lambda: dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message3[0], signed_message3[1], order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ]))
    # print(res.result)

    orderState3 = await alice.get_order_data(order_ID = order_id_1).call()
    print("test revert close order 1: ", orderState3.result.res )
    res3 =list(orderState3.result.res)
    assert res3 == res1


    orderState4 = await bob.get_order_data(order_ID = order_id_2).call()
    print("test revert close order 2: ",orderState4.result.res)
    res4 = list(orderState4.result.res)
    assert res4 == res2

    alice_curr_balance_after = await alice.get_balance().call()
    bob_curr_balance_after = await bob.get_balance().call()

    print("1. Alice Balance after reverting close order: ", alice_curr_balance_after.result.res)
    print("2. Bob Balance after reverting close order: ", bob_curr_balance_after.result.res)

    assert alice_curr_balance.result.res == alice_curr_balance_after.result.res
    assert bob_curr_balance.result.res == bob_curr_balance_after.result.res


@pytest.mark.asyncio
async def test_opening_and_closing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

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

    print("1. Alice Balance before opening order: ", alice_curr_balance_before.result.res)
    print("2. Bob Balance before opening order: ", bob_curr_balance_before.result.res)

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

    execution_price = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size,
        execution_price,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2
    ])
    print(res.result)

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

    print("1. Alice Balance after opening order: ", alice_curr_balance.result.res)
    print("2. Bob Balance after opening order: ", bob_curr_balance.result.res)


    orderState1 = await alice.get_order_data(order_ID = order_id_1).call()
    print("test open and close, open order 1: ",orderState1.result.res )
    res1 = convertList(list(orderState1.result.res))


    # assert res1 == [
    #     from64x61(price1), 
    #     from64x61(execution_price), 
    #     from64x61(position1),
    #     orderType1,
    #     direction1, 
    #     from64x61(size), 
    #     ticker1, 
    #     1
    # ]

    orderState2 = await bob.get_order_data(order_ID = order_id_2).call()
    print("test open and close, open order 2: ",orderState2.result.res)
    res2 = convertList(list(orderState2.result.res))

    # assert res2 == [
    #     from64x61(price2), 
    #     from64x61(execution_price), 
    #     from64x61(position2),
    #     orderType2,
    #     direction2, 
    #     from64x61(size), 
    #     ticker2, 
    #     1
    # ]

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

    res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[1], order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3,
        bob.contract_address, signed_message4[0], signed_message4[1], order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4
    ])
    print(res.result)

    orderState3 = await alice.get_order_data(order_ID = order_id_1).call()
    print("test open and close, close order 1: ", orderState3.result.res )
    res3 = orderState3.result.res

    orderState4 = await bob.get_order_data(order_ID = order_id_2).call()
    print("test open and close, close order 2: ",orderState4.result.res)
    res4 = orderState4.result.res

    alice_curr_balance_after = await alice.get_balance().call()
    bob_curr_balance_after = await bob.get_balance().call()

    print("1. Alice Balance after opening order: ", alice_curr_balance_after.result.res)
    print("2. Bob Balance after opening order: ", bob_curr_balance_after.result.res)


# @pytest.mark.asyncio
# async def test_partial_orders(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

#     ####### Opening of Orders #######
#     size = to64x61(4)

#     order_id_1 = str_to_felt("asdlfkjaf")
#     ticker1 = str_to_felt("32f0406jz7qj8")
#     price1 = to64x61(10789)
#     orderType1 = 0
#     position1 = to64x61(4)
#     direction1 = 0
#     closeOrder1 = 0
#     parentOrder1 = 0

#     order_id_2 = str_to_felt("fdser34iu45g")
#     ticker2 = str_to_felt("32f0406jz7qj8")
#     price2 = to64x61(10789)
#     orderType2 = 0
#     position2 = to64x61(2)
#     direction2 = 1
#     closeOrder2 = 0
#     parentOrder2 = 0

#     order_id_3 = str_to_felt("3dfw32423rv")
#     ticker3 = str_to_felt("32f0406jz7qj8")
#     price3 = to64x61(10789)
#     orderType3 = 0
#     position3 = to64x61(2)
#     direction3 = 1
#     closeOrder3 = 0
#     parentOrder3 = 0

#     execution_price = to64x61(10000)

#     hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
#     print(hash_computed1)

#     hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)
#     print(hash_computed2)

#     hash_computed3 = hash_order(order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3)
#     print(hash_computed3)
    
#     signed_message1 = alice_signer.sign(hash_computed1)
#     print(signed_message1)

#     signed_message2 = bob_signer.sign(hash_computed2)
#     print(signed_message2)

#     signed_message3 = charlie_signer.sign(hash_computed3)
#     print(signed_message3)

#     res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
#         size,
#         execution_price,
#         3,
#         alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, parentOrder1,
#         bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, parentOrder2,
#         charlie.contract_address, signed_message3[0], signed_message3[1], order_id_3, ticker3, price3, orderType3, position3, direction3, closeOrder3, parentOrder3
#     ])
#     print(res.result)

#     orderState1 = await alice.get_order_data(order_ID = order_id_1).call()
#     print("test partial orders, open order 1: ", orderState1.result.res )

#     orderState2 = await bob.get_order_data(order_ID = order_id_2).call()
#     print("test partial orders, open order 2: ",orderState2.result.res)

#     orderState3 = await charlie.get_order_data(order_ID = order_id_3).call()
#     print("test partial orders, open order 3: ",orderState3.result.res)


#     ##### Closing Of Orders ########
#     size2 = to64x61(1)

#     order_id_4 = str_to_felt("er8u324hj4hd")
#     ticker4 = str_to_felt("32f0406jz7qj8")
#     price4 = to64x61(16017)
#     orderType4 = 0
#     position4 = to64x61(2)
#     direction4 = 1
#     closeOrder4 = 1
#     parentOrder4 = order_id_1

#     order_id_5 = str_to_felt("5324k34")
#     ticker5 = str_to_felt("32f0406jz7qj8")
#     price5 = to64x61(16078)
#     orderType5 = 0
#     position5 = to64x61(1.1)
#     direction5 = 0
#     closeOrder5 = 1
#     parentOrder5 = order_id_2

#     order_id_6 = str_to_felt("3df324gds34")
#     ticker6 = str_to_felt("32f0406jz7qj8")
#     price6 = to64x61(16099)
#     orderType6 = 0
#     position6 = to64x61(1.1)
#     direction6 = 0
#     closeOrder6 = 1
#     parentOrder6 = order_id_3

#     execution_price2 = to64x61(17000)

#     hash_computed4 = hash_order(order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4)
#     print(hash_computed4)

#     hash_computed5 = hash_order(order_id_5, ticker5, price5, orderType5, position5, direction5, closeOrder5)
#     print(hash_computed5)
    
#     hash_computed6 = hash_order(order_id_6, ticker6, price6, orderType6, position6, direction6, closeOrder6)
#     print(hash_computed6)

#     signed_message4 = alice_signer.sign(hash_computed4)
#     print(signed_message4)

#     signed_message5 = bob_signer.sign(hash_computed5)
#     print(signed_message5)

#     signed_message6 = charlie_signer.sign(hash_computed6)
#     print(signed_message6)


#     res = await dave_signer.send_transaction( dave, trading.contract_address, "execute_batch", [
#         size2,
#         execution_price2,
#         3,
#         alice.contract_address, signed_message4[0], signed_message4[1], order_id_4, ticker4, price4, orderType4, position4, direction4, closeOrder4, parentOrder4,
#         bob.contract_address, signed_message5[0], signed_message5[1], order_id_5, ticker5, price5, orderType5, position5, direction5, closeOrder5, parentOrder5,
#         charlie.contract_address, signed_message6[0], signed_message6[1], order_id_6, ticker6, price6, orderType6, position6, direction6, closeOrder6, parentOrder6
#     ])
#     print(res.result)

#     orderState4 = await alice.get_order_data(order_ID = order_id_4).call()
#     print("test partial orders, close order 1: ",orderState4.result.res )

#     orderState5 = await bob.get_order_data(order_ID = order_id_5).call()
#     print("test partial orders, close order 2: ",orderState5.result.res)

#     orderState6 = await bob.get_order_data(order_ID = order_id_6).call()
#     print("test partial orders, close order 3: ",orderState6.result.res)

