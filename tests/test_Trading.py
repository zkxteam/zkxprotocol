from turtle import position
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, sign

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)

long_trading_fees = 12
short_trading_fees = 8

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0]
    )

    user1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer3.public_key, 0]
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

    trading = await starknet.deploy(
        "contracts/Trading.cairo",
        constructor_calldata=[]
    )

    return adminAuth, fees, admin1, admin2, user1, trading

@pytest.mark.asyncio
async def test_signing_of_data(adminAuth_factory):
    adminAuth, fees, admin1, admin2, user1, trading = adminAuth_factory

    order_id_1 = str_to_felt("sdaf")
    ticker1 = str_to_felt('BTC')
    price1 = 100000
    position1 = 10
    direction1 = 1
    closeOrder1 = 0

    order_id_2 = str_to_felt("f45g")
    ticker2 = str_to_felt('BTC')
    price2 = 100000
    position2 = 1
    direction2 = 0
    closeOrder2 = 0

    hash_computed1 = hash_order(order_id_1, ticker1, price1, position1, direction1, closeOrder1)
    print(hash_computed1)

    hash_computed2 = hash_order(order_id_2, ticker2, price2, position2, direction2, closeOrder2)
    print(hash_computed2)
    
    signed_message1 = signer1.sign(hash_computed1)
    print(signed_message1)

    signed_message2 = signer2.sign(hash_computed2)
    print(signed_message2)
    
    await signer1.send_transaction(admin1, trading.contract_address, "execute_order", [
        order_id_1, ticker1, price1, position1, direction1, closeOrder1, 
        admin1.contract_address, 
        signed_message1[0], signed_message1[1], 

        order_id_2, ticker2, price2, position2, direction2, closeOrder2, 
        admin2.contract_address, 
        signed_message2[0], signed_message2[1],
        
        1
    ])
    # await signer1.send_transaction(admin1, admin1.contract_address, "place_order", [order_id_1, ticker1, price1, position1, direction1, closeOrder1, signed_message1[0], signed_message1[1], 12])
    execution_info1 = await admin1.get_order_data(str_to_felt("sdaf")).call()
    print(execution_info1.result.res)

    execution_info2 = await admin2.get_order_data(str_to_felt("f45g")).call()
    print(execution_info2.result.res)

    # signed_message2 = signer2.sign(hash_computed)
    # assert_revert(lambda: signer1.send_transaction(admin1, trading.contract_address, "execute_order", [ticker, price, position, direction, signer1.public_key, signed_message2[0], signed_message[1]]))