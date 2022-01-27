from ast import parse
from turtle import position
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, sign, parse_number

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654323)
charlie_signer = Signer(123456789987654323)
dave_signer = Signer(123456789987654323)

long_trading_fees = parse_number(1.2)
short_trading_fees = parse_number(0.8)

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
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [parse_number(1000000)]) 
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [parse_number(1000000)]) 
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave

@pytest.mark.asyncio
async def test_set_balance_for_testing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

    alice_balance = parse_number(100000)
    bob_balance = parse_number(100000)
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_curr_balance = await alice.get_balance().call()
    bob_curr_balance = await bob.get_balance().call()

 
    assert alice_curr_balance.result.res == alice_balance
    assert bob_curr_balance.result.res == bob_balance

async def test_set_allowance_for_testing(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

    alice_balance = parse_number(100000)
    bob_balance = parse_number(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [alice_balance]) 
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [bob_balance]) 

    alice_approved = parse_number(10000)
    bob_approved = parse_number(10000)

    await alice_signer.send_transaction(alice, alice.contract_address, 'approve', [trading.contract_address, alice_approved]) 
    await bob_signer.send_transaction(bob, bob.contract_address, 'approve', [trading.contract_address, bob_approved])

    alice_curr_approved = await alice.get_allowance(trading.contract_address).call()
    bob_curr_approved = await alice.get_allowance(trading.contract_address).call()

    assert alice_curr_approved.result.res == alice_approved
    assert bob_curr_approved.result.res == bob_approved

   
   






@pytest.mark.asyncio
async def test_execution_of_data(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave = adminAuth_factory

    size = 2

    order_id_1 = str_to_felt("sdaf")
    ticker1 = str_to_felt("32f0406jz7qj8")
    price1 = parse_number(10000)
    orderType1 = 0
    position1 = 4
    direction1 = 0
    closeOrder1 = 0

    order_id_2 = str_to_felt("f45g")
    ticker2 = str_to_felt("32f0406jz7qj8")
    price2 = parse_number(10000)
    orderType2 = 0
    position2 = 3
    direction2 = 1
    closeOrder2 = 0

    execution_price = 10000

    hash_computed1 = hash_order(order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1)
    print(hash_computed1)

    hash_computed2 = hash_order(order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2)
    print(hash_computed2)
    
    signed_message1 = alice_signer.sign(hash_computed1)
    print(signed_message1)

    signed_message2 = bob_signer.sign(hash_computed2)
    print(signed_message2)

    execution_info1 = await asset.getAsset(str_to_felt("32f0406jz7qj8")).call()
    print(execution_info1.result.currAsset)

    res = await dave_signer.send_transaction( dave, trading.contract_address, "check_execution", [
        size,
        10000,
        2,
        alice.contract_address, signed_message1[0], signed_message1[1], order_id_1, ticker1, price1, orderType1, position1, direction1, closeOrder1, 
        bob.contract_address, signed_message2[0], signed_message2[1], order_id_2, ticker2, price2, orderType2, position2, direction2, closeOrder2, 
    ])
    print(res.result)

    res = await fees.get_fees().call()
    print(res.result)

    order1 = await trading.get_asset(id=2).call()
    print(order1.result)

    order2 = await trading.get_asset(id=1).call()
    print(order2.result)

    lockedFunds1 = await alice.get_locked_balance().call()
    print(lockedFunds1.result)

    lockedFunds2 = await bob.get_locked_balance().call()
    print(lockedFunds2.result)








    # await admin1.send_transaction(
    #     admin1, 
    #     admin1.contract_address, 
    #     "place_order", 
    #     [
    #         order_id_1, 
    #         ticker1, 
    #         price1, 
    #         orderType1,
    #         position1, 
    #         direction1, 
    #         closeOrder1, 
    #         signed_message1[0], 
    #         signed_message1[1], 
    #         12
    #     ]
    # )
    # execution_info1 = await admin1.get_order_data(str_to_felt("sdaf")).call()
    # print(execution_info1.result.res)

    # execution_info2 = await admin2.get_order_data(str_to_felt("f45g")).call()
    # print(execution_info2.result.res)

    # signed_message2 = signer2.sign(hash_computed)
    # assert_revert(lambda: signer1.send_transaction(admin1, trading.contract_address, "execute_order", [ticker, price, position, direction, signer1.public_key, signed_message2[0], signed_message[1]]))