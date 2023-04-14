from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, str_to_felt, MAX_UINT256, assert_revert, from64x61, to64x61
from utils_links import DEFAULT_LINK_1
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from utils_trading import User, order_direction, order_types, side, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, check_batch_status
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
dave_signer = Signer(123456789987654326)
eduard_signer = Signer(123456789987654327)
gary_signer = Signer(123456789987654328)

maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")
class_hash = 0

initial_timestamp = int(time.time())
DAY_DURATION = 24 * 60 * 60
timestamp2 = int(time.time()) + (DAY_DURATION) + 60
timestamp3 = int(time.time()) + (DAY_DURATION)*2 + 60
timestamp4 = int(time.time()) + (DAY_DURATION)*3 + 60
timestamp5 = int(time.time()) + (DAY_DURATION)*4 + 60
timestamp6 = int(time.time()) + (DAY_DURATION)*5 + 60

SET_XP_NOT_STARTED = 0
SET_XP_IN_PROGRESS = 1
SET_XP_COMPLETED = 2


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

    contract_class = starknet_service.contracts_holder.get_contract_class(
        ContractType.LiquidityPool)
    global class_hash
    class_hash, _ = await starknet_service.starknet.state.declare(contract_class)
    direct_class_hash = compute_class_hash(contract_class)
    class_hash = int.from_bytes(class_hash, 'big')
    assert direct_class_hash == class_hash

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
    hightide = await starknet_service.deploy(ContractType.TestHighTide, [registry.contract_address, 1])
    hightideCalc = await starknet_service.deploy(ContractType.HighTideCalc, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
    user_stats = await starknet_service.deploy(ContractType.UserStats, [registry.contract_address, 1])
    rewardsCalculation = await starknet_service.deploy(ContractType.RewardsCalculation, [registry.contract_address, 1])
    starkway = await starknet_service.deploy(ContractType.Starkway, [registry.contract_address, 1])

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
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 10, 1])

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
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [27, 1, starkway.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [29, 1, rewardsCalculation.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [30, 1, hightideCalc.contract_address])

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
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', TSLA_USD_properties.to_params_list())

    UST_USDC_properties = MarketProperties(
        id=UST_USDC_ID,
        asset=AssetID.UST,
        asset_collateral=AssetID.USDC,
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
        initial_timestamp, 5])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [1])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'set_liquidity_pool_contract_class_hash', [class_hash])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', [ETH_USD_ID, 1, admin1.contract_address, 1, 2, AssetID.USDC, 1000, 0, AssetID.UST, 500, 0])
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', [TSLA_USD_ID, 1, admin1.contract_address, 1, 2, AssetID.USDC, 1000, 0, AssetID.UST, 500, 0])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'set_constants', [
        to64x61(0.8),
        to64x61(0.15),
        to64x61(0.05),
        to64x61(3),
        to64x61(0.3)
    ])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'set_multipliers', [
        to64x61(1),
        to64x61(1),
        to64x61(1),
        to64x61(1),
    ])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'activate_high_tide', [1])
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'activate_high_tide', [2])

    # set the no.of users in a batch for Trader's score calculation and reward distribution
    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, 'set_no_of_users_per_batch', [10])

    # set the no.of users in a batch for xp
    await admin1_signer.send_transaction(admin1, rewardsCalculation.contract_address, 'set_no_of_users_per_batch', [10])

    return starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, marketPrices, liquidate, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation, alice_test, bob_test, charlie_test, python_executor


@pytest.mark.asyncio
async def test_placing_orders_day_0(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

    ##########################
    ### Open orders BTC_USD ##
    ##########################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 100000
    bob_balance = 100000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 5000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

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

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    print(order_volume)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_1*oracle_price_1

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    fee = pytest.approx(
        (from64x61(maker_trading_fees) * quantity_locked_1*oracle_price_1), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    fee = pytest.approx(
        (from64x61(taker_trading_fees) * quantity_locked_1*oracle_price_1), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(
        trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_1 * oracle_price_1

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_1 * oracle_price_1

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 0
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 0

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0

    ##########################
    ### Open orders ETH_USD ##
    ##########################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_2 = 2
    market_id_2 = ETH_USD_ID
    oracle_price_2 = 500

    # Create orders
    orders_2 = [{
        "quantity": 2,
        "market_id": ETH_USD_ID,
        "price": 500,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }, {
        "quantity": 2,
        "market_id": ETH_USD_ID,
        "price": 500,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_2

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

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    print(order_volume)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2*oracle_price_2

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees) *
                        quantity_locked_2*oracle_price_2), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees) *
                        quantity_locked_2*oracle_price_2), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(
        trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_2*oracle_price_2

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_2*oracle_price_2

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 0
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 0

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0

    #############################
    ### Open orders TELSA_USD ###
    #############################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_3 = 4
    market_id_3 = TSLA_USD_ID
    oracle_price_3 = 50

    # Create orders
    orders_3 = [{
        "quantity": 4,
        "market_id": TSLA_USD_ID,
        "price": 50,
        "order_type": order_types["limit"],
    }, {
        "quantity": 4,
        "market_id": TSLA_USD_ID,
        "price": 50,
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_3, users_test=users_test, quantity_locked=quantity_locked_3, market_id=market_id_3, oracle_price=oracle_price_3, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_3

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

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    print(order_volume)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_3 * oracle_price_3

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees) *
                        quantity_locked_3 * oracle_price_3), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees) *
                        quantity_locked_3 * oracle_price_3), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(
        trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_3 * oracle_price_3

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_3 * oracle_price_3

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 0
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 0

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0

    await assert_revert(admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_w", [
        season_id,
        market_id,
    ]), "HighTideCalc: Season still ongoing")

    await assert_revert(admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_trader_score", [
        season_id,
        market_id,
    ]), "HighTideCalc: Season still ongoing")


@ pytest.mark.asyncio
async def test_closing_orders_day_1(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp2,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    #### Open orders ##############
    quantity_locked_1 = 1
    execution_price_1 = 5000

    ##########################
    ### Close orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for CLOSE orders
    quantity_locked_2 = 1
    market_id_2 = BTC_USD_ID
    oracle_price_2 = 6000

    # Create orders
    orders_2 = [{
        "quantity": 1,
        "price": 6000,
        "direction": order_direction["short"],
        "side": side["sell"],
        "order_type": order_types["limit"],

    }, {
        "quantity": 1,
        "price": 6000,
        "side": side["sell"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)
    season_id = 1
    market_id = market_id_2

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    assert days_traded.result.res == 2

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 1).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    assert trade_frequency.result.frequency == [2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_1 * execution_price_1

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["sell"])).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2 * oracle_price_2

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees) *
                         quantity_locked_1 * execution_price_1), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees) *
                         quantity_locked_1 * execution_price_1), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(
        trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_2 * oracle_price_2
    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_2 * oracle_price_2

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 1000
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 5000

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 1000
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 5000

    #### Open orders ##############
    quantity_locked_1 = 2
    execution_price_1 = 500

    ############################
    ### Close orders ETH_USD ###
    ############################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for CLOSE orders
    quantity_locked_2 = 2
    market_id_2 = ETH_USD_ID
    oracle_price_2 = 400

    # Create orders
    orders_2 = [{
        "quantity": 2,
        "price": 400,
        "market_id": ETH_USD_ID,
        "direction": order_direction["short"],
        "side": side["sell"],
        "order_type": order_types["limit"],

    }, {
        "quantity": 2,
        "price": 400,
        "market_id": ETH_USD_ID,
        "side": side["sell"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_2

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    assert days_traded.result.res == 2

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 1).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    assert trade_frequency.result.frequency == [2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_1 * execution_price_1
    print("final short volume ETH", from64x61(order_volume.result[1]))

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["sell"])).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2 * oracle_price_2
    print("final long volume ETH", from64x61(order_volume.result[1]))

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees) *
                        quantity_locked_1 * execution_price_1), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees) *
                        quantity_locked_1 * execution_price_1), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(
        trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_2 * oracle_price_2

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_2 * oracle_price_2

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 200
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 1000

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 200
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 1000

    #### Open orders ##############
    quantity_locked_1 = 4
    execution_price_1 = 50

    #############################
    ### Close orders TSLA_USD ###
    #############################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for CLOSE orders
    quantity_locked_2 = 3
    market_id_2 = TSLA_USD_ID
    oracle_price_2 = 40

    # Create orders
    orders_2 = [{
        "quantity": 3,
        "price": 40,
        "market_id": TSLA_USD_ID,
        "side": side["sell"],
        "order_type": order_types["limit"],

    }, {
        "quantity": 3,
        "price": 40,
        "market_id": TSLA_USD_ID,
        "direction": order_direction["short"],
        "side": side["sell"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_2

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    assert days_traded.result.res == 2

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 1).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    assert trade_frequency.result.frequency == [2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_1 * execution_price_1
    print("final short volume TSLA", from64x61(order_volume.result[1]))

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["sell"])).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2 * oracle_price_2
    print("final long volume TSLA", from64x61(order_volume.result[1]))

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees) *
                        quantity_locked_1 * execution_price_1), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees) *
                        quantity_locked_1 * execution_price_1), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(
        trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_2 * oracle_price_2

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_2 * oracle_price_2

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 30
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 150

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 30
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 150


@pytest.mark.asyncio
async def test_opening_orders_day_2(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

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

    #### Open orders ##############
    quantity_locked_1 = 1
    execution_price_1 = 5000

    quantity_locked_2 = 1
    execution_price_2 = 6000
    ####### Opening of Orders #######
    ##########################
    ### Open orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_3 = 1
    market_id_3 = BTC_USD_ID
    oracle_price_3 = 6500

    # Create orders
    orders_3 = [{
        "quantity": 2,
        "price": 6500,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }, {
        "quantity": 1,
        "price": 6500,
    }]

    # execute order
    (_, complete_orders, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_3, users_test=users_test, quantity_locked=quantity_locked_3, market_id=market_id_3, oracle_price=oracle_price_3, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_3

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    print(days_traded.result.res)
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 2).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    print(active_traders.result.res)
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    print(trade_frequency.result.frequency)
    assert trade_frequency.result.frequency == [2, 2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    print(order_volume.result)
    assert order_volume.result[0] == 4
    assert from64x61(order_volume.result[1]) == 2*quantity_locked_1 * \
        execution_price_1 + 2*quantity_locked_3*oracle_price_3

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["sell"])).call()
    print("real", order_volume.result)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2 * execution_price_2

    ##########################
    ### Open orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_4 = 1
    market_id_4 = BTC_USD_ID
    oracle_price_4 = 6500

    # Create orders
    orders_4 = [{
        "order_id": complete_orders[0]["order_id"]
    }, {
        "quantity": 1,
        "price": 6500,
    }]

    # execute order
    (_, complete_orders, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_4, users_test=users_test, quantity_locked=quantity_locked_4, market_id=market_id_4, oracle_price=oracle_price_4, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_4

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    print(days_traded.result.res)
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 2).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 4

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    print(active_traders.result.res)
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    print(trade_frequency.result.frequency)
    assert trade_frequency.result.frequency == [2, 2, 4]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 4

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    print(order_volume.result)
    assert order_volume.result[0] == 6
    assert from64x61(order_volume.result[1]) == 2*quantity_locked_1 * \
        execution_price_1 + 4*quantity_locked_3*oracle_price_3

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["sell"])).call()
    print("real", order_volume.result)
    #print("expected", [2, 2*to64x61(size2*execution_price2)])
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2 * \
        quantity_locked_2 * execution_price_2


@pytest.mark.asyncio
async def test_opening_closing_orders_day_3(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

    # here we test with new traders in request_list
    # we also test a batch of trades with open as well as close type orders
    charlie_balance = to64x61(50000)

    await admin1_signer.send_transaction(admin1, charlie.contract_address, 'set_balance', [AssetID.USDC, charlie_balance])
    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp4,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    # here we test with new traders in request_list
    # we also test a batch of trades with open as well as close type orders
    #### Open orders ##############
    quantity_locked_1 = 1
    execution_price_1 = 5000

    quantity_locked_2 = 1
    execution_price_2 = 6000

    quantity_locked_3 = 1
    execution_price_3 = 6500
    ##########################
    ### Open orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, charlie_test]

    # Sufficient balance for users
    charlie_balance = 100000

    # Batch params for OPEN orders
    quantity_locked_4 = 1
    market_id_4 = BTC_USD_ID
    asset_id_4 = AssetID.USDC
    oracle_price_4 = 7000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=[charlie], users_test=[charlie_test], balance_array=[charlie_balance], asset_id=asset_id_4)

    # Create orders
    orders_4 = [{
        "quantity": 1,
        "price": 7000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
        "leverage": 4
    }, {
        "quantity": 1,
        "price": 7000,
        "leverage": 2
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_4, users_test=users_test, quantity_locked=quantity_locked_4, market_id=market_id_4, oracle_price=oracle_price_4, trading=trading, is_reverted=0, error_code=0)

    ############################
    ### CLOSE orders BTC_USD ###
    ############################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_5 = 1
    market_id_5 = BTC_USD_ID
    oracle_price_5 = 7000

    # Create orders
    orders_5 = [{
        "quantity": 2,
        "price": 7000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
        "side": side["sell"]
    }, {
        "quantity": 2,
        "price": 7000,
        "side": side["sell"]
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_5, users_test=users_test, quantity_locked=quantity_locked_5, market_id=market_id_5, oracle_price=oracle_price_5, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_4

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    assert days_traded.result.res == 4

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 3).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 4

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    assert active_traders.result.res == 3

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    assert trade_frequency.result.frequency == [2, 2, 4, 4]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 4

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    print(order_volume.result)
    assert order_volume.result[0] == 8
    assert from64x61(order_volume.result[1]) == (2*quantity_locked_1*execution_price_1 + 4*quantity_locked_3*execution_price_3
                                                 + 2*quantity_locked_4*oracle_price_4)
    print("final short volume BTC", from64x61(order_volume.result[1]))

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["sell"])).call()
    print(order_volume.result)
    assert order_volume.result[0] == 4
    assert from64x61(order_volume.result[1]) == (2*quantity_locked_2*execution_price_2
                                                 + 2*quantity_locked_4*oracle_price_4)
    print("final long volume BTC", from64x61(order_volume.result[1]))


@pytest.mark.asyncio
async def test_opening_closing_orders_day_4(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

    # increment to a later date
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp5,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

   #############################
    ### Open orders TELSA_USD ###
    #############################
    # List of users
    users_test = [alice_test, charlie_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = TSLA_USD_ID
    oracle_price_1 = 30

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "market_id": TSLA_USD_ID,
        "price": 30,
        "order_type": order_types["limit"],
        "side": side["sell"]
    }, {
        "quantity": 1,
        "market_id": TSLA_USD_ID,
        "price": 30,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_1

    days_traded = await trading_stats.get_total_days_traded(season_id, market_id).call()
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, market_id, 4).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, market_id).call()
    assert active_traders.result.res == 3

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, market_id).call()
    assert trade_frequency.result.frequency == [2, 2, 0, 0, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, market_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["buy"])).call()
    assert order_volume.result[0] == 3
    assert from64x61(order_volume.result[1]) == ((2*4*50) + (1*1*30))
    print("final short volume TSLA", from64x61(order_volume.result[1]))

    order_volume = await trading_stats.get_order_volume((season_id, market_id, side["sell"])).call()
    assert order_volume.result[0] == 3
    assert from64x61(order_volume.result[1]) == ((2*3*40) + (1*1*30))
    print("final long volume TSLA", from64x61(order_volume.result[1]))

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_fee.result.fee_64x61) == 0.03879999999999986

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, charlie.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees) *
                        quantity_locked_1 * oracle_price_1), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == 0.1503499999999998

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader1_order_volume.result.number_of_orders == 2
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == (
        (3*40) + quantity_locked_1 * oracle_price_1)

    trader2_order_volume = await user_stats.get_trader_order_volume(charlie.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_1 * oracle_price_1

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 50
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 200

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, charlie.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, charlie.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0


@pytest.mark.asyncio
async def test_calculating_factors(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation, alice_test, bob_test, charlie_test, python_executor = adminAuth_factory

    season_id = 1
    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    num_trading_days = fetched_trading_season.num_trading_days

    timestamp = fetched_trading_season.start_timestamp + \
        (num_trading_days*24*60*60) + 60

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    await admin1_signer.send_transaction(admin1, hightide.contract_address, "end_trade_season", [season_id])

    markets = await hightide.get_hightides_by_season_id(1).call()
    print(markets.result)

    top_stats = await hightideCalc.find_top_stats(1).call()
    print(top_stats.result)

    ETH_factors = await hightideCalc.get_hightide_factors(1, ETH_USD_ID).call()
    ETH_parsed = list(ETH_factors.result.res)
    print(ETH_parsed)

    assert from64x61(ETH_parsed[0]) == pytest.approx(
        ((3600/4)/(76000/12)), abs=1e-6)
    assert from64x61(ETH_parsed[1]) == (2/4)
    assert from64x61(ETH_parsed[2]) == (2/5)
    assert from64x61(ETH_parsed[3]) == (2/3)

    TSLA_factors = await hightideCalc.get_hightide_factors(1, TSLA_USD_ID).call()
    TSLA_parsed = list(TSLA_factors.result.res)
    print(TSLA_parsed)

    assert from64x61(TSLA_parsed[0]) == pytest.approx(
        ((700/6)/(76000/12)), abs=1e-6)
    assert from64x61(TSLA_parsed[1]) == (2/4)
    assert from64x61(TSLA_parsed[2]) == (3/5)
    assert from64x61(TSLA_parsed[3]) == (3/3)

    # Get Xp state
    xp_state = await rewardsCalculation.get_xp_state(season_id).call()
    assert xp_state.result.state == SET_XP_NOT_STARTED

    await admin1_signer.send_transaction(admin1, rewardsCalculation.contract_address, "set_user_xp_values",
                                         [
                                             season_id,
                                             3,
                                             alice.contract_address,
                                             100,
                                             bob.contract_address,
                                             200,
                                             charlie.contract_address,
                                             300,
                                         ],
                                         )

    no_of_active_traders_info = await trading_stats.get_num_active_traders(season_id, 0).call()
    assert no_of_active_traders_info.result.res == 3

    # Get no.of batches info
    no_of_batches_info = await rewardsCalculation.get_no_of_batches_per_season(season_id).call()
    assert no_of_batches_info.result.no_of_batches == 1

    # Get Xp state
    xp_state = await rewardsCalculation.get_xp_state(season_id).call()
    assert xp_state.result.state == SET_XP_COMPLETED

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_w", [
        season_id,
        ETH_USD_ID,
    ])

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_trader_score", [
        season_id,
        ETH_USD_ID,
    ])

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_w", [
        season_id,
        TSLA_USD_ID,
    ])

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_trader_score", [
        season_id,
        TSLA_USD_ID,
    ])

    a = await rewardsCalculation.get_user_xp_value(season_id, alice.contract_address).call()
    print("alice xp value", a.result)
    b = await rewardsCalculation.get_user_xp_value(season_id, bob.contract_address).call()
    print("bob xp value", b.result)
    c = await rewardsCalculation.get_user_xp_value(season_id, charlie.contract_address).call()
    print("charlie xp value", c.result)
    d = await hightide.get_constants().call()
    print("constants value", d.result)
    e = await hightide.get_multipliers().call()
    print("multipliers value", e.result)

    # Trader score is zero for all traders becuase, BTC_USD_ID is not listed under hightide
    alice_w_BTC_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, BTC_USD_ID, alice.contract_address).call()
    assert from64x61(alice_w_BTC_USD_ID.result.trader_score) == 0
    bob_w_BTC_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, BTC_USD_ID, bob.contract_address).call()
    assert from64x61(bob_w_BTC_USD_ID.result.trader_score) == 0
    charlie_w_BTC_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, BTC_USD_ID, charlie.contract_address).call()
    assert from64x61(charlie_w_BTC_USD_ID.result.trader_score) == 0

    # Here, Trader score for charlie is zero. Becuase, he didn't trade ETH_USD_ID
    alice_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, alice.contract_address).call()
    assert from64x61(
        alice_w_ETH_USD_ID.result.trader_score) == 0.4479042456318879
    bob_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, bob.contract_address).call()
    assert from64x61(
        bob_w_ETH_USD_ID.result.trader_score) == 0.5520957543681121
    charlie_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, charlie.contract_address).call()
    assert from64x61(charlie_w_ETH_USD_ID.result.trader_score) == 0

    # Get the trader score for all traders
    alice_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, alice.contract_address).call()
    assert from64x61(
        alice_w_TSLA_USD_ID.result.trader_score) == 0.3060977266932676
    bob_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, bob.contract_address).call()
    assert from64x61(
        bob_w_TSLA_USD_ID.result.trader_score) == 0.37100273218642876
    charlie_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, charlie.contract_address).call()
    assert from64x61(
        charlie_w_TSLA_USD_ID.result.trader_score) == 0.3228995411203036

    # funds flow per market comparision
    funds_flow_BTC_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, BTC_USD_ID).call()
    assert from64x61(funds_flow_BTC_USD_ID.result.funds_flow) == 0
    funds_flow_ETH_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, ETH_USD_ID).call()
    assert from64x61(
        funds_flow_ETH_USD_ID.result.funds_flow) == 0.42719298245614035
    funds_flow_TSLA_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, TSLA_USD_ID).call()
    assert from64x61(
        funds_flow_TSLA_USD_ID.result.funds_flow) == 0.5296052631578947
