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

    quoteL1Fee = await starknet.deploy(
        "contracts/QuoteL1Fee.cairo",
        constructor_calldata=[0, 1]
    )
    
    return admin1, quoteL1Fee


@pytest.mark.asyncio
async def test_add_to_withdrawal_request(adminAuth_factory):
    admin1, quoteL1Fee = adminAuth_factory

    luser_l1_address_ = 123
    ticker_ = 1434
    amount_ = 0
    timestamp_ = 1657016684
    L1_fee_amount_ = 0
    L1_fee_ticker_ = 1434

    timestamp1_ = 1657016695
    timestamp2_ = 1657016697

    await admin1_signer.send_transaction(admin1, quoteL1Fee.contract_address, 'set_max_length', [3])
    await admin1_signer.send_transaction(admin1, quoteL1Fee.contract_address, 'add_message_recurse', [luser_l1_address_, ticker_, amount_, timestamp_, L1_fee_amount_, L1_fee_ticker_, 0])
    await admin1_signer.send_transaction(admin1, quoteL1Fee.contract_address, 'add_message_recurse', [luser_l1_address_, ticker_, amount_, timestamp_, L1_fee_amount_, L1_fee_ticker_, 0])
    await admin1_signer.send_transaction(admin1, quoteL1Fee.contract_address, 'add_message_recurse', [luser_l1_address_, ticker_, amount_, timestamp1_, L1_fee_amount_, L1_fee_ticker_, 0])
    await admin1_signer.send_transaction(admin1, quoteL1Fee.contract_address, 'add_message_recurse', [luser_l1_address_, ticker_, amount_, timestamp2_, L1_fee_amount_, L1_fee_ticker_, 0])
    # await bob_signer.send_transaction(bob, withdrawal_request.contract_address, 'add_withdrawal_request', [l1_wallet_address_2, collateral_id_2, amount_2, 0])

    fetched_message = await quoteL1Fee.get_message(0).call()
    fetched_message1 = await quoteL1Fee.get_message(1).call()
    print(fetched_message.result)
    print(fetched_message1.result)