import pytest
import ABR_data
import time
import asyncio
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, str_to_felt, hash_order, assert_event_emitted, to64x61, convertTo64x61, assert_revert
from utils_trading import User, order_direction, order_types, order_time_in_force, order_life_cycles, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, check_batch_status
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from helpers import StarknetService, ContractType, AccountFactory
from starkware.starknet.business_logic.execution.objects import OrderedEvent
from starkware.starknet.public.abi import get_selector_from_name

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)


maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")

L1_dummy_address = 0x01234567899876543210


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def abr_factory(starknet_service: StarknetService):

    # Deploy admin accounts
    admin1 = await starknet_service.deploy(ContractType.Account, [admin1_signer.public_key])
    admin2 = await starknet_service.deploy(ContractType.Account, [admin2_signer.public_key])

    # Deploy infrastructure (Part 1)
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])

    python_executor = OrderExecutor()
    # Deploy user accounts
    account_factory = AccountFactory(
        starknet_service, L1_dummy_address, registry.contract_address, 1)

    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    alice_test = User(123456789987654323, alice.contract_address)

    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    bob_test = User(123456789987654324, bob.contract_address)

    timestamp = int(time.time())
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    # Deploy infrastructure (Part 2)
    fees = await starknet_service.deploy(ContractType.TradingFees, [registry.contract_address, 1])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    fixed_math = await starknet_service.deploy(ContractType.Math_64x61, [])
    holding = await starknet_service.deploy(ContractType.Holding, [registry.contract_address, 1])
    feeBalance = await starknet_service.deploy(ContractType.FeeBalance, [registry.contract_address, 1])
    market = await starknet_service.deploy(ContractType.Markets, [registry.contract_address, 1])
    liquidityFund = await starknet_service.deploy(ContractType.LiquidityFund, [registry.contract_address, 1])
    insurance = await starknet_service.deploy(ContractType.InsuranceFund, [registry.contract_address, 1])
    emergency = await starknet_service.deploy(ContractType.EmergencyFund, [registry.contract_address, 1])
    trading = await starknet_service.deploy(ContractType.Trading, [registry.contract_address, 1])
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [registry.contract_address, 1])
    accountRegistry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    abr = await starknet_service.deploy(ContractType.ABR, [registry.contract_address, 1])
    abr_fund = await starknet_service.deploy(ContractType.ABRFund, [registry.contract_address, 1])
    abr_payment = await starknet_service.deploy(ContractType.ABRPayment, [registry.contract_address, 1])
    marketPrices = await starknet_service.deploy(ContractType.MarketPrices, [registry.contract_address, 1])
    liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
    user_stats = await starknet_service.deploy(ContractType.UserStats, [registry.contract_address, 1])

    # Give permissions
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAssets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageMarkets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFeeDetails, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFunds, True])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Asset, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Market, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.FeeDiscount, 1, feeDiscount.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.TradingFees, 1, fees.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Trading, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.FeeBalance, 1, feeBalance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Holding, 1, holding.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.EmergencyFund, 1, emergency.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.LiquidityFund, 1, liquidityFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.InsuranceFund, 1, insurance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountRegistry, 1, accountRegistry.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.ABR, 1, abr.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.ABRFund, 1, abr_fund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.ABRPayment, 1, abr_payment.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountDeployer, 1, admin1.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Liquidate, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.MarketPrices, 1, marketPrices.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Hightide, 1, hightide.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.TradingStats, 1, trading_stats.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.UserStats, 1, user_stats.contract_address])

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
        id=AssetID.BTC,
        short_name=str_to_felt("Bitcoin"),
        asset_version=0,
        is_tradable=1,
        is_collateral=0,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', BTC_settings)

    # Add USDC asset
    USDC_settings = build_asset_properties(
        id=AssetID.USDC,
        short_name=str_to_felt("USDC"),
        asset_version=0,
        is_tradable=0,
        is_collateral=1,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', USDC_settings)

    # Add markets
    BTC_USD_properties = MarketProperties(
        id=BTC_USD_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.USDC,
        leverage=to64x61(10),
        is_tradable=True,
        is_archived=False,
        ttl=10,
        tick_size=1,
        step_size=1,
        minimum_order_size=10,
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(10),
        maintenance_margin_fraction=1,
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', BTC_USD_properties.to_params_list())

    # Fund the Holding contract
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])

    # Fund the Liquidity fund contract
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])

    # Fund ABR fund contract
    await admin1_signer.send_transaction(admin1, abr_fund.contract_address, 'fund', [BTC_USD_ID, to64x61(1000000)])

    btc_perp_spot_64x61 = convertTo64x61(ABR_data.btc_perp_spot)
    btc_perp_64x61 = convertTo64x61(ABR_data.btc_perp)

    # Add accounts to Account Registry
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [alice.contract_address])
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [bob.contract_address])

    # Set the threshold for oracle price in Trading contract
    await admin1_signer.send_transaction(admin1, trading.contract_address, 'set_threshold_percentage', [to64x61(5)])
    return (starknet_service.starknet, admin1, trading, fixed_math, alice,
            bob, abr, abr_fund, abr_payment, btc_perp_spot_64x61, btc_perp_64x61, timestamp, admin2, alice_test, bob_test, python_executor)


@pytest.mark.asyncio
async def test_fund_called_by_non_authorized_address(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2, _, _, _ = abr_factory

    amount = to64x61(1000000)
    await assert_revert(
        admin2_signer.send_transaction(
            admin2, abr_fund.contract_address, "fund", [BTC_USD_ID, amount]),
        reverted_with="FundLib: Unauthorized call to manage funds"
    )


@pytest.mark.asyncio
async def test_fund_called_by_authorized_address(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2, _, _, _ = abr_factory

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
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2,  _, _, _ = abr_factory

    amount = to64x61(500000)
    abr_fund_balance_before = await abr_fund.balance(BTC_USD_ID).call()
    await assert_revert(
        admin2_signer.send_transaction(
            admin2, abr_fund.contract_address, "defund", [BTC_USD_ID, amount]),
        reverted_with="FundLib: Unauthorized call to manage funds"
    )

    abr_fund_balance = await abr_fund.balance(BTC_USD_ID).call()
    assert abr_fund_balance.result.amount == abr_fund_balance_before.result.amount


@pytest.mark.asyncio
async def test_defund_called_by_authorized_address(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2, _, _, _ = abr_factory

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
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2, alice_test, bob_test, python_executor = abr_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 50000
    bob_balance = 50000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 40900

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 40900,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }, {
        "quantity": 1,
        "price": 40900,
    }]

    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading)

    # Get balances before abr call
    alice_balance_before = await alice.get_balance(AssetID.USDC).call()
    bob_balance_before = await bob.get_balance(AssetID.USDC).call()
    abr_fund_balance_before = await abr_fund.balance(BTC_USD_ID).call()
    arguments = [BTC_USD_ID, 480] + btc_spot + [480]+btc_perp

    await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)

    abr_result = await abr.get_abr_value(BTC_USD_ID).call()

    abr_to_pay = await fixed_math.Math64x61_mul(abr_result.result.price, abr_result.result.abr).call()

    abr_tx = await admin1_signer.send_transaction(admin1, abr_payment.contract_address, "pay_abr", [2, alice.contract_address, bob.contract_address])

    assert_events_emitted_from_all_calls(
        abr_tx,
        [
            [0, abr_fund.contract_address, 'withdraw_ABR_called', [
                alice.contract_address, market_id_1, abr_to_pay.result.res, initial_timestamp]],
            [1, alice.contract_address, 'transferred_abr', [
                market_id_1, abr_to_pay.result.res, initial_timestamp]],
            [2, abr_payment.contract_address, 'abr_payment_called_user_position', [
                market_id_1, alice.contract_address, initial_timestamp]],
            [3, bob.contract_address, 'transferred_from_abr', [
                market_id_1, abr_to_pay.result.res, initial_timestamp]],
            [4, abr_fund.contract_address, 'deposit_ABR_called', [
                bob.contract_address, market_id_1, abr_to_pay.result.res, initial_timestamp]],
            [5, abr_payment.contract_address, 'abr_payment_called_user_position', [
                market_id_1, bob.contract_address, initial_timestamp]]
        ]
    )

    alice_balance_after = await alice.get_balance(AssetID.USDC).call()
    bob_balance_after = await bob.get_balance(AssetID.USDC).call()
    abr_fund_balance_after = await abr_fund.balance(BTC_USD_ID).call()

    assert alice_balance_before.result.res == alice_balance_after.result.res - \
        abr_to_pay.result.res
    assert bob_balance_before.result.res == bob_balance_after.result.res + \
        abr_to_pay.result.res
    assert abr_fund_balance_before.result.amount == abr_fund_balance_after.result.amount


@pytest.mark.asyncio
async def test_will_not_charge_abr_twice_under_8_hours(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2, _, _, _ = abr_factory

    alice_balance_before = await alice.get_balance(AssetID.USDC).call()
    bob_balance_before = await bob.get_balance(AssetID.USDC).call()

    await admin1_signer.send_transaction(admin1, abr_payment.contract_address, "pay_abr", [2, alice.contract_address, bob.contract_address])

    alice_balance_after = await alice.get_balance(AssetID.USDC).call()
    bob_balance_after = await bob.get_balance(AssetID.USDC).call()

    assert alice_balance_before.result.res == alice_balance_after.result.res
    assert bob_balance_before.result.res == bob_balance_after.result.res


@pytest.mark.asyncio
async def test_will_charge_abr_after_8_hours(abr_factory):
    starknet, admin1, trading, fixed_math, alice, bob, abr, abr_fund, abr_payment, btc_spot, btc_perp, initial_timestamp, admin2, _, _, _ = abr_factory

    timestamp = int(time.time()) + 28810

    starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet.state.state.block_info.gas_price,
        sequencer_address=starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    alice_balance = await alice.get_balance(AssetID.USDC).call()
    bob_balance = await bob.get_balance(AssetID.USDC).call()
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
            [0, abr_fund.contract_address, 'withdraw_ABR_called', [
                alice.contract_address, marketID_1, abr_to_pay.result.res, timestamp]],
            [1, alice.contract_address, 'transferred_abr', [
                marketID_1, abr_to_pay.result.res, timestamp]],
            [2, abr_payment.contract_address, 'abr_payment_called_user_position', [
                marketID_1, alice.contract_address, timestamp]],
            [3, bob.contract_address, 'transferred_from_abr', [
                marketID_1, abr_to_pay.result.res, timestamp]],
            [4, abr_fund.contract_address, 'deposit_ABR_called', [
                bob.contract_address, marketID_1, abr_to_pay.result.res, timestamp]],
            [5, abr_payment.contract_address, 'abr_payment_called_user_position', [
                marketID_1, bob.contract_address, timestamp]]
        ]
    )

    alice_balance_after = await alice.get_balance(AssetID.USDC).call()
    bob_balance_after = await bob.get_balance(AssetID.USDC).call()
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
