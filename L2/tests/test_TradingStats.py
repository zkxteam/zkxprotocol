from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61
from utils_trading import User, order_direction, order_types, order_time_in_force, order_life_cycles, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, check_batch_status
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


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
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")

initial_timestamp = int(time.time())
timestamp2 = int(time.time()) + (60*60*24) + 60
timestamp3 = int(time.time()) + (60*60*24)*2 + 60
timestamp4 = int(time.time()) + (60*60*24)*3 + 60
timestamp5 = int(time.time()) + (60*60*24)*31 + 60


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
    # Deploy infrastructure (Part 1)
    admin1 = await starknet_service.deploy(ContractType.Account, [
        admin1_signer.public_key
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        admin2_signer.public_key
    ])
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    fees = await starknet_service.deploy(ContractType.TradingFees, [registry.contract_address, 1])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])

    python_executor = OrderExecutor()
    # Deploy user accounts
    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )
    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    alice_test = User(123456789987654323, alice.contract_address)

    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    bob_test = User(123456789987654324, bob.contract_address)

    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)
    charlie_test = User(123456789987654325, charlie.contract_address)

    dave = await account_factory.deploy_account(dave_signer.public_key)

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=initial_timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    # Deploy infrastructure (Part 2)
    fixed_math = await starknet_service.deploy(ContractType.Math_64x61, [])
    holding = await starknet_service.deploy(ContractType.Holding, [registry.contract_address, 1])
    feeBalance = await starknet_service.deploy(ContractType.FeeBalance, [registry.contract_address, 1])
    market = await starknet_service.deploy(ContractType.Markets, [registry.contract_address, 1])
    liquidity = await starknet_service.deploy(ContractType.LiquidityFund, [registry.contract_address, 1])
    insurance = await starknet_service.deploy(ContractType.InsuranceFund, [registry.contract_address, 1])
    emergency = await starknet_service.deploy(ContractType.EmergencyFund, [registry.contract_address, 1])
    trading = await starknet_service.deploy(ContractType.Trading, [registry.contract_address, 1])
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [registry.contract_address, 1])
    marketPrices = await starknet_service.deploy(ContractType.MarketPrices, [registry.contract_address, 1])
    liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
    collateral_prices = await starknet_service.deploy(
        ContractType.CollateralPrices,
        [registry.contract_address, 1]
    )
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
    user_stats = await starknet_service.deploy(ContractType.UserStats, [registry.contract_address, 1])

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Access 2 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 7, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 8, 1])

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # add user accounts to account registry
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [admin1.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [admin2.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [alice.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [bob.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [charlie.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [dave.contract_address])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [3, 1, feeDiscount.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [4, 1, fees.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [5, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [6, 1, feeBalance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [7, 1, holding.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [8, 1, emergency.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [9, 1, liquidity.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [10, 1, insurance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [11, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [13, 1, collateral_prices.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [21, 1, marketPrices.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [24, 1, hightide.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [25, 1, trading_stats.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [26, 1, user_stats.contract_address])

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

    # Add assets
    BTC_properties = build_asset_properties(
        id=AssetID.BTC,
        asset_version=1,
        short_name=str_to_felt("BTC"),
        is_tradable=True,
        is_collateral=False,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', BTC_properties)

    ETH_properties = build_asset_properties(
        id=AssetID.ETH,
        asset_version=1,
        short_name=str_to_felt("ETH"),
        is_tradable=True,
        is_collateral=False,
        token_decimal=18
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', ETH_properties)

    USDC_properties = build_asset_properties(
        id=AssetID.USDC,
        asset_version=1,
        short_name=str_to_felt("USDC"),
        is_tradable=False,
        is_collateral=True,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', USDC_properties)

    UST_properties = build_asset_properties(
        id=AssetID.UST,
        asset_version=1,
        short_name=str_to_felt("UST"),
        is_tradable=True,
        is_collateral=True,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', UST_properties)

    DOGE_properties = build_asset_properties(
        id=AssetID.DOGE,
        asset_version=1,
        short_name=str_to_felt("DOGE"),
        is_tradable=False,
        is_collateral=False,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', DOGE_properties)

    TESLA_properties = build_asset_properties(
        id=AssetID.TSLA,
        asset_version=1,
        short_name=str_to_felt("TESLA"),
        is_tradable=True,
        is_collateral=False,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', TESLA_properties)

    # Add markets
    BTC_USD_properties = MarketProperties(
        id=BTC_USD_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.USDC,
        leverage=to64x61(10),
        is_tradable=True,
        is_archived=False,
        ttl=60,
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
        minimum_order_size=10,
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
        minimum_order_size=10,
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
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', ETH_USD_properties.to_params_list())

    TSLA_USD_properties = MarketProperties(
        id=TSLA_USD_ID,
        asset=AssetID.TSLA,
        asset_collateral=AssetID.USDC,
        leverage=to64x61(10),
        is_tradable=False,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=10,
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
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', TSLA_USD_properties.to_params_list())

    UST_USDC_properties = MarketProperties(
        id=UST_USDC_ID,
        asset=AssetID.UST,
        asset_collateral=AssetID.USDC,
        leverage=to64x61(10),
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=10,
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
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', UST_USDC_properties.to_params_list())

    # Update collateral prices
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.USDC, to64x61(1)])
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.UST, to64x61(1)])

    # Fund the Holding contract
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    # Fund the Liquidity fund contract
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    season_id = 1
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, to64x61(30)])

    # Set the threshold for oracle price in Trading contract
    await admin1_signer.send_transaction(admin1, trading.contract_address, 'set_threshold_percentage', [to64x61(5)])
    return starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, marketPrices, liquidate, trading_stats, hightide, alice_test, bob_test, charlie_test, python_executor


@pytest.mark.asyncio
async def test_unauthorized_call(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, alice_test, bob_test, _, python_executor = adminAuth_factory

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
    oracle_price_1 = 5000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    alice_order = {
        "quantity": 1,
        "price": 5000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }

    bob_order = {
        "quantity": 1,
        "price": 5000,
    }

    # Create orders
    (_, alice_order_64x61) = alice_test.create_order(**alice_order)

    (_, bob_order_64x61) = bob_test.create_order(**bob_order)

    # TraderStats
    alice_stats = [
        alice.contract_address,
        to64x61(1),
        to64x61(5000),
        to64x61(1),
        to64x61(23),
        to64x61(5000)
    ]

    bob_stats = [
        bob.contract_address,
        to64x61(1),
        to64x61(5000),
        to64x61(1),
        to64x61(23),
        to64x61(5000)
    ]

    # execute order
    await assert_revert(
        dave_signer.send_transaction(dave, trading_stats.contract_address, "record_trade_batch_stats", [
            market_id_1,
            to64x61(oracle_price_1),
            2,
            *alice_order_64x61.values(),
            *bob_order_64x61.values(),
            2,
            *alice_stats,
            *bob_stats,
            2,
            to64x61(1),
            to64x61(1),
            to64x61(1),
        ]), "TradingStats: Trade can be recorded only by Trading contract"
    )


@pytest.mark.asyncio
async def test_invalid_season_id_call(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, alice_test, bob_test, _, python_executor = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 5000

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 5000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }, {
        "quantity": 1,
        "price": 5000,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    # Check for tradings stats
    season_id = 0
    await assert_revert(trading_stats.get_total_days_traded(season_id, market_id_1).call(), "Invalid season id")

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id_1).call()
    assert active_traders.result.res == 0

    await assert_revert(trading_stats.get_max_trades_in_day(season_id, market_id_1).call(), "Invalid season id")

    order_volume = await trading_stats.get_order_volume((season_id, market_id_1, 0)).call()
    assert order_volume.result[0] == 0
    assert from64x61(order_volume.result[1]) == 0


@pytest.mark.asyncio
async def test_opening_orders_day_0(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, alice_test, bob_test, _, python_executor = adminAuth_factory

    # start season to test recording of trade stats
    season_id = 1
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [
        season_id])

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 5000
    execution_price_1 = 5000

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 5000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }, {
        "quantity": 1,
        "price": 5000,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_1

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    assert days_traded.result.res == 1

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 0).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    assert trade_frequency.result.frequency == [2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, market_id, 1)).call()
    print("Order volume long, day 0:", from64x61(order_volume.result[1]))
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_1*execution_price_1


@pytest.mark.asyncio
async def test_closing_orders_day_1(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, alice_test, bob_test, _, python_executor = adminAuth_factory

    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp2,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    quantity_locked_1 = 1
    execution_price_1 = 5000
    #### Closing Of Orders ########
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_2 = 1
    market_id_2 = BTC_USD_ID
    oracle_price_2 = 6000

    # Create orders
    orders_2 = [{
        "price": 6000,
        "order_type": order_types["limit"],
        "life_cycle": order_life_cycles["close"]
    }, {
        "price": 6000,
        "direction": order_direction["short"],
        "life_cycle": order_life_cycles["close"]
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)

    season_id = 1

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id_2).call()
    print(days_traded.result.res)
    assert days_traded.result.res == 2

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id_2, 1).call()
    assert num_trades_in_a_day.result.res == 2
    print(num_trades_in_a_day.result.res)

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id_2).call()
    assert active_traders.result.res == 2
    print(active_traders.result.res)

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id_2).call()
    assert trade_frequency.result.frequency == [2, 2]
    print(trade_frequency.result.frequency)

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id_2).call()
    assert max_trades.result.res == 2
    print(max_trades.result.res)

    order_volume = await trading_stats.get_order_volume((season_id, market_id_2, 1)).call()
    print("Order volume open, day 1:", from64x61(order_volume.result[1]))
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        execution_price_1*quantity_locked_1

    order_volume = await trading_stats.get_order_volume((season_id, market_id_2, 2)).call()
    print("Order volume close, day 1:", from64x61(order_volume.result[1]))
    print(order_volume.result[0], from64x61(order_volume.result[1]))
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2*oracle_price_2


@pytest.mark.asyncio
async def test_opening_orders_day_2(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, alice_test, bob_test, _, python_executor = adminAuth_factory

    # here we check the scenario that there are multiple calls to record_trade_batch_stats in a single day
    # we also check that recording is handled properly when orders are executed partially
    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp3,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ######### Open orders ##############
    quantity_locked_1 = 1
    execution_price_1 = 5000

    quantity_locked_2 = 1
    execution_price_2 = 6000
    ####### Opening of Orders Partially #######
    users_test = [alice_test, bob_test]
    quantity_locked_3 = 1
    market_id_3 = BTC_USD_ID
    oracle_price_3 = 6500

    orders_3 = [{
        "price": 6500,
        "quantity": 2,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }, {
        "price": 6500,
    }]

    # execute order
    (_, complete_orders_3, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_3, users_test=users_test, quantity_locked=quantity_locked_3, market_id=market_id_3, oracle_price=oracle_price_3, trading=trading, is_reverted=0, error_code=0)

    season_id = 1

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id_3).call()
    print(days_traded.result.res)
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id_3, 2).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id_3).call()
    print(active_traders.result.res)
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id_3).call()
    print(trade_frequency.result.frequency)
    assert trade_frequency.result.frequency == [2, 2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id_3).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, market_id_3, 1)).call()
    print("Order volume open, day 2:", from64x61(order_volume.result[1]))
    assert order_volume.result[0] == 4
    assert from64x61(order_volume.result[1]) == 2*quantity_locked_1 * \
        execution_price_1 + 2*quantity_locked_3*oracle_price_3

    order_volume = await trading_stats.get_order_volume((season_id, market_id_3, 2)).call()
    print("Order volume close, day 2:", from64x61(order_volume.result[1]))
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2*execution_price_2

    ####### Opening of Orders Partially 2 #######

    # Create orders
    orders_4 = [{
        "order_id": complete_orders_3[0]["order_id"]
    }, {
        "price": 6500,
    }]

    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_4, users_test=users_test, quantity_locked=quantity_locked_3, market_id=market_id_3, oracle_price=oracle_price_3, trading=trading, is_reverted=0, error_code=0)

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id_3).call()
    print(days_traded.result.res)
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id_3, 2).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 4

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id_3).call()
    print(active_traders.result.res)
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id_3).call()
    print(trade_frequency.result.frequency)
    assert trade_frequency.result.frequency == [2, 2, 4]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id_3).call()
    assert max_trades.result.res == 4

    order_volume = await trading_stats.get_order_volume((season_id, market_id_3, 1)).call()
    print("Order volume open, day 2:", from64x61(order_volume.result[1]))
    assert order_volume.result[0] == 6
    assert from64x61(order_volume.result[1]) == 2*quantity_locked_1 * \
        execution_price_1 + 4*quantity_locked_3*oracle_price_3

    order_volume = await trading_stats.get_order_volume((season_id, market_id_3, 2)).call()
    print("Order volume close, day 2:", from64x61(order_volume.result[1]))
    print("real", order_volume.result)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2*execution_price_2


@pytest.mark.asyncio
async def test_opening_closing_orders_day_3(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

    # here we test with new traders in request_list
    # we also test a batch of trades with open as well as close type orders

    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp4,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ######### Open orders ##############
    quantity_locked_1 = 1
    execution_price_1 = 5000

    quantity_locked_2 = 1
    execution_price_2 = 6000

    quantity_locked_3 = 1
    execution_price_3 = 6500

    ####### Opening of Orders #######
    quantity_locked_4 = 1
    users_test = [alice_test, charlie_test]
    asset_id_4 = AssetID.USDC
    market_id_4 = BTC_USD_ID
    oracle_price_4 = 7000

    charlie_balance = 50000
    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=[charlie], users_test=[charlie_test], balance_array=[charlie_balance], asset_id=asset_id_4)

    # Create Orders
    orders_5 = [{
        "leverage": 4,
        "price": 7000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"]
    }, {
        "leverage": 2,
        "price": 7000,
    }]

    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_5, users_test=users_test, quantity_locked=quantity_locked_4, market_id=market_id_4, oracle_price=oracle_price_4, trading=trading, is_reverted=0, error_code=0)

    orders_6 = [{
        "price": 7000,
        "life_cycle": order_life_cycles["close"],
        "order_type": order_types["limit"]
    }, {
        "price": 7000,
        "life_cycle": order_life_cycles["close"],
        "direction": order_direction["short"]
    }]

    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_6, users_test=[alice_test, bob_test], quantity_locked=quantity_locked_4, market_id=market_id_4, oracle_price=oracle_price_4, trading=trading, is_reverted=0, error_code=0)

    season_id = 1

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id_4).call()
    assert days_traded.result.res == 4

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id_4, 3).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 4

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id_4).call()
    assert active_traders.result.res == 3

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id_4).call()
    assert trade_frequency.result.frequency == [2, 2, 4, 4]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id_4).call()
    assert max_trades.result.res == 4

    order_volume = await trading_stats.get_order_volume((season_id, market_id_4, 1)).call()
    print("Order volume open, day 3:", from64x61(order_volume.result[1]))
    print(2*quantity_locked_1 *
          execution_price_1 + 4*quantity_locked_3*execution_price_3
          + 2*quantity_locked_4*oracle_price_4)
    assert order_volume.result[0] == 8
    assert from64x61(order_volume.result[1]) == 2*quantity_locked_1 * execution_price_1 + \
        4*quantity_locked_3*execution_price_3 + 2*quantity_locked_4*oracle_price_4

    order_volume = await trading_stats.get_order_volume((season_id, market_id_4, 2)).call()
    print("Order volume close, day 3:", from64x61(order_volume.result[1]))
    assert order_volume.result[0] == 4
    assert from64x61(order_volume.result[1]) == 2 * quantity_locked_2 * \
        execution_price_2 + 2*quantity_locked_4*oracle_price_4


@pytest.mark.asyncio
async def test_opening_orders_day_32(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

    # test recording after season has ended - no calls should be recorded
    # this test being commented out till num_trading_days bug fixed in hightide contract

    return

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp5,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )
    #### Open orders ##############
    size1 = to64x61(1)
    execution_price1 = to64x61(5000)

    size2 = to64x61(1)
    execution_price2 = to64x61(6000)

    size3 = to64x61(1)
    execution_price3 = to64x61(650)

    size4 = to64x61(1)
    execution_price4 = to64x61(7000)

    marketID_1 = BTC_USD_ID

    ####### Opening of Orders #######
    size1 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("sdj324hka8kaedf123")
    assetID_1 = AssetID.BTC
    collateralID_1 = AssetID.USDC
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("wer4iljerw123")
    assetID_2 = AssetID.BTC
    collateralID_2 = AssetID.USDC
    price2 = to64x61(5000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ])

    season_id = 1
    market_id = marketID_1

    # all stats should be same as per previous probe except frequency table
    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    assert days_traded.result.res == 4

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 30).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 0

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    assert active_traders.result.res == 3

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    assert trade_frequency.result.frequency == [2, 2, 4, 4] + 26*[0]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 4

    order_volume = await trading_stats.get_order_volume((season_id, market_id, 0)).call()
    print(order_volume.result)
    assert order_volume.result[0] == 8
    assert from64x61(order_volume.result[1]) == (2*from64x61(size1)*from64x61(execution_price1) + 4*from64x61(size3)*from64x61(execution_price3)
                                                 + 2*from64x61(size4)*from64x61(execution_price4))

    order_volume = await trading_stats.get_order_volume((season_id, market_id, 1)).call()
    print(order_volume.result)
    assert order_volume.result[0] == 4
    assert from64x61(order_volume.result[1]) == (2*from64x61(size2)*from64x61(execution_price2)
                                                 + 2*from64x61(size4)*from64x61(execution_price4))
