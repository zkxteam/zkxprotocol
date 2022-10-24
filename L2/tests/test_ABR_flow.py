from copyreg import constructor
import pytest
import ABR_data
import time
import asyncio
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, build_asset_properties, str_to_felt, hash_order, assert_event_emitted, assert_events_emitted, to64x61, convertTo64x61, assert_revert
from helpers import StarknetService, ContractType, AccountFactory
from starkware.starknet.business_logic.execution.objects import OrderedEvent
from starkware.starknet.public.abi import get_selector_from_name

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)


maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_ID = str_to_felt("32f0406jz7qj8")
USDC_ID = str_to_felt("fghj3am52qpzsib")
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")

L1_dummy_address = 0x01234567899876543210


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def abr_factory(starknet_service: StarknetService):

    admin1 = await starknet_service.deploy(
        ContractType.Account, 
        [admin1_signer.public_key]
    )

    admin2 = await starknet_service.deploy(
        ContractType.Account, 
        [admin2_signer.public_key]
    )

    adminAuth = await starknet_service.deploy(
        ContractType.AdminAuth, 
        [admin1.contract_address, 0x0]
    )
    registry = await starknet_service.deploy(
        ContractType.AuthorizedRegistry, 
        [adminAuth.contract_address]
    )

    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )

    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)

    timestamp = int(time.time())

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    fees = await starknet_service.deploy(
        ContractType.TradingFees, 
        [registry.contract_address, 1]
    )
    asset = await starknet_service.deploy(
        ContractType.Asset, 
        [registry.contract_address, 1]
    )
    fixed_math = await starknet_service.deploy(
        ContractType.Math_64x61, 
        []
    )
    holding = await starknet_service.deploy(
        ContractType.Holding, 
        [registry.contract_address, 1]
    )
    feeBalance = await starknet_service.deploy(
        ContractType.FeeBalance, 
        [registry.contract_address, 1]
    )
    market = await starknet_service.deploy(
        ContractType.Markets, 
        [registry.contract_address, 1]
    )
    liquidityFund = await starknet_service.deploy(
        ContractType.LiquidityFund, 
        [registry.contract_address, 1]
    )
    insurance = await starknet_service.deploy(
        ContractType.InsuranceFund, 
        [registry.contract_address, 1]
    )
    emergency = await starknet_service.deploy(
        ContractType.EmergencyFund, 
        [registry.contract_address, 1]
    )
    trading = await starknet_service.deploy(
        ContractType.Trading, 
        [registry.contract_address, 1]
    )
    feeDiscount = await starknet_service.deploy(
        ContractType.FeeDiscount, 
        [registry.contract_address, 1]
    )
    accountRegistry = await starknet_service.deploy(
        ContractType.AccountRegistry, 
        [registry.contract_address, 1]
    )
    abr = await starknet_service.deploy(
        ContractType.ABR, 
        [registry.contract_address, 1]
    )
    abr_fund = await starknet_service.deploy(
        ContractType.ABRFund, 
        [registry.contract_address, 1]
    )
    abr_payment = await starknet_service.deploy(
        ContractType.ABRPayment, 
        [registry.contract_address, 1]
    )
    marketPrices = await starknet_service.deploy(
        ContractType.MarketPrices, 
        [registry.contract_address, 1]
    )
    liquidate = await starknet_service.deploy(
        ContractType.Liquidate, 
        [registry.contract_address, 1]
    )
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
   

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
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [8, 1, emergency.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [9, 1, liquidityFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [10, 1, insurance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, accountRegistry.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [17, 1, abr.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [18, 1, abr_fund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [19, 1, abr_payment.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [11, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [21, 1, marketPrices.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [24, 1, hightide.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [25, 1, trading_stats.contract_address])

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

    # Add BTC asset
    BTC_settings = build_asset_properties(
        id = BTC_ID,
        asset_version = 0,
        ticker = str_to_felt("BTC"),
        short_name = str_to_felt("Bitcoin"),
        is_tradable = 1,
        is_collateral = 0,
        token_decimal = 8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', BTC_settings)

    # Add USDC asset
    USDC_settings = build_asset_properties(
        id = USDC_ID,
        asset_version = 0,
        ticker = str_to_felt("USDC"),
        short_name = str_to_felt("USDC"),
        is_tradable = 0,
        is_collateral = 1,
        token_decimal = 6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', USDC_settings)

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [
        BTC_USD_ID, # market id
        BTC_ID, # asset id
        USDC_ID, # collateral id
        to64x61(10), # leverage
        1, # is_tradable
        0, # is_archived
        10, # ttl
        1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000
    ])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])

    # Fund the Liquidity fund contract
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [USDC_ID, to64x61(1000000)])

    # Fund ABR fund contract
    await admin1_signer.send_transaction(admin1, abr_fund.contract_address, 'fund', [BTC_USD_ID, to64x61(1000000)])

    # Set the balance of admin1 and admin2
    #await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])

    btc_perp_spot_64x61 = convertTo64x61(ABR_data.btc_perp_spot)
    btc_perp_64x61 = convertTo64x61(ABR_data.btc_perp)

    # Add accounts to Account Registry
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [alice.contract_address])
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [bob.contract_address])

    return (starknet_service.starknet, admin1, trading, fixed_math, alice, 
        bob, abr, abr_fund, abr_payment, btc_perp_spot_64x61, btc_perp_64x61, timestamp, admin2)

@pytest.mark.asyncio
async def test_fund_called_by_non_authorized_address(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2 = abr_factory

    amount = to64x61(1000000)
    await assert_revert(
        admin2_signer.send_transaction(admin2, abr_fund.contract_address, "fund", [BTC_USD_ID, amount])
    )

@pytest.mark.asyncio
async def test_fund_called_by_authorized_address(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2 = abr_factory

    amount = to64x61(1000000)
    abr_fund_balance_before = await abr_fund.balance(BTC_USD_ID).call()
    fund_tx = await admin1_signer.send_transaction(admin1, abr_fund.contract_address, "fund", [BTC_USD_ID, amount])

    assert_event_emitted(
        fund_tx,
        from_address=abr_fund.contract_address,
        name="fund_ABR_called",
        data=[
            BTC_USD_ID,
            amount
        ]
    )

    abr_fund_balance = await abr_fund.balance(BTC_USD_ID).call()
    assert abr_fund_balance.result.amount == abr_fund_balance_before.result.amount + amount

@pytest.mark.asyncio
async def test_defund_called_by_non_authorized_address(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2 = abr_factory

    amount = to64x61(500000)
    abr_fund_balance_before = await abr_fund.balance(BTC_USD_ID).call()
    await assert_revert(
        admin2_signer.send_transaction(admin2, abr_fund.contract_address, "defund", [BTC_USD_ID, amount])
    )

    abr_fund_balance = await abr_fund.balance(BTC_USD_ID).call()
    assert abr_fund_balance.result.amount == abr_fund_balance_before.result.amount 

@pytest.mark.asyncio
async def test_defund_called_by_authorized_address(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2 = abr_factory

    amount = to64x61(500000)
    abr_fund_balance_before = await abr_fund.balance(BTC_USD_ID).call()
    defund_tx = await admin1_signer.send_transaction(admin1, abr_fund.contract_address, "defund", [BTC_USD_ID, amount])

    assert_event_emitted(
        defund_tx,
        from_address=abr_fund.contract_address,
        name="defund_ABR_called",
        data=[
            BTC_USD_ID,
            amount
        ]
    )

    abr_fund_balance = await abr_fund.balance(BTC_USD_ID).call()
    assert abr_fund_balance.result.amount == abr_fund_balance_before.result.amount - amount


@pytest.mark.asyncio
async def test_abr_payments(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2 = abr_factory

    alice_balance = to64x61(50000)
    bob_balance = to64x61(50000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin1_signer.send_transaction(admin1, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("343uofdsjnv")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(40900)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("wer4iljerw")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(40900)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(40900)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await admin1_signer.send_transaction(admin1, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ])

    alice_balance = await alice.get_balance(USDC_ID).call()
    bob_balance = await bob.get_balance(USDC_ID).call()
    abr_fund_balance = await abr_fund.balance(BTC_USD_ID).call()

    arguments = [BTC_USD_ID, 480] + btc_spot + [480]+btc_perp

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)

    abr_result = await abr.get_abr_value(BTC_USD_ID).call()

    abr_to_pay = await fixed_math.Math64x61_mul(abr_result.result.price, abr_result.result.abr).call()
    

    abr_tx = await admin1_signer.send_transaction(admin1, abr_payment.contract_address, "pay_abr", [2, alice.contract_address, bob.contract_address])

    
    assert_events_emitted_from_all_calls(
        abr_tx,
        [
            [0, abr_fund.contract_address, 'withdraw_ABR_called', [alice.contract_address, marketID_1, abr_to_pay.result.res, initial_timestamp]],
            [1, alice.contract_address, 'transferred_abr', [marketID_1, abr_to_pay.result.res, initial_timestamp]],
            [2, abr_payment.contract_address, 'abr_payment_called_user_position', [marketID_1, alice.contract_address, initial_timestamp]],
            [3, bob.contract_address, 'transferred_from_abr', [marketID_1, abr_to_pay.result.res, initial_timestamp]],
            [4, abr_fund.contract_address, 'deposit_ABR_called', [bob.contract_address, marketID_1, abr_to_pay.result.res, initial_timestamp]],
            [5, abr_payment.contract_address, 'abr_payment_called_user_position', [marketID_1, bob.contract_address, initial_timestamp]]
        ]
    )
    

    alice_balance_after = await alice.get_balance(USDC_ID).call()
    bob_balance_after = await bob.get_balance(USDC_ID).call()
    abr_fund_balance_after = await abr_fund.balance(BTC_USD_ID).call()

    assert alice_balance.result.res == alice_balance_after.result.res - abr_to_pay.result.res
    assert bob_balance.result.res == bob_balance_after.result.res + abr_to_pay.result.res
    assert abr_fund_balance.result.amount == abr_fund_balance_after.result.amount


@pytest.mark.asyncio
async def test_will_not_charge_abr_twice_under_8_hours(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2 = abr_factory

    alice_balance_before = await alice.get_balance(USDC_ID).call()
    bob_balance_before = await bob.get_balance(USDC_ID).call()

    await admin1_signer.send_transaction(admin1, abr_payment.contract_address, "pay_abr", [2, alice.contract_address, bob.contract_address])

    alice_balance_after = await alice.get_balance(USDC_ID).call()
    bob_balance_after = await bob.get_balance(USDC_ID).call()

    assert alice_balance_before.result.res == alice_balance_after.result.res
    assert bob_balance_before.result.res == bob_balance_after.result.res


@pytest.mark.asyncio
async def test_will_charge_abr_after_8_hours(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2 = abr_factory

    timestamp = int(time.time()) + 28810

    starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet.state.state.block_info.gas_price,
        sequencer_address=starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    alice_balance = await alice.get_balance(USDC_ID).call()
    bob_balance = await bob.get_balance(USDC_ID).call()
    abr_fund_balance = await abr_fund.balance(BTC_USD_ID).call()

    arguments = [BTC_USD_ID, 480] + btc_spot + [480]+btc_perp

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    abr_result = await abr.get_abr_value(BTC_USD_ID).call()

    abr_to_pay = await fixed_math.Math64x61_mul(abr_result.result.price, abr_result.result.abr).call()
    abr_tx = await admin1_signer.send_transaction(admin1, abr_payment.contract_address, "pay_abr", [2, alice.contract_address, bob.contract_address])
    
    marketID_1 = BTC_USD_ID

    assert_events_emitted_from_all_calls(
        abr_tx,
        [
            [0, abr_fund.contract_address, 'withdraw_ABR_called', [alice.contract_address, marketID_1, abr_to_pay.result.res, timestamp]],
            [1, alice.contract_address, 'transferred_abr', [marketID_1, abr_to_pay.result.res, timestamp]],
            [2, abr_payment.contract_address, 'abr_payment_called_user_position', [marketID_1, alice.contract_address, timestamp]],
            [3, bob.contract_address, 'transferred_from_abr', [marketID_1, abr_to_pay.result.res, timestamp]],
            [4, abr_fund.contract_address, 'deposit_ABR_called', [bob.contract_address, marketID_1, abr_to_pay.result.res, timestamp]],
            [5, abr_payment.contract_address, 'abr_payment_called_user_position', [marketID_1, bob.contract_address, timestamp]]
        ]
    )
  
    
    alice_balance_after = await alice.get_balance(USDC_ID).call()
    bob_balance_after = await bob.get_balance(USDC_ID).call()
    abr_fund_balance_after = await abr_fund.balance(BTC_USD_ID).call()

    assert alice_balance.result.res == alice_balance_after.result.res - abr_to_pay.result.res
    assert bob_balance.result.res == bob_balance_after.result.res + abr_to_pay.result.res
    assert abr_fund_balance.result.amount == abr_fund_balance_after.result.amount

def assert_events_emitted_from_all_calls(tx_exec_info, events):
    """Assert events are fired with correct data."""
    for event in events:
        order, from_address, name, data = event
        event_obj = OrderedEvent(
            order=order,
            keys=[get_selector_from_name(name)],
            data=data,
        )

        base = tx_exec_info.call_info.internal_calls[0]
        if event_obj in base.events and from_address == base.contract_address:
            return

        try:
            internal_calls = base.internal_calls
            for base2 in internal_calls:
                if event_obj in base2.events and from_address == base2.contract_address:
                    return
        except IndexError:
            pass

        raise BaseException("Event not fired or not fired correctly")