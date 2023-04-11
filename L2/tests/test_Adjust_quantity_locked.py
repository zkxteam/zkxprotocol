from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from starkware.starknet.business_logic.execution.objects import OrderedEvent
from starkware.starknet.public.abi import get_selector_from_name

from utils import ContractIndex, ManagerAction, Signer, str_to_felt, from64x61, to64x61, assert_revert, assert_event_with_custom_keys_emitted, PRIME, PRIME_HALF
from utils_trading import User, order_direction, order_side, order_types, order_time_in_force, side, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, compare_margin_info, check_batch_status, compare_markets_array
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
non_admin_signer = Signer(123456789987654330)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
dave_signer = Signer(123456789987654326)
eduard_signer = Signer(123456789987654327)
felix_signer = Signer(123456789987654328)
gary_signer = Signer(123456789987654329)


maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")

timestamp = int(time.time())
timestamp1 = int(time.time()) + 61
timestamp2 = timestamp1 + 125


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def trading_test_initializer(starknet_service: StarknetService):

    # Deploy infrastructure (Part 1)
    admin1 = await starknet_service.deploy(ContractType.Account, [
        admin1_signer.public_key
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        admin2_signer.public_key
    ])
    non_admin = await starknet_service.deploy(ContractType.Account, [
        non_admin_signer.public_key
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
    print("alice", hex(alice.contract_address))
    alice_test = User(123456789987654323, alice.contract_address)

    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    print("bob", hex(bob.contract_address))
    bob_test = User(123456789987654324, bob.contract_address)

    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)
    print("charlie", hex(charlie.contract_address))
    charlie_test = User(123456789987654325, charlie.contract_address)

    dave = await account_factory.deploy_account(dave_signer.public_key)
    print("dave", hex(dave.contract_address))

    eduard = await account_factory.deploy_ZKX_account(eduard_signer.public_key)
    eduard_test = User(123456789987654327, eduard.contract_address)

    felix = await account_factory.deploy_ZKX_account(felix_signer.public_key)
    print("felix", hex(felix.contract_address))
    felix_test = User(123456789987654328, felix.contract_address)

    gary = await account_factory.deploy_ZKX_account(gary_signer.public_key)
    print("gary", hex(gary.contract_address))
    gary_test = User(123456789987654329, gary.contract_address)

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
    liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
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
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [felix.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [gary.contract_address])

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
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Liquidate, 1, liquidate.contract_address])
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
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(20),
        currently_allowed_leverage=to64x61(20),
        maintenance_margin_fraction=to64x61(0.075),
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
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(20),
        currently_allowed_leverage=to64x61(20),
        maintenance_margin_fraction=to64x61(0.075),
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
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(20),
        currently_allowed_leverage=to64x61(20),
        maintenance_margin_fraction=to64x61(0.075),
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
        is_tradable=False,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=10,
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(5),
        currently_allowed_leverage=to64x61(3),
        maintenance_margin_fraction=to64x61(0.075),
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
        maintenance_margin_fraction=to64x61(0.075),
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', UST_USDC_properties.to_params_list())

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
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    print("Trading contract:", hex(trading.contract_address))
    print("liquidate contract:", hex(liquidate.contract_address))
    print("Market:", hex(market.contract_address))
    print("Market Prices:", hex(marketPrices.contract_address))
    print("Auth Registry", hex(registry.contract_address))

    return starknet_service.starknet, python_executor, admin1, admin2, alice, bob, charlie, dave, eduard, felix, gary, alice_test, bob_test, charlie_test, eduard_test, felix_test, gary_test, adminAuth, fees, asset, trading, marketPrices, fixed_math, holding, feeBalance, liquidity, insurance, trading_stats, non_admin


@pytest.mark.asyncio
async def test_adjust_quantity_locked(trading_test_initializer):
    starknet_service, python_executor, admin1, _, _, _, _, _, _, felix, gary, _, _, _, _, felix_test, gary_test, _, _, _, trading, marketPrices, _, holding, fee_balance, liquidity, insurance, trading_stats, non_admin = trading_test_initializer

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [felix, gary]
    users_test = [felix_test, gary_test]

    # Sufficient balance for users
    felix_balance = 5000
    gary_balance = 2000
    balance_array = [felix_balance, gary_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 3
    market_id_1 = ETH_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 2000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 3,
        "market_id": ETH_USD_ID,
        "price": 2000,
        "order_type": order_types["limit"],
        "leverage": 5
    }, {
        "quantity": 3,
        "market_id": ETH_USD_ID,
        "price": 2000,
        "leverage": 5,
        "direction": order_direction["short"],
    }]

    # execute order
    (batch_id_1, _, info) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, timestamp=timestamp)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # compare margin info
    await compare_margin_info(user=felix, user_test=felix_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)
    await compare_margin_info(user=gary, user_test=gary_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)

    # compare markets array
    await compare_markets_array(user=felix, user_test=felix_test, collatera_id=asset_id_1)
    await compare_markets_array(user=gary, user_test=gary_test, collatera_id=asset_id_1)

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [felix, felix, gary]
    users_test = [felix_test, felix_test, gary_test]

    # Batch params for OPEN orders
    quantity_locked_2 = 4
    market_id_2 = ETH_USD_ID
    asset_id_2 = AssetID.USDC
    oracle_price_2 = 2000

    # Create orders
    orders_2 = [{
        "quantity": 2.5,
        "market_id": ETH_USD_ID,
        "price": 2000,
        "side": side["sell"],
        "order_type": order_types["limit"],
    }, {
        "quantity": 1.5,
        "market_id": ETH_USD_ID,
        "price": 2000,
        "side": side["sell"],
        "order_type": order_types["limit"],
    }, {
        "quantity": 4,
        "market_id": ETH_USD_ID,
        "price": 2000,
        "leverage": 10,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0, timestamp=timestamp)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_2)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_2)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_2)

    # compare margin info
    await compare_margin_info(user=felix, user_test=felix_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)
    await compare_margin_info(user=gary, user_test=gary_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)

    # compare markets array
    await compare_markets_array(user=felix, user_test=felix_test, collatera_id=asset_id_1)
    await compare_markets_array(user=gary, user_test=gary_test, collatera_id=asset_id_1)

    info = await felix.get_account_info(AssetID.USDC).call()
    print("Account info: ", info.result)