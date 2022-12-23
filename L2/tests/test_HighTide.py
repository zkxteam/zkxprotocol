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
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, print_parsed_positions, print_parsed_collaterals, assert_events_emitted, assert_event_emitted
from utils_links import DEFAULT_LINK_1, prepare_starknet_string
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from utils_trading import User, order_direction, order_types, order_time_in_force, order_life_cycles, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, check_batch_status
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
dave_signer = Signer(123456789987654326)
eduard_signer = Signer(123456789987654327)

maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")
class_hash = 0
USDC_L1_address = 123
UST_L1_address = 456
whitelisted_usdc = None
whitelisted_ust = None

initial_timestamp = int(time.time())


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def hightide_test_initializer(starknet_service: StarknetService):
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
    eduard = await account_factory.deploy_account(eduard_signer.public_key)

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

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # add user accounts to account registry
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [admin1.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [admin2.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [alice.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [bob.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [charlie.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [dave.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [eduard.contract_address])

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

    # Set the threshold for oracle price in Trading contract
    await admin1_signer.send_transaction(admin1, trading.contract_address, 'set_threshold_percentage', [to64x61(5)])
    # Deploy ERC20 contracts
    native_erc20_usdc = await starknet_service.deploy(ContractType.ERC20, [str_to_felt("USDC"), str_to_felt("USDC"), 6, 100, 0, starkway.contract_address, admin1.contract_address])
    native_erc20_ust = await starknet_service.deploy(ContractType.ERC20, [str_to_felt("UST"), str_to_felt("UST"), 18, 100, 0, starkway.contract_address, admin1.contract_address])

    # add native token l2 address
    await admin1_signer.send_transaction(admin1, starkway.contract_address, 'add_native_token_l2_address', [USDC_L1_address, native_erc20_usdc.contract_address])
    await admin1_signer.send_transaction(admin1, starkway.contract_address, 'add_native_token_l2_address', [UST_L1_address, native_erc20_ust.contract_address])

    return starknet_service, python_executor, admin1, admin2, alice, bob, charlie, dave, eduard, alice_test, bob_test, charlie_test, adminAuth, trading, hightide, hightideCalc, rewardsCalculation, native_erc20_usdc, native_erc20_ust, starkway


@pytest.mark.asyncio
async def test_set_multipliers_unauthorized_user(hightide_test_initializer):
    _, _, _, _, _, _, _, _, eduard, _, _, _, _, _, hightide, _, _, _, _, _, = hightide_test_initializer

    await assert_revert(
        eduard_signer.send_transaction(
            eduard, hightide.contract_address, 'set_multipliers', [1, 2, 3, 4]),
        reverted_with="HighTide: Unauthorized call to set multipliers"
    )


@pytest.mark.asyncio
async def test_set_multipliers_authorized_admin(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    set_multipliers_tx = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'set_multipliers', [
        1, 2, 3, 4])

    assert_event_emitted(
        set_multipliers_tx,
        from_address=hightide.contract_address,
        name="multipliers_for_rewards_added",
        data=[
            admin1.contract_address, 1, 2, 3, 4
        ]
    )

    execution_info = await hightide.get_multipliers().call()
    fetched_multipliers = execution_info.result.multipliers

    assert fetched_multipliers.a_1 == 1
    assert fetched_multipliers.a_2 == 2
    assert fetched_multipliers.a_3 == 3
    assert fetched_multipliers.a_4 == 4


@pytest.mark.asyncio
async def test_set_constants_unauthorized_user(hightide_test_initializer):
    _, _, _, _, _, _, _, _, eduard, _, _, _, _, _, hightide, _, _, _, _, _, = hightide_test_initializer

    await assert_revert(
        eduard_signer.send_transaction(
            eduard, hightide.contract_address, 'set_constants', [1, 2, 3, 4, 5]),
        reverted_with="HighTide: Unauthorized call to set constants"
    )


@pytest.mark.asyncio
async def test_set_constants_authorized_admin(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    set_constants_tx = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'set_constants', [
        1, 2, 3, 4, 5])

    assert_event_emitted(
        set_constants_tx,
        from_address=hightide.contract_address,
        name="constants_for_trader_score_added",
        data=[
            admin1.contract_address, 1, 2, 3, 4, 5
        ]
    )

    execution_info = await hightide.get_constants().call()
    fetched_constants = execution_info.result.constants

    assert fetched_constants.a == 1
    assert fetched_constants.b == 2
    assert fetched_constants.c == 3
    assert fetched_constants.z == 4
    assert fetched_constants.e == 5


@pytest.mark.asyncio
async def test_setup_trading_season_unauthorized_user(hightide_test_initializer):
    _, _, _, _, _, _, _, _, eduard, _, _, _, _, _, hightide, _, _, _, _, _, = hightide_test_initializer

    await assert_revert(
        eduard_signer.send_transaction(
            eduard, hightide.contract_address, 'setup_trade_season', [initial_timestamp, 30]),
        "HighTide: Unauthorized call to setup trade season"
    )


@pytest.mark.asyncio
async def test_setup_trading_season_authorized_admin(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    trade_season_setup_tx = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, 30])

    assert_event_emitted(
        trade_season_setup_tx,
        from_address=hightide.contract_address,
        name="trading_season_set_up",
        data=[
            admin1.contract_address,
            0,
            initial_timestamp,
            30
        ]
    )

    execution_info = await hightide.get_season(1).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == initial_timestamp
    assert fetched_trading_season.num_trading_days == 30


@pytest.mark.asyncio
async def test_start_trade_season_unauthorized_user(hightide_test_initializer):
    _, _, _, _, _, _, _, _, eduard, _, _, _, _, _, hightide, _, _, _, _, _, = hightide_test_initializer

    await assert_revert(
        eduard_signer.send_transaction(
            eduard, hightide.contract_address, 'start_trade_season', [1]),
        reverted_with="HighTide: Unauthorized call to start trade season"
    )


@pytest.mark.asyncio
async def test_start_trade_season_authorized_admin(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer
    start_trade_season_tx = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [1])

    assert_event_emitted(
        start_trade_season_tx,
        from_address=hightide.contract_address,
        name="trading_season_started",
        data=[
            admin1.contract_address, 1
        ]
    )

    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 1


# end trade season before it gets expired
@pytest.mark.asyncio
async def test_end_trade_season_before_expiry(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    await assert_revert(
        admin1_signer.send_transaction(
            admin1,
            hightide.contract_address,
            "end_trade_season",
            [1],
        ),
        "HighTide: Trading season is still active"
    )


# end trade season after it gets expired
@pytest.mark.asyncio
async def test_end_trade_season_after_expiry(hightide_test_initializer):
    starknet_service, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer
    execution_info = await hightide.get_season(1).call()
    fetched_trading_season = execution_info.result.trading_season

    num_trading_days = fetched_trading_season.num_trading_days

    timestamp = fetched_trading_season.start_timestamp + \
        (num_trading_days*24*60*60) + 1

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    execution_info = await admin1_signer.send_transaction(admin1, hightide.contract_address,
                                                          "end_trade_season", [1])

    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 0


@pytest.mark.asyncio
async def test_get_season_with_invalid_season_id(hightide_test_initializer):
    _, _, _, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    await assert_revert(hightide.get_season(2).call(), reverted_with="HighTide: Trading season id existence mismatch")


@pytest.mark.asyncio
async def test_initialize_hightide_for_expired_trading_season(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer
    await assert_revert(admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide',
                                                       [BTC_USD_ID, 1, admin1.contract_address, 1, 2, USDC_L1_address, 1000, 0, UST_L1_address, 500, 0]),
                        "HighTide: Trading season already ended")


@pytest.mark.asyncio
async def test_initialize_hightide_with_zero_class_hash(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer
    await assert_revert(admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide',
                                                       [BTC_USD_ID, 1, admin1.contract_address, 1, 2, USDC_L1_address, 1000, 0, UST_L1_address, 500, 0]))


@pytest.mark.asyncio
async def test_initialize_hightide(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    # 1. Setup and start new season
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, 40])
    season_id = 2
    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == initial_timestamp
    assert fetched_trading_season.num_trading_days == 40

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [season_id])
    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id
    assert season_id == 2

    # 2. Set Liquidity pool contract class hash
    tx_exec_info = await admin1_signer.send_transaction(admin1,
                                                        hightide.contract_address,
                                                        'set_liquidity_pool_contract_class_hash',
                                                        [class_hash])

    assert_event_emitted(
        tx_exec_info,
        from_address=hightide.contract_address,
        name='liquidity_pool_contract_class_hash_changed',
        data=[
            class_hash
        ]
    )

    # 3. Initialize hightide
    tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide',
                                                        [BTC_USD_ID, season_id, admin1.contract_address, 1, 2, USDC_L1_address, 1000, 0, UST_L1_address, 500, 0])
    hightide_id = 1
    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    assert_events_emitted(
        tx_exec_info,
        [
            [0, hightide.contract_address, 'liquidity_pool_contract_deployed',
                [hightide_id, liquidity_pool_address]],
            [1, hightide.contract_address, 'hightide_initialized',
                [admin1.contract_address, hightide_id]],
        ]
    )

    fetched_rewards = await hightide.get_hightide_reward_tokens(hightide_id).call()
    assert fetched_rewards.result.reward_tokens_list[0].token_id == USDC_L1_address
    assert fetched_rewards.result.reward_tokens_list[0].no_of_tokens == (
        1000, 0)
    assert fetched_rewards.result.reward_tokens_list[1].token_id == UST_L1_address
    assert fetched_rewards.result.reward_tokens_list[1].no_of_tokens == (
        500, 0)


# activating hightide will fail as there are no funds in liquidity pool contract
@pytest.mark.asyncio
async def test_activate_hightide_with_zero_fund_transfer(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    hightide_id = 1
    await assert_revert(
        admin1_signer.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Liquidity pool should be fully funded"
    )


# Hightide activation fails becuase of insufficient native tokens
@pytest.mark.asyncio
async def test_activate_hightide_with_insufficient_native_tokens(hightide_test_initializer):
    starknet_service, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, native_erc20_usdc, native_erc20_ust, _ = hightide_test_initializer

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id
    hightide_id = 1

    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    # 1. Fund liquidity pool with insufficient no. of native tokens
    await admin1_signer.send_transaction(admin1, native_erc20_usdc.contract_address,
                                         'mint', [liquidity_pool_address, 500, 0],)

    await admin1_signer.send_transaction(admin1, native_erc20_ust.contract_address,
                                         'mint', [liquidity_pool_address, 500, 0],)

    # 2. Activate Hightide
    await assert_revert(
        admin1_signer.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Liquidity pool should be fully funded"
    )


# Hightide activation with sufficient native tokens
@pytest.mark.asyncio
async def test_activate_hightide_with_sufficient_native_tokens(hightide_test_initializer):
    starknet_service, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, native_erc20_usdc, _, _ = hightide_test_initializer

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id
    hightide_id = 1

    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    # 1. Fund liquidity pool with sufficient native tokens
    await admin1_signer.send_transaction(admin1, native_erc20_usdc.contract_address,
                                         'mint', [liquidity_pool_address, 500, 0],)

    # 2. Activate Hightide
    tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address,
                                                        "activate_high_tide", [hightide_id])

    assert_events_emitted(
        tx_exec_info,
        [
            [0, hightide.contract_address, 'hightide_activated',
                [admin1.contract_address, hightide_id]],
            [1, hightide.contract_address,
                'assigned_hightide_to_season', [hightide_id, season_id]],
        ]
    )

    execution_info = await hightide.get_hightides_by_season_id(season_id).call()
    hightide_list = execution_info.result.hightide_list
    assert hightide_list[0] == hightide_id


# Hightide activation fails becuase, hightide is already activated
@pytest.mark.asyncio
async def test_activate_hightide_which_is_already_activated(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer
    hightide_id = 1
    await assert_revert(
        admin1_signer.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Hightide is already activated"
    )


# Hightide activation fails becuase, trading season is already expired
@pytest.mark.asyncio
async def test_activate_hightide_for_expired_trading_season(hightide_test_initializer):
    starknet_service, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, native_erc20_usdc, native_erc20_ust, _ = hightide_test_initializer

    season_id = 2
    # 1. Initialize Hightide
    tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide',
                                                        [BTC_USD_ID, season_id, admin1.contract_address, 1, 2, USDC_L1_address, 2000, 0, UST_L1_address, 2000, 0])
    hightide_id = 2
    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    # 2. Fund Liquidity pool with sufficient native tokens
    await admin1_signer.send_transaction(admin1, native_erc20_usdc.contract_address,
                                         'mint', [liquidity_pool_address, 2000, 0],)

    await admin1_signer.send_transaction(admin1, native_erc20_ust.contract_address,
                                         'mint', [liquidity_pool_address, 2000, 0],)

    # 3. End trading season
    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season
    num_trading_days = fetched_trading_season.num_trading_days
    timestamp = fetched_trading_season.start_timestamp + \
        (num_trading_days*24*60*60) + 1

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )
    await admin1_signer.send_transaction(admin1, hightide.contract_address,
                                         "end_trade_season", [season_id])

    # 4. Activate Hightide
    await assert_revert(
        admin1_signer.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Trading season already ended"
    )


# activating hightide by funding both native and non native tokens
@pytest.mark.asyncio
async def test_activate_hightide_with_native_and_non_native_tokens(hightide_test_initializer):
    starknet_service, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, native_erc20_usdc, native_erc20_ust, starkway = hightide_test_initializer

    execution_info = await hightide.get_season(2).call()
    fetched_trading_season = execution_info.result.trading_season

    num_trading_days = fetched_trading_season.num_trading_days

    timestamp = fetched_trading_season.start_timestamp + \
        (num_trading_days*24*60*60) + 1

    #  1. Setup and start new season
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        timestamp, 5])
    season_id = 3
    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [season_id])
    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id
    assert season_id == 3

    # 2. Initialize Hightide
    tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide',
                                                        [ETH_USD_ID, season_id, admin1.contract_address, 1, 2, USDC_L1_address, 3000, 0, UST_L1_address, 5000, 0])
    hightide_id = 3
    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    # 3. Deploy non native token contracts and whitelist the addresses
    global whitelisted_usdc
    global whitelisted_ust
    whitelisted_usdc = await starknet_service.deploy(ContractType.ERC20,
                                                     [str_to_felt("USDC"), str_to_felt("USDC"), 6, 100, 0, starkway.contract_address, admin1.contract_address])
    whitelisted_ust = await starknet_service.deploy(ContractType.ERC20,
                                                    [str_to_felt("UST"), str_to_felt("UST"), 18, 200, 0, starkway.contract_address, admin1.contract_address])

    await admin1_signer.send_transaction(admin1, starkway.contract_address,
                                         'whitelist_token_address', [USDC_L1_address, whitelisted_usdc.contract_address],)

    await admin1_signer.send_transaction(admin1, starkway.contract_address,
                                         'whitelist_token_address', [UST_L1_address, whitelisted_ust.contract_address],)

    # 4. Fund liquidity pool with both native and non native tokens
    await admin1_signer.send_transaction(admin1, whitelisted_usdc.contract_address,
                                         'mint', [liquidity_pool_address, 2000, 0],)

    await admin1_signer.send_transaction(admin1, whitelisted_ust.contract_address,
                                         'mint', [liquidity_pool_address, 4500, 0],)

    await admin1_signer.send_transaction(admin1, native_erc20_usdc.contract_address,
                                         'mint', [liquidity_pool_address, 1000, 0],)

    await admin1_signer.send_transaction(admin1, native_erc20_ust.contract_address,
                                         'mint', [liquidity_pool_address, 500, 0],)

    # 5. Activate Hightide
    tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address,
                                                        "activate_high_tide", [hightide_id])

    assert_events_emitted(
        tx_exec_info,
        [
            [0, hightide.contract_address, 'hightide_activated',
                [admin1.contract_address, hightide_id]],
            [1, hightide.contract_address,
                'assigned_hightide_to_season', [hightide_id, season_id]],
        ]
    )

    execution_info = await hightide.get_hightides_by_season_id(season_id).call()
    hightide_list = execution_info.result.hightide_list
    assert hightide_list[0] == hightide_id


# Hightide activation fails becuase of insufficient native tokens
@pytest.mark.asyncio
async def test_activate_hightide_with_insufficient_non_native_tokens(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer

    season_id = 3
    # 1. Initialize Hightide
    tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide',
                                                        [TSLA_USD_ID, season_id, admin1.contract_address, 1, 2, USDC_L1_address, 1000, 0, UST_L1_address, 2000, 0])
    hightide_id = 4
    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    # 2. Fund liquidity pool with non native tokens. But, no of tokens should be insufficient to activate hightide
    await admin1_signer.send_transaction(admin1, whitelisted_usdc.contract_address,
                                         'mint', [liquidity_pool_address, 1000, 0],)

    await admin1_signer.send_transaction(admin1, whitelisted_ust.contract_address,
                                         'mint', [liquidity_pool_address, 1000, 0],)

    # 3. Activate Hightide
    await assert_revert(
        admin1_signer.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Liquidity pool should be fully funded"
    )


# Hightide activation with sufficient non native tokens
@pytest.mark.asyncio
async def test_activate_hightide_with_sufficient_non_native_tokens(hightide_test_initializer):
    _, _, admin1, _, _, _, _, _, _, _, _, _, _, _, hightide, _, _, _, _, _ = hightide_test_initializer
    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id
    hightide_id = 4

    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    # 1. Fund liquidity pool with sufficient non native tokens
    await admin1_signer.send_transaction(admin1, whitelisted_ust.contract_address,
                                         'mint', [liquidity_pool_address, 1000, 0],)

    # 2. Activate Hightide
    tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address,
                                                        "activate_high_tide", [hightide_id])

    assert_events_emitted(
        tx_exec_info,
        [
            [0, hightide.contract_address, 'hightide_activated',
                [admin1.contract_address, hightide_id]],
            [1, hightide.contract_address,
                'assigned_hightide_to_season', [hightide_id, season_id]],
        ]
    )

    execution_info = await hightide.get_hightides_by_season_id(season_id).call()
    hightide_list = execution_info.result.hightide_list
    assert hightide_list[0] == hightide_id - 1
    assert hightide_list[1] == hightide_id


@pytest.mark.asyncio
async def test_placing_orders_day_0(hightide_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, alice_test, bob_test, _, _, trading, _, _, _, _, _, _ = hightide_test_initializer

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


@pytest.mark.asyncio
async def test_closing_orders_day_1(hightide_test_initializer):
    starknet_service, python_executor, admin1, _, alice, bob, _, dave, _, alice_test, bob_test, _, _, trading, hightide, _, _, _, _, _ = hightide_test_initializer

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id

    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    timestamp = fetched_trading_season.start_timestamp + (60*60*24) + 60

    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )
    ##########################
    ### Close orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for CLOSE orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    oracle_price_1 = 6000

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 6000,
        "life_cycle": order_life_cycles["close"],
        "order_type": order_types["limit"],

    }, {
        "quantity": 1,
        "price": 6000,
        "life_cycle": order_life_cycles["close"],
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

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
        "life_cycle": order_life_cycles["close"],
        "order_type": order_types["limit"],

    }, {
        "quantity": 2,
        "price": 400,
        "market_id": ETH_USD_ID,
        "life_cycle": order_life_cycles["close"],
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)

    #############################
    ### Close orders TSLA_USD ###
    #############################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for CLOSE orders
    quantity_locked_3 = 3
    market_id_3 = TSLA_USD_ID
    oracle_price_3 = 40

    # Create orders
    orders_3 = [{
        "quantity": 3,
        "price": 40,
        "market_id": TSLA_USD_ID,
        "life_cycle": order_life_cycles["close"],
        "order_type": order_types["limit"],
        "direction": order_direction["short"],

    }, {
        "quantity": 3,
        "price": 40,
        "market_id": TSLA_USD_ID,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_3, users_test=users_test, quantity_locked=quantity_locked_3, market_id=market_id_3, oracle_price=oracle_price_3, trading=trading, is_reverted=0, error_code=0)


@pytest.mark.asyncio
async def test_opening_orders_day_2(hightide_test_initializer):
    starknet_service, python_executor, admin1, _, alice, bob, _, dave, _, alice_test, bob_test, _, _, trading, hightide, _, _, _, _, _ = hightide_test_initializer

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id

    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    timestamp = fetched_trading_season.start_timestamp + (60*60*24)*2 + 60

    # here we check the scenario that there are multiple calls to record_trade_batch_stats in a single day
    # we also check that recording is handled properly when orders are executed partially
    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ##########################
    ### Open orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 6500

    # Create orders
    orders_1 = [{
        "quantity": 2,
        "price": 6500,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
    }, {
        "quantity": 1,
        "price": 6500,
    }]

    # execute order
    (_, complete_orders) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    ##########################
    ### Open orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_2 = 1
    market_id_2 = BTC_USD_ID
    asset_id_2 = AssetID.USDC
    oracle_price_2 = 6500

    # Create orders
    orders_2 = [{
        "order_id": complete_orders[0]["order_id"]
    }, {
        "quantity": 1,
        "price": 6500,
    }]

    # execute order
    (_, complete_orders) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)


@pytest.mark.asyncio
async def test_opening_closing_orders_day_3(hightide_test_initializer):
    starknet_service, python_executor, admin1, _, alice, bob, charlie, dave, _, alice_test, bob_test, charlie_test, _, trading, hightide, _, _, _, _, _ = hightide_test_initializer

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id

    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    timestamp = fetched_trading_season.start_timestamp + (60*60*24)*3 + 60

    # here we test with new traders in request_list
    # we also test a batch of trades with open as well as close type orders
    charlie_balance = to64x61(50000)

    await admin1_signer.send_transaction(admin1, charlie.contract_address, 'set_balance', [AssetID.USDC, charlie_balance])
    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ##########################
    ### Open orders BTC_USD ##
    ##########################
    # List of users
    users_test = [alice_test, charlie_test]

    # Sufficient balance for users
    charlie_balance = 100000

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 7000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=[charlie], users_test=[charlie_test], balance_array=[charlie_balance], asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
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
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    ############################
    ### CLOSE orders BTC_USD ###
    ############################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_2 = 2
    market_id_2 = BTC_USD_ID
    oracle_price_2 = 7000

    # Create orders
    orders_2 = [{
        "quantity": 2,
        "price": 7000,
        "order_type": order_types["limit"],
        "life_cycle": order_life_cycles["close"]
    }, {
        "quantity": 2,
        "price": 7000,
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)


@pytest.mark.asyncio
async def test_opening_closing_orders_day_4(hightide_test_initializer):
    starknet_service, python_executor, admin1, _, alice, bob, charlie, dave, _, alice_test, bob_test, charlie_test, _, trading, hightide, _, _, _, _, _ = hightide_test_initializer

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id

    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    timestamp = fetched_trading_season.start_timestamp + (60*60*24)*4 + 60

    # increment to a later date
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )
    #############################
    ### Open orders TELSA_USD ###
    #############################
    # List of users
    users_test = [alice_test, bob_test]

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
        "direction": order_direction["short"],
        "life_cycle": order_life_cycles["close"]
    }, {
        "quantity": 1,
        "market_id": TSLA_USD_ID,
        "price": 30,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)


@pytest.mark.asyncio
async def test_calculating_factors(hightide_test_initializer):
    starknet_service, _, admin1, _, alice, bob, charlie, dave, _, _, _, _, _, _, hightide, hightideCalc, rewardsCalculation, _, _, _ = hightide_test_initializer

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id

    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    num_trading_days = fetched_trading_season.num_trading_days

    timestamp = fetched_trading_season.start_timestamp + \
        (num_trading_days*24*60*60) + 1

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    await admin1_signer.send_transaction(admin1, hightide.contract_address, "end_trade_season", [season_id])

    markets = await hightide.get_hightides_by_season_id(season_id).call()
    print(markets.result)

    top_stats = await hightideCalc.find_top_stats(season_id).call()
    print(top_stats.result)

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

    set_factors_tx = await dave_signer.send_transaction(dave, hightideCalc.contract_address, "calculate_high_tide_factors", [
        season_id,
    ])

    ETH_factors = await hightideCalc.get_hightide_factors(season_id, ETH_USD_ID).call()
    ETH_parsed = list(ETH_factors.result.res)
    print(ETH_parsed)

    assert from64x61(ETH_parsed[0]) == pytest.approx(
        ((3600/4)/(76000/12)), abs=1e-6)
    assert from64x61(ETH_parsed[1]) == (2/4)
    assert from64x61(ETH_parsed[2]) == (2/5)
    assert from64x61(ETH_parsed[3]) == (2/3)

    TSLA_factors = await hightideCalc.get_hightide_factors(season_id, TSLA_USD_ID).call()
    TSLA_parsed = list(TSLA_factors.result.res)
    print(TSLA_parsed)

    assert from64x61(TSLA_parsed[0]) == pytest.approx(
        ((700/6)/(76000/12)), abs=1e-6)
    assert from64x61(TSLA_parsed[1]) == (2/4)
    assert from64x61(TSLA_parsed[2]) == (3/5)
    assert from64x61(TSLA_parsed[3]) == (3/3)

    assert_events_emitted(
        set_factors_tx,
        [
            [0, hightideCalc.contract_address, "high_tide_factors_set",
                [season_id, ETH_USD_ID] + ETH_parsed],
            [1, hightideCalc.contract_address, "high_tide_factors_set",
                [season_id, TSLA_USD_ID] + TSLA_parsed]
        ]
    )

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

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_funds_flow", [
        season_id
    ])

    # funds flow per market comparision
    funds_flow_BTC_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, BTC_USD_ID).call()
    assert from64x61(funds_flow_BTC_USD_ID.result.funds_flow) == 0
    funds_flow_ETH_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, ETH_USD_ID).call()
    assert from64x61(
        funds_flow_ETH_USD_ID.result.funds_flow) == 0.42719298245614035
    funds_flow_TSLA_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, TSLA_USD_ID).call()
    assert from64x61(
        funds_flow_TSLA_USD_ID.result.funds_flow) == 0.5296052631578947

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_w", [
        season_id,
        ETH_USD_ID,
        2,
        alice.contract_address,
        bob.contract_address,
    ])

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_trader_score", [
        season_id,
        ETH_USD_ID,
        2,
        alice.contract_address,
        bob.contract_address,
    ])

    # Here, Trader score for charlie is zero. Becuase, he didn't trade ETH_USD_ID
    alice_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, alice.contract_address).call()
    assert from64x61(
        alice_w_ETH_USD_ID.result.trader_score) == 0.4479042456318879
    bob_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, bob.contract_address).call()
    assert from64x61(
        bob_w_ETH_USD_ID.result.trader_score) == 0.5520957543681121
    charlie_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, charlie.contract_address).call()
    assert from64x61(charlie_w_ETH_USD_ID.result.trader_score) == 0

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_w", [
        season_id,
        TSLA_USD_ID,
        3,
        alice.contract_address,
        bob.contract_address,
        charlie.contract_address,
    ])

    await admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_trader_score", [
        season_id,
        TSLA_USD_ID,
        3,
        alice.contract_address,
        bob.contract_address,
        charlie.contract_address,
    ])

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

# # @pytest.mark.asyncio
# # async def test_distribute_rewards(adminAuth_factory):
# #     adminAuth, admin1, admin2, eduard, alice, bob, charlie, dave, native_erc20_usdc, native_erc20_ust, starkway, starknet_service, trading, hightide, hightideCalc, rewardsCalculation = adminAuth_factory

# #     season_id = 3
# #     execution_info = await hightide.get_hightides_by_season_id(season_id).call()
# #     hightide_list = execution_info.result.hightide_list

# #     # 1. Get 1st hightide metadata
# #     ETH_execution_info = await hightide.get_hightide(hightide_list[0]).call()
# #     liquidity_pool_address = ETH_execution_info.result.hightide_metadata.liquidity_pool_address

# #     # a. Get witelisted USDC balance
# #     whitelisted_usdc_balance = await whitelisted_usdc.balanceOf(liquidity_pool_address).call()
# #     # b. Get witelisted UST balance
# #     whitelisted_ust_balance = await whitelisted_ust.balanceOf(liquidity_pool_address).call()
# #     # c. Get native USDC balance
# #     native_usdc_balance = await native_erc20_usdc.balanceOf(liquidity_pool_address).call()
# #     # d. Get native UST balance
# #     native_ust_balance = await native_erc20_ust.balanceOf(liquidity_pool_address).call()

# #     # 2. Distribute rewards for ETH_USDC hightide
# #     tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address,"distribute_rewards",[
# #         hightide_list[0],
# #         2,
# #         alice.contract_address,
# #         bob.contract_address,
# #     ])

# #     # Get R value of ETH_USD market
# #     funds_flow_ETH_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, ETH_USD_ID).call()
# #     assert from64x61(funds_flow_ETH_USD_ID.result.funds_flow) == 0.42719298245614035

# #     # Get token rewards for ETH_USD market
# #     fetched_rewards = await hightide.get_hightide_reward_tokens(hightide_list[0]).call()

# #     # a. Get Alice native and non native USDC and UST balance's for ETH
# #     alice_eth_whitelisted_usdc_balance = await whitelisted_usdc.balanceOf(alice.contract_address).call()
# #     alice_eth_whitelisted_ust_balance = await whitelisted_ust.balanceOf(alice.contract_address).call()
# #     alice_eth_native_usdc_balance = await native_erc20_usdc.balanceOf(alice.contract_address).call()
# #     alice_eth_native_ust_balance = await native_erc20_ust.balanceOf(alice.contract_address).call()

# #     # Get w value of ETH_USD market
# #     alice_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, alice.contract_address).call()
# #     assert from64x61(alice_w_ETH_USD_ID.result.trader_score) == 0.4479042456318879

# #     # Check Alice's balance after reward distribution
# #     alice_usdc_reward_for_ETH_USDC_pair = (from64x61(funds_flow_ETH_USD_ID.result.funds_flow) *
# #                                             from64x61(alice_w_ETH_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[0].no_of_tokens.low)

# #     alice_ust_reward_for_ETH_USDC_pair = (from64x61(funds_flow_ETH_USD_ID.result.funds_flow) *
# #                                             from64x61(alice_w_ETH_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[1].no_of_tokens.low)

# #     alice_usdc_balance = ( alice_eth_whitelisted_usdc_balance.result.balance.low +
# #                         alice_eth_native_usdc_balance.result.balance.low)

# #     assert alice_usdc_balance == int(alice_usdc_reward_for_ETH_USDC_pair)

# #     alice_ust_balance = ( alice_eth_whitelisted_ust_balance.result.balance.low +
# #                         alice_eth_native_ust_balance.result.balance.low)

# #     assert alice_ust_balance == int(alice_ust_reward_for_ETH_USDC_pair)

# #     # b. Get bob native and non native USDC and UST balance's for ETH
# #     bob_eth_whitelisted_usdc_balance = await whitelisted_usdc.balanceOf(bob.contract_address).call()
# #     bob_eth_whitelisted_ust_balance = await whitelisted_ust.balanceOf(bob.contract_address).call()
# #     bob_eth_native_usdc_balance = await native_erc20_usdc.balanceOf(bob.contract_address).call()
# #     bob_eth_native_ust_balance = await native_erc20_ust.balanceOf(bob.contract_address).call()

# #     # Get w value of ETH_USD market
# #     bob_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, bob.contract_address).call()
# #     assert from64x61(bob_w_ETH_USD_ID.result.trader_score) == 0.5520957543681121

# #     # Check bob's balance after reward distribution
# #     bob_usdc_reward_for_ETH_USDC_pair = (from64x61(funds_flow_ETH_USD_ID.result.funds_flow) *
# #                                             from64x61(bob_w_ETH_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[0].no_of_tokens.low)

# #     bob_ust_reward_for_ETH_USDC_pair = (from64x61(funds_flow_ETH_USD_ID.result.funds_flow) *
# #                                             from64x61(bob_w_ETH_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[1].no_of_tokens.low)

# #     bob_usdc_balance = ( bob_eth_whitelisted_usdc_balance.result.balance.low +
# #                         bob_eth_native_usdc_balance.result.balance.low)

# #     assert bob_usdc_balance == int(bob_usdc_reward_for_ETH_USDC_pair)

# #     bob_ust_balance = ( bob_eth_whitelisted_ust_balance.result.balance.low +
# #                         bob_eth_native_ust_balance.result.balance.low)

# #     assert bob_ust_balance == int(bob_ust_reward_for_ETH_USDC_pair)

# #     # 1. Get 2nd hightide metadata
# #     TSLA_execution_info = await hightide.get_hightide(hightide_list[1]).call()
# #     liquidity_pool_address = TSLA_execution_info.result.hightide_metadata.liquidity_pool_address

# #     # a. Get witelisted USDC balance
# #     whitelisted_usdc_balance = await whitelisted_usdc.balanceOf(liquidity_pool_address).call()
# #     # b. Get witelisted UST balance
# #     whitelisted_ust_balance = await whitelisted_ust.balanceOf(liquidity_pool_address).call()
# #     # c. Get native USDC balance
# #     native_usdc_balance = await native_erc20_usdc.balanceOf(liquidity_pool_address).call()
# #     # d. Get native UST balance
# #     native_ust_balance = await native_erc20_ust.balanceOf(liquidity_pool_address).call()

# #     # 2. Distribute rewards for TSLA_USDC hightide
# #     tx_exec_info = await admin1_signer.send_transaction(admin1, hightide.contract_address, "distribute_rewards", [
# #         hightide_list[1],
# #         3,
# #         alice.contract_address,
# #         bob.contract_address,
# #         charlie.contract_address,
# #     ])

# #     # Get R value of TSLA_USD market
# #     funds_flow_TSLA_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, TSLA_USD_ID).call()
# #     assert from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) == 0.5296052631578947

# #     # Get token rewards for TSLA_USD market
# #     fetched_rewards = await hightide.get_hightide_reward_tokens(hightide_list[1]).call()

# #     # a. Get Alice native and non native USDC and UST balance's for TSLA
# #     alice_tsla_whitelisted_usdc_balance = await whitelisted_usdc.balanceOf(alice.contract_address).call()
# #     alice_tsla_whitelisted_ust_balance = await whitelisted_ust.balanceOf(alice.contract_address).call()
# #     alice_tsla_native_usdc_balance = await native_erc20_usdc.balanceOf(alice.contract_address).call()
# #     alice_tsla_native_ust_balance = await native_erc20_ust.balanceOf(alice.contract_address).call()

# #     # Get w value of TSLA_USD_ID market
# #     alice_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, alice.contract_address).call()
# #     assert from64x61(alice_w_TSLA_USD_ID.result.trader_score) == 0.3060977266932676

# #     # Check Alice's balance after reward distribution
# #     alice_usdc_reward_for_TSLA_USDC_pair = (from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) *
# #                                             from64x61(alice_w_TSLA_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[0].no_of_tokens.low)

# #     alice_ust_reward_for_TSLA_USDC_pair = (from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) *
# #                                             from64x61(alice_w_TSLA_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[1].no_of_tokens.low)

# #     alice_usdc_balance = ( alice_tsla_whitelisted_usdc_balance.result.balance.low +
# #                         alice_tsla_native_usdc_balance.result.balance.low)

# #     assert alice_usdc_balance == int(alice_usdc_reward_for_TSLA_USDC_pair) + int(alice_usdc_reward_for_ETH_USDC_pair)

# #     alice_ust_balance = ( alice_tsla_whitelisted_ust_balance.result.balance.low +
# #                         alice_tsla_native_ust_balance.result.balance.low)

# #     assert alice_ust_balance == int(alice_ust_reward_for_TSLA_USDC_pair) + int(alice_ust_reward_for_ETH_USDC_pair)

# #     # b. Get bob native and non native USDC and UST balance's for TSLA
# #     bob_tsla_whitelisted_usdc_balance = await whitelisted_usdc.balanceOf(bob.contract_address).call()
# #     bob_tsla_whitelisted_ust_balance = await whitelisted_ust.balanceOf(bob.contract_address).call()
# #     bob_tsla_native_usdc_balance = await native_erc20_usdc.balanceOf(bob.contract_address).call()
# #     bob_tsla_native_ust_balance = await native_erc20_ust.balanceOf(bob.contract_address).call()

# #     # Get w value of TSLA_USD_ID market
# #     bob_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, bob.contract_address).call()
# #     assert from64x61(bob_w_TSLA_USD_ID.result.trader_score) == 0.37100273218642876

# #     # Check bob's balance after reward distribution
# #     bob_usdc_reward_for_TSLA_USDC_pair = (from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) *
# #                                             from64x61(bob_w_TSLA_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[0].no_of_tokens.low)

# #     bob_ust_reward_for_TSLA_USDC_pair = (from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) *
# #                                             from64x61(bob_w_TSLA_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[1].no_of_tokens.low)

# #     bob_usdc_balance = ( bob_tsla_whitelisted_usdc_balance.result.balance.low +
# #                         bob_tsla_native_usdc_balance.result.balance.low)

# #     assert bob_usdc_balance == int(bob_usdc_reward_for_TSLA_USDC_pair) + int(bob_usdc_reward_for_ETH_USDC_pair)

# #     bob_ust_balance = ( bob_tsla_whitelisted_ust_balance.result.balance.low +
# #                         bob_tsla_native_ust_balance.result.balance.low)

# #     assert bob_ust_balance == int(bob_ust_reward_for_TSLA_USDC_pair) + int(bob_ust_reward_for_ETH_USDC_pair)

# #     # c. Get charlie native and non native USDC and UST balance's for TSLA
# #     charlie_tsla_whitelisted_usdc_balance = await whitelisted_usdc.balanceOf(charlie.contract_address).call()
# #     charlie_tsla_whitelisted_ust_balance = await whitelisted_ust.balanceOf(charlie.contract_address).call()
# #     charlie_tsla_native_usdc_balance = await native_erc20_usdc.balanceOf(charlie.contract_address).call()
# #     charlie_tsla_native_ust_balance = await native_erc20_ust.balanceOf(charlie.contract_address).call()

# #     # Get w value of TSLA_USD_ID market
# #     charlie_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, charlie.contract_address).call()
# #     assert from64x61(charlie_w_TSLA_USD_ID.result.trader_score) == 0.3228995411203036

# #     # Check charlie's balance after reward distribution
# #     charlie_usdc_reward_for_TSLA_USDC_pair = (from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) *
# #                                             from64x61(charlie_w_TSLA_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[0].no_of_tokens.low)

# #     charlie_ust_reward_for_TSLA_USDC_pair = (from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) *
# #                                             from64x61(charlie_w_TSLA_USD_ID.result.trader_score) *
# #                                             fetched_rewards.result.reward_tokens_list[1].no_of_tokens.low)

# #     charlie_usdc_balance = ( charlie_tsla_whitelisted_usdc_balance.result.balance.low +
# #                         charlie_tsla_native_usdc_balance.result.balance.low)

# #     assert charlie_usdc_balance == int(charlie_usdc_reward_for_TSLA_USDC_pair)

# #     charlie_ust_balance = ( charlie_tsla_whitelisted_ust_balance.result.balance.low +
# #                         charlie_tsla_native_ust_balance.result.balance.low)

# #     assert charlie_ust_balance == int(charlie_ust_reward_for_TSLA_USDC_pair)
