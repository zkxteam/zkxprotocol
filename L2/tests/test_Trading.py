from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, str_to_felt, to64x61
from utils_trading import User, order_direction, order_types, order_time_in_force, order_side, close_order, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions
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
eduard_signer = Signer(123456789987654327)


maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")


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
    print(alice.contract_address)

    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    bob_test = User(123456789987654324, bob.contract_address)
    print(bob.contract_address)

    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)
    charlie_test = User(123456789987654325, charlie.contract_address)

    dave = await account_factory.deploy_account(dave_signer.public_key)

    eduard = await account_factory.deploy_ZKX_account(eduard_signer.public_key)
    eduard_test = User(123456789987654327, eduard.contract_address)

    timestamp = int(time.time())
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=timestamp,
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
    # liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
    collateral_prices = await starknet_service.deploy(
        ContractType.CollateralPrices,
        [registry.contract_address, 1]
    )
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
    user_stats = await starknet_service.deploy(ContractType.UserStats, [registry.contract_address, 1])

    # Give necessary rights to admin1
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAssets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageMarkets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFeeDetails, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFunds, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageCollateralPrices, True])

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountDeployer, 1, admin1.contract_address])

    # add user accounts to account registry
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [admin1.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [admin2.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [alice.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [bob.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [charlie.contract_address])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Asset, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Market, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.FeeDiscount, 1, feeDiscount.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.TradingFees, 1, fees.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Trading, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.FeeBalance, 1, feeBalance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Holding, 1, holding.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.EmergencyFund, 1, emergency.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.LiquidityFund, 1, liquidity.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.InsuranceFund, 1, insurance.contract_address])
    # await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Liquidate, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.CollateralPrices, 1, collateral_prices.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountRegistry, 1, account_registry.contract_address])
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
        minimum_order_size=10,
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
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

    # Set the threshold for oracle price in Trading contract
    await admin1_signer.send_transaction(admin1, trading.contract_address, 'set_threshold_percentage', [to64x61(5)])
    return starknet_service.starknet, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, feeBalance, marketPrices, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance


@pytest.mark.asyncio
async def test_revert_balance_low_user_1(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 100
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Low Balance- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_balance_low_user_2(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 100
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Low Balance- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_leverage_more_than_allowed_user_1(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "leverage": 10.1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Leverage must be <= to the maximum allowed leverage- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_leverage_more_than_allowed_user_2(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "leverage": 10.001,
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Leverage must be <= to the maximum allowed leverage- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_leverage_below_1(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "leverage": 0.9,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Leverage must be >= 1- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_wrong_market_passed(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "market_id": ETH_USD_ID,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: All orders in a batch must be from the same market- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_quantity_low_user_1(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 0.00001
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 0.00001,
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.00001,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Quantity must be >= to the minimum order size- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_quantity_low_user_2(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 0.00001
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.00001,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Quantity must be >= to the minimum order size- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_market_untradable(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = TSLA_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "market_id": TSLA_USD_ID,
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.00001,
        "market_id": TSLA_USD_ID,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Market is not tradable- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_unregistered_user(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, eduard]
    users_test = [alice_test, eduard_test]

    # Sufficient balance for users
    alice_balance = 10000
    eduard_balance = 10000
    balance_array = [alice_balance, eduard_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: User account not registered- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_taker_direction_wrong(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["long"],
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Taker order must be in opposite direction of Maker order(s)- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_maker_direction_wrong(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob, charlie]
    users_test = [alice_test, bob_test, charlie_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    charlie_balance = 10000
    balance_array = [alice_balance, bob_balance, charlie_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 2
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: All Maker orders must be in the same direction- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_invalid_batch_extra_maker_orders(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob, charlie]
    users_test = [alice_test, bob_test, charlie_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    charlie_balance = 10000
    balance_array = [alice_balance, bob_balance, charlie_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Taker order must come after Maker orders- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_invalid_batch_extra_taker_orders(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob, charlie]
    users_test = [alice_test, bob_test, charlie_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    charlie_balance = 10000
    balance_array = [alice_balance, bob_balance, charlie_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "side": order_side["taker"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Taker order must be the last order in the list- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_taker_post_only_order(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "side": order_side["taker"],
        "post_only": 1
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Post Only order cannot be a taker- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_taker_fk_partial_order(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"],
    }, {
        "quantity": 2,
        "direction": order_direction["short"],
        "side": order_side["taker"],
        "time_in_force": order_time_in_force["fill_or_kill"]

    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: F&K order should be executed fully- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_parent_position_is_empty(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["limit"],
        "close_order": close_order["close"]
    }, {
        "quantity": 2,
        "direction": order_direction["short"],
        "side": order_side["taker"],
        "time_in_force": order_time_in_force["fill_or_kill"]

    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"The parentPosition size cannot be 0- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_maker_order_is_market(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "order_type": order_types["market"],
    }, {
        "quantity": 2,
        "direction": order_direction["short"],
        "side": order_side["taker"],
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Maker orders must be limit orders- {error_at_index}")


@pytest.mark.asyncio
async def test_revert_if_price_beyond_threshold(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Insufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 1050.12,
        "order_type": order_types["limit"]
    }, {
        "quantity": 2,
        "direction": order_direction["short"],
        "side": order_side["taker"],
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_message=f"Trading: Execution price not in range- {error_at_index}")


@pytest.mark.asyncio
async def test_opening_and_closing_full_orders(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 10000
    bob_balance = 10000
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 3
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 3,
        "order_type": order_types["limit"]
    }, {
        "quantity": 3,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ###################
    ### Close orders ##
    ###################
    # Batch params for OPEN orders
    quantity_locked_2 = 3
    oracle_price_2 = 1000

    # Create orders
    orders_2 = [{
        "quantity": 3,
        "direction": order_direction["short"],
        "close_order": close_order["close"],
        "order_type": order_types["limit"]
    }, {
        "quantity": 3,
        "close_order": close_order["close"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ########


@pytest.mark.asyncio
async def test_opening_and_closing_full_orders_with_leverage(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
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
        "leverage": 4.234,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1.523,
        "leverage": 5.1,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ###################
    ### Close orders ##
    ###################
    # Batch params for OPEN orders
    quantity_locked_2 = 1.523
    oracle_price_2 = 1018.87

    # Create orders
    orders_2 = [{
        "quantity": 1.523,
        "direction": order_direction["short"],
        "close_order": close_order["close"],
        "order_type": order_types["limit"]
    }, {
        "quantity": 1.523,
        "close_order": close_order["close"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    #########


@pytest.mark.asyncio
async def test_opening_and_closing_three_orders_full_with_leverage(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob, charlie]
    users_test = [alice_test, bob_test, charlie_test]

    # Sufficient balance for users
    alice_balance = 12343.3428549
    bob_balance = 9334.98429831
    charlie_balance = 54324.65215
    balance_array = [alice_balance, bob_balance, charlie_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 0.53
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1013.41

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 0.6,
        "leverage": 6.435,
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.53,
        "leverage": 5.194,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ###################
    ### Close orders ##
    ###################
    # Batch params for OPEN orders
    quantity_locked_2 = 0.53
    oracle_price_2 = 1018.87

    # Create orders
    orders_2 = [{
        "quantity": 0.53,
        "direction": order_direction["short"],
        "close_order": close_order["close"],
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.53,
        "close_order": close_order["close"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    #########


@pytest.mark.asyncio
async def test_opening_partial_orders(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 5781.341239
    bob_balance = 9823.4731
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 0.81
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1013.41

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 2,
        # "leverage": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.81,
        # "leverage": 5.194,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_message=0)
    print(complete_orders_1[0]["order_id"])
    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ##########################
    ### Open orders Partial ##
    ##########################
    # Batch params for OPEN orders
    quantity_locked_2 = 1.19
    oracle_price_2 = 1002.87

    # Create orders
    orders_2 = [{
        "order_id": complete_orders_1[0]["order_id"]
    }, {
        "quantity": 1.19,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    #########


# @pytest.mark.asyncio
# async def test_closing_partial_orders(adminAuth_factory):
#     _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

#     ##############################
#     ### Close orders partially ###
#     ##############################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 1000
#     bob_balance = 1000
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 0.343
#     market_id_1 = BTC_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 1013.41

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "quantity": 2,
#         "close_order": close_order["close"],
#         "direction": order_direction["short"],
#         "order_type": order_types["limit"]
#     }, {
#         "quantity": 0.343,
#         "direction": order_direction["long"],
#         "side": order_side["taker"]
#     }]

#     user_short = bob_test.get_position(
#         market_id=market_id_1, direction=order_direction["short"])
#     print("Before order execution: ", user_short)

#     # execute order
#     complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_message=0)
#     print(complete_orders_1[0]["order_id"])

#     user_short = bob_test.get_position(
#         market_id=market_id_1, direction=order_direction["short"])
#     print("Before order execution: ", user_short)
#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     ###############################
#     ### Close orders partially ###
#     ##############################
#     # Batch params for OPEN orders
#     quantity_locked_2 = 1.657
#     oracle_price_2 = 1002.87

#     # Create orders
#     orders_2 = [{
#         "order_id": complete_orders_1[0]["order_id"]
#     }, {
#         "quantity": 1.9,
#         "direction": order_direction["long"],
#         "side": order_side["taker"]
#     }]

#     # execute order
#     complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_message=0)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     #########


@pytest.mark.asyncio
async def test_opening_and_closing_full_orders_different_market(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, eduard, fixed_math, holding, fee_balance, _, alice_test, bob_test, charlie_test, eduard_test, python_executor, liquidity, insurance = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 2321.3428549
    bob_balance = 4535.98429831
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 4.5
    market_id_1 = ETH_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 123.45

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "market_id": ETH_USD_ID,
        "quantity": 4.5,
        "price": 120.2,
        "order_type": order_types["limit"]
    }, {
        "market_id": ETH_USD_ID,
        "quantity": 4.5,
        "price": 120.2,
        "direction": order_direction["short"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ###################
    ### Close orders ##
    ###################
    # Batch params for OPEN orders
    quantity_locked_2 = 1.523
    oracle_price_2 = 130.87

    # Create orders
    orders_2 = [{
        "market_id": ETH_USD_ID,
        "quantity": 4.5,
        "price": 130.2,
        "direction": order_direction["short"],
        "close_order": close_order["close"],
        "order_type": order_types["limit"]
    }, {
        "market_id": ETH_USD_ID,
        "quantity": 4.5,
        "close_order": close_order["close"],
        "side": order_side["taker"]
    }]

    # execute order
    complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_message=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    #########
