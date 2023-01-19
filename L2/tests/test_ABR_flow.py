import pytest
import ABR_data
import time
import asyncio
from calculate_abr import calculate_abr
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, str_to_felt, assert_event_emitted, to64x61, convertTo64x61, assert_revert, from64x61, PRIME
from utils_trading import User, order_direction, order_types, order_time_in_force, order_life_cycles, OrderExecutor, User, ABR, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, compare_abr_values, check_batch_status, set_abr_value, make_abr_payments
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from helpers import StarknetService, ContractType, AccountFactory
from starkware.starknet.business_logic.execution.objects import OrderedEvent
from starkware.starknet.public.abi import get_selector_from_name

non_admin_signer = Signer(123456789987654327)
admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
dave_signer = Signer(123456789987654326)


maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
ETH_UST_ID = str_to_felt("dsfi32i4ufds8hlkk")
L1_dummy_address = 0x01234567899876543210

timestamp = int(time.time())
timestamp_1 = timestamp + 28800
timestamp_2 = timestamp_1 + 100
timestamp_3 = timestamp_1 + 3600 - 1
timestamp_4 = timestamp_1 + 3600


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def abr_factory(starknet_service: StarknetService):
    # Deploy admin accounts
    admin1 = await starknet_service.deploy(ContractType.Account, [admin1_signer.public_key])
    admin2 = await starknet_service.deploy(ContractType.Account, [admin2_signer.public_key])
    non_admin_1 = await starknet_service.deploy(ContractType.Account, [non_admin_signer.public_key])

    # Deploy infrastructure (Part 1)
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])

    python_executor = OrderExecutor()
    abr_executor = ABR()
    # Deploy user accounts
    account_factory = AccountFactory(
        starknet_service, L1_dummy_address, registry.contract_address, 1)

    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    print("alice", hex(alice.contract_address))
    alice_test = User(123456789987654323, alice.contract_address)

    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    print("bob", hex(bob.contract_address))
    bob_test = User(123456789987654324, bob.contract_address)

    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)
    print("charlie", hex(charlie.contract_address))
    charlie_test = User(123456789987654325, charlie.contract_address)

    dave = await account_factory.deploy_ZKX_account(dave_signer.public_key)
    print("dave", hex(dave.contract_address))
    dave_test = User(123456789987654326, dave.contract_address)

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
    print("Trading contract:", hex(trading.contract_address))
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [registry.contract_address, 1])
    accountRegistry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    abr_calculations = await starknet_service.deploy(ContractType.ABRCalculations, [])
    print("abr_calculations contract:", hex(abr_calculations.contract_address))
    abr_core = await starknet_service.deploy(ContractType.ABRCore, [registry.contract_address, 1])
    print("abr_core contract:", hex(abr_core.contract_address))
    abr_fund = await starknet_service.deploy(ContractType.ABRFund, [registry.contract_address, 1])
    abr_payment = await starknet_service.deploy(ContractType.ABRPayment, [registry.contract_address, 1])
    print("abr_payment contract:", hex(abr_payment.contract_address))
    marketPrices = await starknet_service.deploy(ContractType.MarketPrices, [registry.contract_address, 1])
    liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
    print("liquidate contract:", hex(liquidate.contract_address))
    collateral_prices = await starknet_service.deploy(ContractType.CollateralPrices, [registry.contract_address, 1])
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
    user_stats = await starknet_service.deploy(ContractType.UserStats, [registry.contract_address, 1])

    # Give permissions
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAssets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageMarkets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFeeDetails, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFunds, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageCollateralPrices, True])

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
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.ABRCalculations, 1, abr_calculations.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.ABRCore, 1, abr_core.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.ABRFund, 1, abr_fund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.ABRPayment, 1, abr_payment.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountDeployer, 1, admin1.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Liquidate, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.CollateralPrices, 1, collateral_prices.contract_address])
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

    ETH_properties = build_asset_properties(
        id=AssetID.ETH,
        asset_version=1,
        short_name=str_to_felt("ETH"),
        is_tradable=True,
        is_collateral=False,
        token_decimal=18
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', ETH_properties)

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

    UST_properties = build_asset_properties(
        id=AssetID.UST,
        asset_version=1,
        short_name=str_to_felt("UST"),
        is_tradable=True,
        is_collateral=True,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', UST_properties)

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

    BTC_UST_properties = MarketProperties(
        id=BTC_UST_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.UST,
        leverage=to64x61(10),
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(5),
        currently_allowed_leverage=to64x61(3),
        maintenance_margin_fraction=1,
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', BTC_UST_properties.to_params_list())

    ETH_USD_properties = MarketProperties(
        id=ETH_USD_ID,
        asset=AssetID.ETH,
        asset_collateral=AssetID.USDC,
        leverage=to64x61(10),
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=to64x61(0.0001),
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
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', ETH_USD_properties.to_params_list())

    ETH_UST_properties = MarketProperties(
        id=ETH_UST_ID,
        asset=AssetID.ETH,
        asset_collateral=AssetID.UST,
        leverage=to64x61(10),
        is_tradable=False,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=to64x61(0.0001),
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
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', ETH_UST_properties.to_params_list())

    # Fund the Holding contract
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.UST, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    # Fund the Liquidity fund contract
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.UST, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    # Fund ABR fund contract
    await admin1_signer.send_transaction(admin1, abr_fund.contract_address, 'fund', [BTC_USD_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, abr_fund.contract_address, 'fund', [BTC_UST_ID, to64x61(1000000)])

    # Update collateral prices
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.USDC, to64x61(1)])
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.UST, to64x61(1)])

    # Add accounts to Account Registry
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [alice.contract_address])
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [bob.contract_address])
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [charlie.contract_address])
    await admin1_signer.send_transaction(admin1, accountRegistry.contract_address, 'add_to_account_registry', [dave.contract_address])

    # Set the threshold for oracle price in Trading contract
    await admin1_signer.send_transaction(admin1, trading.contract_address, 'set_threshold_percentage', [to64x61(5)])
    return (starknet_service, non_admin_1, admin1, trading, fixed_math, alice, bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor)


def assert_no_events_emitted(tx_info):
    base = tx_info.call_info.internal_calls[0]
    assert len(base.events) == 0

    internal_calls = base.internal_calls
    for base2 in internal_calls:
        assert len(base2.events) == 0


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


@pytest.mark.asyncio
async def test_fund_called_by_non_authorized_address(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    amount = to64x61(1000000)
    await assert_revert(
        admin2_signer.send_transaction(
            admin2, abr_fund.contract_address, "fund", [BTC_USD_ID, amount]),
        reverted_with="FundLib: Unauthorized call to manage funds"
    )


@pytest.mark.asyncio
async def test_fund_called_by_authorized_address(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory
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

    fund_tx = await admin1_signer.send_transaction(admin1, abr_fund.contract_address, "fund", [BTC_UST_ID, amount])

    assert_event_emitted(
        fund_tx,
        from_address=abr_fund.contract_address,
        name="fund_ABR_called",
        data=[
            BTC_UST_ID,
            amount
        ]
    )

    abr_fund_balance = await abr_fund.balance(BTC_USD_ID).call()
    assert abr_fund_balance.result.amount == abr_fund_balance_before.result.amount + amount


@pytest.mark.asyncio
async def test_defund_called_by_non_authorized_address(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

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
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

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
async def test_set_invalid_no_of_users_in_a_batch(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'set_no_of_users_per_batch', [0]),
        "ABRCore: No of users in a batch must be > 0"
    )

    no_of_users_per_batch_query = await abr_core.get_no_of_users_per_batch().call()
    assert no_of_users_per_batch_query.result.res == 0


@pytest.mark.asyncio
async def test_set_no_of_users_in_a_batch(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await admin1_signer.send_transaction(
        admin1, abr_core.contract_address, 'set_no_of_users_per_batch', [2])

    no_of_users_per_batch_query = await abr_core.get_no_of_users_per_batch().call()
    assert no_of_users_per_batch_query.result.res == 2


@pytest.mark.asyncio
async def test_view_functions_state_0(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    epoch_query = await abr_core.get_epoch().call()
    assert epoch_query.result.res == 0

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 0

    next_timestamp_query = await abr_core.get_next_abr_timestamp().call()
    assert next_timestamp_query.result.res == timestamp_1

    remaining_pay_abr_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_query.result.res == 0

    no_of_batches_query = await abr_core.get_no_of_batches_for_current_epoch().call()
    assert no_of_batches_query.result.res == 0

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == []


@pytest.mark.asyncio
async def test_trades_different_markets(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    ###########################
    ### Open orders BTC_USD ###
    ###########################

    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 12343.3428549
    bob_balance = 9334.98429831
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1.523
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1038.1

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 3,
        "price": 1038.1,
        "leverage": 4.234,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1.523,
        "price": 1038.1,
        "leverage": 5.1,
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ###########################
    ### Open orders ETH_USD ###
    ###########################

    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 2
    market_id_1 = ETH_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 281

    # Create orders
    orders_1 = [{
        "market_id": ETH_USD_ID,
        "quantity": 2,
        "price": 281,
        "leverage": 2.123,
        "order_type": order_types["limit"]
    }, {
        "market_id": ETH_USD_ID,
        "quantity": 2,
        "price": 281,
        "leverage": 3.2,
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)


@pytest.mark.asyncio
async def test_set_invalid_timestamp(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'set_abr_timestamp', [timestamp - 1]),
        "ABRCore: New Timstamp must be > last timestamp + abr_interval"
    )

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 0


@pytest.mark.asyncio
async def test_set_abr_state_0(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    arguments_64x61 = [ETH_UST_ID, 480, *convertTo64x61(
        ABR_data.btc_usd_perp_spot_1), 480, *convertTo64x61(ABR_data.btc_usd_perp_1)]
    # Set BTC_USD ABR
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'set_abr_value', arguments_64x61),
        "ABRCore: Invalid State"
    )


@pytest.mark.asyncio
async def test_pay_abr_state_0(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory
    # Set BTC_USD ABR
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'make_abr_payments', []
        ),
        "ABRCore: Invalid State"
    )


@pytest.mark.asyncio
async def test_set_timestamp(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp_1,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    set_abr_timestamp_tx = await admin1_signer.send_transaction(
        admin1, abr_core.contract_address, 'set_abr_timestamp', [timestamp_1])

    assert_events_emitted_from_all_calls(
        set_abr_timestamp_tx,
        [
            [0, abr_core.contract_address, 'abr_timestamp_set', [1, timestamp_1]],
            [1, abr_core.contract_address, 'state_changed', [1, 1]]
        ]
    )


@ pytest.mark.asyncio
async def test_view_functions_state_1(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment,  timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    epoch_query = await abr_core.get_epoch().call()
    assert epoch_query.result.res == 1

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 1

    next_timestamp_query = await abr_core.get_next_abr_timestamp().call()
    assert next_timestamp_query.result.res == timestamp_1 + 28800

    remaining_pay_abr_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_query.result.res == 0

    no_of_batches_query = await abr_core.get_no_of_batches_for_current_epoch().call()
    assert no_of_batches_query.result.res == 0

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == [
        BTC_USD_ID, BTC_UST_ID, ETH_USD_ID]


@ pytest.mark.asyncio
async def test_set_abr_1(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory
    # Set BTC_USD ABR
    (set_abr_value_tx, abr_value, abr_last_price) = await set_abr_value(market_id=BTC_USD_ID, node_signer=admin1_signer, node=admin1, abr_core=abr_core, abr_executor=abr_executor, timestamp=from64x61(timestamp_1), spot=ABR_data.btc_usd_perp_spot_1, perp=ABR_data.btc_usd_perp_1, spot_64x61=convertTo64x61(ABR_data.btc_usd_perp_spot_1), perp_64x61=convertTo64x61(ABR_data.btc_usd_perp_1), epoch=1, base_rate=0.0000125, boll_width=2.0)

    assert_events_emitted_from_all_calls(
        set_abr_value_tx,
        [
            [0, abr_core.contract_address, 'abr_set',
                [1, BTC_USD_ID, abr_value, abr_last_price]]
        ]
    )

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == [
        BTC_UST_ID, ETH_USD_ID]


@ pytest.mark.asyncio
async def test_set_inequal_length(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    arguments_64x61 = [ETH_USD_ID, 480, *convertTo64x61(
        ABR_data.eth_usd_perp_spot_1), 479, *convertTo64x61(ABR_data.eth_usd_perp_1[:479])]
    # Set BTC_USD ABR
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'set_abr_value', arguments_64x61),
        "ABRCalculations: Index array length must be equal to Perp array length"
    )

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == [
        BTC_UST_ID, ETH_USD_ID]


@ pytest.mark.asyncio
async def test_set_abr_already_set_market(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    arguments_64x61 = [BTC_USD_ID, 480, *convertTo64x61(
        ABR_data.btc_usd_perp_spot_1), 480, *convertTo64x61(ABR_data.btc_usd_perp_1)]
    # Set BTC_USD ABR
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'set_abr_value', arguments_64x61),
        "ABRCore: ABR already set for the market"
    )

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == [
        BTC_UST_ID, ETH_USD_ID]


@pytest.mark.asyncio
async def test_pay_abr_state_1(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory
    # Set BTC_USD ABR
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'make_abr_payments', []
        ),
        "ABRCore: Invalid State"
    )


@ pytest.mark.asyncio
async def test_set_abr_untradable_market(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    arguments_64x61 = [ETH_UST_ID, 480, *convertTo64x61(
        ABR_data.btc_usd_perp_spot_1), 480, *convertTo64x61(ABR_data.btc_usd_perp_1)]
    # Set BTC_USD ABR
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'set_abr_value', arguments_64x61),
        "ABRCore: Given Market is not tradable"
    )

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == [
        BTC_UST_ID, ETH_USD_ID]


@ pytest.mark.asyncio
async def test_set_abr_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory
    # Set ETH_USD ABR
    (set_abr_value_tx, abr_value, abr_last_price) = await set_abr_value(market_id=ETH_USD_ID, node_signer=admin1_signer, node=admin1, abr_core=abr_core, abr_executor=abr_executor, timestamp=from64x61(timestamp_1), spot=ABR_data.eth_usd_perp_spot_1, perp=ABR_data.eth_usd_perp_1, spot_64x61=convertTo64x61(ABR_data.eth_usd_perp_spot_1), perp_64x61=convertTo64x61(ABR_data.eth_usd_perp_1), epoch=1, base_rate=0.0000125, boll_width=2.0)

    assert_events_emitted_from_all_calls(
        set_abr_value_tx,
        [
            [0, abr_core.contract_address, 'abr_set',
                [1, ETH_USD_ID, abr_value, abr_last_price]]
        ]
    )

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == [
        BTC_UST_ID]


@ pytest.mark.asyncio
async def test_pay_abr_state_1(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, "make_abr_payments", []),
        "ABRCore: Invalid State"
    )


@ pytest.mark.asyncio
async def test_set_timestamp_state_1(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await assert_revert(
        admin1_signer.send_transaction(
            admin1, abr_core.contract_address, 'set_abr_timestamp', [timestamp_2]),
        "ABRCore: Invalid State"
    )


@ pytest.mark.asyncio
async def test_set_abr_3(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory
    # Set BTC_UST ABR
    (set_abr_value_tx, abr_value, abr_last_price) = await set_abr_value(market_id=BTC_UST_ID, node_signer=admin1_signer, node=admin1, abr_core=abr_core, abr_executor=abr_executor, timestamp=from64x61(timestamp_1), spot=ABR_data.btc_ust_perp_spot_1, perp=ABR_data.btc_ust_perp_1, spot_64x61=convertTo64x61(ABR_data.btc_ust_perp_spot_1), perp_64x61=convertTo64x61(ABR_data.btc_ust_perp_1), epoch=1, base_rate=0.0000125, boll_width=2.0)

    assert_events_emitted_from_all_calls(
        set_abr_value_tx,
        [
            [0, abr_core.contract_address, 'abr_set',
                [1, BTC_UST_ID, abr_value, abr_last_price]],
            [1, abr_core.contract_address, 'state_changed',
                [1, 2]],

        ]
    )
    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == []


@ pytest.mark.asyncio
async def test_view_functions_state_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    epoch_query = await abr_core.get_epoch().call()
    assert epoch_query.result.res == 1

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 2

    next_timestamp_query = await abr_core.get_next_abr_timestamp().call()
    assert next_timestamp_query.result.res == timestamp_1 + 28800

    remaining_pay_abr_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_query.result.res == 2

    no_of_batches_query = await abr_core.get_no_of_batches_for_current_epoch().call()
    assert no_of_batches_query.result.res == 2

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == []


@ pytest.mark.asyncio
async def test_trade_new_market(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp_2,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ###########################
    ### Open orders BTC_UST ###
    ###########################

    # List of users
    users = [charlie, dave]
    users_test = [charlie_test, dave_test]

    # Sufficient balance for users
    charlie_balance = 10000
    dave_balance = 10000
    balance_array = [charlie_balance, dave_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_UST_ID
    asset_id_1 = AssetID.UST
    oracle_price_1 = 1200

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "market_id": BTC_UST_ID,
        "quantity": 1,
        "price": 1200,
        "leverage": 1,
        "order_type": order_types["limit"]
    }, {
        "market_id": BTC_UST_ID,
        "quantity": 1,
        "price": 1200,
        "leverage": 1,
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp_2), is_reverted=0, error_code=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)


@ pytest.mark.asyncio
async def test_pay_abr_call_1(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    abr_tx = await make_abr_payments(admin_signer=admin1_signer, admin=admin1, abr_core=abr_core,
                                     abr_executor=abr_executor, users_test=[alice_test, bob_test], timestamp=from64x61(timestamp_2))

    await compare_user_balances(users=[alice, bob], user_tests=[alice_test, bob_test], asset_id=AssetID.USDC)
    await compare_user_positions(users=[alice, bob], users_test=[alice_test, bob_test], market_id=BTC_USD_ID)
    await compare_user_positions(users=[alice, bob], users_test=[alice_test, bob_test], market_id=ETH_USD_ID)

    remaining_pay_abr_calls_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_calls_query.result.res == 1

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 2


@ pytest.mark.asyncio
async def test_pay_abr_call_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await make_abr_payments(admin_signer=admin1_signer, admin=admin1, abr_core=abr_core,
                            abr_executor=abr_executor, users_test=[charlie_test, dave_test], timestamp=from64x61(timestamp_2))

    await compare_user_balances(users=[charlie, dave], user_tests=[charlie_test, dave_test], asset_id=AssetID.UST)
    await compare_user_positions(users=[charlie, dave], users_test=[charlie_test, dave_test], market_id=BTC_UST_ID)

    remaining_pay_abr_calls_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_calls_query.result.res == 0

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 0


@pytest.mark.asyncio
async def test_abr_interval_unauthorized(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    hour_1 = 60*60
    await assert_revert(
        non_admin_signer.send_transaction(
            non_admin, abr_core.contract_address, 'set_abr_interval', [hour_1]),
        "ABRCore: Unauthorized Call"
    )


@pytest.mark.asyncio
async def test_abr_interval_invalid(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await assert_revert(
        admin2_signer.send_transaction(
            admin2, abr_core.contract_address, 'set_abr_interval', [0]),
        "ABRCore: new_abr_interval must be > 0"
    )


@pytest.mark.asyncio
async def test_abr_interval(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    hour_1 = 60*60
    await admin1_signer.send_transaction(
        admin1, abr_core.contract_address, 'set_abr_interval', [hour_1])


@pytest.mark.asyncio
async def test_view_functions_state_0_round_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    epoch_query = await abr_core.get_epoch().call()
    assert epoch_query.result.res == 1

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 0

    next_timestamp_query = await abr_core.get_next_abr_timestamp().call()
    assert next_timestamp_query.result.res == timestamp_1 + 3600

    remaining_pay_abr_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_query.result.res == 0

    no_of_batches_query = await abr_core.get_no_of_batches_for_current_epoch().call()
    assert no_of_batches_query.result.res == 0

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == []


@pytest.mark.asyncio
async def test_set_timestamp_invalid_epoch_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp_3,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )
    await assert_revert(admin1_signer.send_transaction(
        admin1, abr_core.contract_address, 'set_abr_timestamp', [timestamp_3]),
        "ABRCore: New Timstamp must be > last timestamp + abr_interval"
    )


@ pytest.mark.asyncio
async def test_set_timestamp_epoch_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp_3,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    set_abr_timestamp_tx = await admin1_signer.send_transaction(
        admin1, abr_core.contract_address, 'set_abr_timestamp', [timestamp_4])

    assert_events_emitted_from_all_calls(
        set_abr_timestamp_tx,
        [
            [0, abr_core.contract_address, 'abr_timestamp_set', [2, timestamp_4]],
            [1, abr_core.contract_address, 'state_changed', [2, 1]],
        ]
    )


@pytest.mark.asyncio
async def test_view_functions_state_1_round_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    epoch_query = await abr_core.get_epoch().call()
    assert epoch_query.result.res == 2

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 1

    next_timestamp_query = await abr_core.get_next_abr_timestamp().call()
    assert next_timestamp_query.result.res == timestamp_4 + 3600

    remaining_pay_abr_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_query.result.res == 0

    no_of_batches_query = await abr_core.get_no_of_batches_for_current_epoch().call()
    assert no_of_batches_query.result.res == 0

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == [
        BTC_USD_ID, BTC_UST_ID, ETH_USD_ID]


@pytest.mark.asyncio
async def test_set_bollinger_width_unauthorized(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await assert_revert(non_admin_signer.send_transaction(
        non_admin, abr_core.contract_address, 'set_bollinger_width', [to64x61(1.5)]),
        "ABRCore: Unauthorized Call"
    )


@pytest.mark.asyncio
async def test_set_bollinger_width_authorized(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await admin1_signer.send_transaction(admin1, abr_core.contract_address, 'set_bollinger_width', [to64x61(1.5)])

    bollinger_width_query = await abr_core.get_bollinger_width().call()
    assert from64x61(bollinger_width_query.result.res) == 1.5


@pytest.mark.asyncio
async def test_set_base_abr_rate_unauthorized(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await assert_revert(non_admin_signer.send_transaction(
        non_admin, abr_core.contract_address, 'set_base_abr_rate', [to64x61(0.000025)]),
        "ABRCore: Unauthorized Call"
    )


@pytest.mark.asyncio
async def test_set_base_abr_rate_authorized(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    await admin1_signer.send_transaction(admin1, abr_core.contract_address, 'set_base_abr_rate', [to64x61(0.000025)])

    base_abr_rate_query = await abr_core.get_base_abr_rate().call()
    assert from64x61(base_abr_rate_query.result.res) == pytest.approx(
        0.000025, abs=1e-3)


@pytest.mark.asyncio
async def test_set_abr_round_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    # Set BTC_UST ABR
    (set_abr_value_tx, abr_value, abr_last_price) = await set_abr_value(market_id=BTC_UST_ID, node_signer=admin1_signer, node=admin1, abr_core=abr_core, abr_executor=abr_executor, timestamp=from64x61(timestamp_4), spot=ABR_data.btc_ust_perp_spot_2, perp=ABR_data.btc_ust_perp_2, spot_64x61=convertTo64x61(ABR_data.btc_ust_perp_spot_2), perp_64x61=convertTo64x61(ABR_data.btc_ust_perp_2), epoch=2, base_rate=0.000025, boll_width=1.5)

    assert_events_emitted_from_all_calls(
        set_abr_value_tx,
        [
            [0, abr_core.contract_address, 'abr_set',
                [2, BTC_UST_ID, abr_value, abr_last_price]]
        ]
    )
    # Set BTC_USD ABR
    (set_abr_value_tx, abr_value, abr_last_price) = await set_abr_value(market_id=BTC_USD_ID, node_signer=admin1_signer, node=admin1, abr_core=abr_core, abr_executor=abr_executor, timestamp=from64x61(timestamp_4), spot=ABR_data.btc_usd_perp_spot_2, perp=ABR_data.btc_usd_perp_2, spot_64x61=convertTo64x61(ABR_data.btc_usd_perp_spot_2), perp_64x61=convertTo64x61(ABR_data.btc_usd_perp_2), epoch=2, base_rate=0.000025, boll_width=1.5)

    assert_events_emitted_from_all_calls(
        set_abr_value_tx,
        [
            [0, abr_core.contract_address, 'abr_set',
                [2, BTC_USD_ID, abr_value, abr_last_price]]
        ]
    )
    # Set ETH_USD ABR
    (set_abr_value_tx, abr_value, abr_last_price) = await set_abr_value(market_id=ETH_USD_ID, node_signer=admin1_signer, node=admin1, abr_core=abr_core, abr_executor=abr_executor, timestamp=from64x61(timestamp_4), spot=ABR_data.eth_usd_perp_spot_2, perp=ABR_data.eth_usd_perp_2, spot_64x61=convertTo64x61(ABR_data.eth_usd_perp_spot_2), perp_64x61=convertTo64x61(ABR_data.eth_usd_perp_2), epoch=2, base_rate=0.000025, boll_width=1.5)

    assert_events_emitted_from_all_calls(
        set_abr_value_tx,
        [
            [0, abr_core.contract_address, 'abr_set',
                [2, ETH_USD_ID, abr_value, abr_last_price]],
            [1, abr_core.contract_address, 'state_changed',
                [2, 2]
             ]
        ]
    )
    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == []


@pytest.mark.asyncio
async def test_view_functions_state_2_round_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    epoch_query = await abr_core.get_epoch().call()
    assert epoch_query.result.res == 2

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 2

    next_timestamp_query = await abr_core.get_next_abr_timestamp().call()
    assert next_timestamp_query.result.res == timestamp_4 + 3600

    remaining_pay_abr_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_query.result.res == 2

    no_of_batches_query = await abr_core.get_no_of_batches_for_current_epoch().call()
    assert no_of_batches_query.result.res == 2

    remaining_markets_query = await abr_core.get_markets_remaining().call()
    assert remaining_markets_query.result.remaining_markets_list == []


@pytest.mark.asyncio
async def test_make_abr_payments_round_2(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    abr_tx = await make_abr_payments(admin_signer=admin1_signer, admin=admin1, abr_core=abr_core,
                                     abr_executor=abr_executor, users_test=[alice_test, bob_test], timestamp=from64x61(timestamp_4))

    await compare_user_balances(users=[alice, bob], user_tests=[alice_test, bob_test], asset_id=AssetID.USDC)
    await compare_user_positions(users=[alice, bob], users_test=[alice_test, bob_test], market_id=BTC_USD_ID)
    await compare_user_positions(users=[alice, bob], users_test=[alice_test, bob_test], market_id=ETH_USD_ID)

    remaining_pay_abr_calls_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_calls_query.result.res == 1

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 2

    abr_tx = await make_abr_payments(admin_signer=admin1_signer, admin=admin1, abr_core=abr_core,
                                     abr_executor=abr_executor, users_test=[charlie_test, dave_test], timestamp=from64x61(timestamp_4))

    await compare_user_balances(users=[charlie, dave], user_tests=[charlie_test, dave_test], asset_id=AssetID.USDC)
    await compare_user_positions(users=[charlie, dave], users_test=[charlie_test, dave_test], market_id=BTC_UST_ID)
    await compare_user_positions(users=[charlie, dave], users_test=[charlie_test, dave_test], market_id=ETH_USD_ID)

    remaining_pay_abr_calls_query = await abr_core.get_remaining_pay_abr_calls().call()
    assert remaining_pay_abr_calls_query.result.res == 0

    state_query = await abr_core.get_state().call()
    assert state_query.result.res == 0


@pytest.mark.asyncio
async def test_abr_result_different_length(abr_factory):
    starknet_service, non_admin, admin1, trading, fixed_math, alice,  bob, charlie, dave, abr_calculations, abr_core, abr_fund, abr_payment, timestamp, admin2, alice_test, bob_test, charlie_test, dave_test, python_executor, abr_executor = abr_factory

    spot_array = ABR_data.btc_usd_perp_spot_1
    perp_array = ABR_data.btc_usd_perp_1
    spot_array_64x61 = convertTo64x61(spot_array)
    perp_array_64x61 = convertTo64x61(perp_array)
    market_id = BTC_USD_ID

    data_points = [60*i for i in range(1, 9)]
    for i in data_points:
        python_abr_rate = calculate_abr(
            perp_spot=spot_array[:i], perp=perp_array[:i], base_rate=0.000025, boll_width=1.5)

        abr_query = await abr_calculations.calculate_abr(spot_array_64x61[:i], perp_array_64x61[:i], to64x61(1.5), to64x61(0.000025)).call()

        print("i:", i)
        print("Python rate", python_abr_rate)
        print("Cairo rate", from64x61(abr_query.result.abr_value), "\n")
        assert python_abr_rate == pytest.approx(
            from64x61(abr_query.result.abr_value), abs=1e-6)
