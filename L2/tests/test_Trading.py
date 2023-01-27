from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, str_to_felt, from64x61, to64x61, assert_revert, PRIME, PRIME_HALF
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

timestamp = 0


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def trading_test_initializer(starknet_service: StarknetService):
    global timestamp

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
    liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
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

    print("Trading contract:", hex(trading.contract_address))
    print("liquidate contract:", hex(liquidate.contract_address))
    print("Market:", hex(market.contract_address))
    print("Market Prices:", hex(marketPrices.contract_address))
    print("Auth Registry", hex(registry.contract_address))
    return starknet_service.starknet, python_executor, admin1, admin2, alice, bob, charlie, dave, eduard, felix, gary, alice_test, bob_test, charlie_test, eduard_test, felix_test, gary_test, adminAuth, fees, asset, trading, marketPrices, fixed_math, holding, feeBalance, liquidity, insurance, trading_stats


# @pytest.mark.asyncio
# async def test_for_risk_while_opening_order(trading_test_initializer):
#     starknet_service, python_executor, admin1, _, _, _, _, _, _, felix, gary, _, _, _, _, felix_test, gary_test, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer
#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [felix, gary]
#     users_test = [felix_test, gary_test]

#     # Sufficient balance for users
#     felix_balance = 100
#     gary_balance = 100
#     balance_array = [felix_balance, gary_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 1
#     market_id_1 = BTC_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 200

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "quantity": 1,
#         "price": 200,
#         "order_type": order_types["limit"],
#         "leverage": 10
#     }, {
#         "quantity": 1,
#         "price": 200,
#         "leverage": 3,
#         "direction": order_direction["short"],
#     }]

#     # execute order
#     (batch_id_1, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)
#     await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     timestamp = int(time.time()) + 61

#     starknet_service.state.state.block_info = BlockInfo(
#         block_number=1, block_timestamp=timestamp, gas_price=starknet_service.state.state.block_info.gas_price,
#         sequencer_address=starknet_service.state.state.block_info.sequencer_address,
#         starknet_version=STARKNET_VERSION
#     )

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [felix, gary]
#     users_test = [felix_test, gary_test]

#     # Sufficient balance for users
#     felix_balance = 40
#     gary_balance = 100
#     balance_array = [felix_balance, gary_balance]

#     # Batch params for OPEN orders
#     quantity_locked_2 = 1
#     market_id_2 = BTC_USD_ID
#     asset_id_2 = AssetID.USDC
#     oracle_price_2 = 40

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_2)

#     # Create orders
#     orders_2 = [{
#         "quantity": 1,
#         "price": 40,
#         "order_type": order_types["limit"],
#         "leverage": 10
#     }, {
#         "quantity": 1,
#         "price": 40,
#         "leverage": 3,
#         "direction": order_direction["short"],
#     }]

#     # execute order
#     await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_2)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_2)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_2)

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [felix, gary]
#     users_test = [felix_test, gary_test]

#     # Sufficient balance for users
#     felix_balance = 40
#     gary_balance = 40
#     balance_array = [felix_balance, gary_balance]

#     # Batch params for OPEN orders
#     quantity_locked_3 = 1
#     market_id_3 = BTC_USD_ID
#     asset_id_3 = AssetID.USDC
#     oracle_price_3 = 40

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_3)

#     # Create orders
#     orders_3 = [{
#         "quantity": 1,
#         "price": 40,
#         "order_type": order_types["limit"],
#         "leverage": 10
#     }, {
#         "quantity": 1,
#         "price": 40,
#         "leverage": 3,
#         "direction": order_direction["short"],
#     }]

#     # execute order
#     await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_3, users_test=users_test, quantity_locked=quantity_locked_3, market_id=market_id_3, oracle_price=oracle_price_3, trading=trading, is_reverted=1, error_code="1101:", error_at_index=0, param_2=market_id_3)

#     open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
#     assert open_interest_response.result.res == to64x61(2)

@pytest.mark.asyncio
async def test_revert_balance_low_user_1(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0501:", error_at_index=error_at_index, param_2=to64x61(alice_balance))


@pytest.mark.asyncio
async def test_revert_balance_low_user_2(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0501:", error_at_index=error_at_index, param_2=to64x61(bob_balance))


@pytest.mark.asyncio
async def test_revert_if_leverage_more_than_allowed_user_1(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0502:", error_at_index=error_at_index, param_2=to64x61(10.1))


@pytest.mark.asyncio
async def test_revert_if_leverage_more_than_allowed_user_2(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0502:", error_at_index=error_at_index, param_2=to64x61(10.001))


@pytest.mark.asyncio
async def test_revert_if_leverage_below_1(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0503:", error_at_index=error_at_index, param_2=to64x61(0.9))


@pytest.mark.asyncio
async def test_revert_if_wrong_market_passed(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0504:", error_at_index=error_at_index, param_2=ETH_USD_ID)


@pytest.mark.asyncio
async def test_revert_if_quantity_low_user_1(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0505:", error_at_index=error_at_index, param_2=to64x61(0.00001))


@pytest.mark.asyncio
async def test_revert_if_quantity_low_user_2(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0505:", error_at_index=error_at_index, param_2=to64x61(0.00001))


@pytest.mark.asyncio
async def test_revert_if_market_order_slippage_error(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
        "order_type": order_types["limit"],
        "price": 1010.01
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "slippage": 1
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0506:", error_at_index=error_at_index, param_2=to64x61(1010.01))


@pytest.mark.asyncio
async def test_revert_if_limit_order_bad_short_limit_price(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
        "order_type": order_types["limit"],
        "price": 1010.01
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "order_type": order_types["limit"],
        "price": 1010.02
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0507:", error_at_index=error_at_index, param_2=to64x61(1010.01))


@pytest.mark.asyncio
async def test_revert_if_limit_order_bad_long_limit_price(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
        "price": 1010.01
    }, {
        "quantity": 1,
        "order_type": order_types["limit"],
        "price": 1010.00
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0508:", error_at_index=error_at_index, param_2=to64x61(1010.01))


@pytest.mark.asyncio
async def test_revert_if_market_untradable(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0509:", param_2=TSLA_USD_ID)


@pytest.mark.asyncio
async def test_revert_if_unregistered_user(trading_test_initializer):
    _, python_executor, admin1, _, alice, _, _, _, eduard, _, _, alice_test, _, _, eduard_test, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [eduard, alice]
    users_test = [eduard_test, alice_test]

    # Sufficient balance for users
    alice_balance = 10000
    eduard_balance = 10000
    balance_array = [eduard_balance, alice_balance]

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
    }]

    error_at_index = 0
    signed_address = eduard.contract_address - \
        PRIME if eduard.contract_address > PRIME_HALF else eduard.contract_address
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0510:", error_at_index=error_at_index, param_2=signed_address)


@pytest.mark.asyncio
async def test_revert_if_taker_direction_wrong(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
        "direction": order_direction["long"]
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0511:", error_at_index=error_at_index, param_2=order_direction["long"])


@pytest.mark.asyncio
async def test_revert_if_maker_direction_wrong(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0512:", error_at_index=error_at_index, param_2=order_direction["short"])


@pytest.mark.asyncio
async def test_revert_if_invalid_batch_extra_maker_orders(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0513:", error_at_index=error_at_index, param_2=error_at_index)


@pytest.mark.asyncio
async def test_revert_if_insufficient_maker_orders(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
        "quantity": 0.5,
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.5,
        "order_type": order_types["limit"]
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
        "order_type": order_types["limit"]
    }]

    error_at_index = 2
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0514:", error_at_index=error_at_index, param_2=error_at_index)


@pytest.mark.asyncio
async def test_revert_if_invalid_batch_extra_taker_orders(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer
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
        "direction": order_direction["short"],
    }, {
        "quantity": 1,
        "direction": order_direction["short"],
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0512:", error_at_index=error_at_index, param_2=order_direction["short"])


@pytest.mark.asyncio
async def test_revert_if_taker_post_only_order(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
        "post_only": 1
    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0515:", error_at_index=error_at_index, param_2=error_at_index)


@pytest.mark.asyncio
async def test_revert_if_taker_fk_partial_order(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
        "time_in_force": order_time_in_force["fill_or_kill"]

    }]

    error_at_index = 1
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0516:", error_at_index=error_at_index, param_2=to64x61(1))


@pytest.mark.asyncio
async def test_revert_if_maker_order_is_market(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=1, error_code=f"0518:", error_at_index=error_at_index, param_2=error_at_index)


@pytest.mark.asyncio
async def test_revert_if_price_beyond_threshold(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

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
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=timestamp, is_reverted=1, error_code=f"0519:", error_at_index=error_at_index, param_2=to64x61(1050.12))


@pytest.mark.asyncio
async def test_opening_and_closing_full_orders(trading_test_initializer):
    starknet_service, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

    timestamp = int(time.time()) + 61

    starknet_service.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.state.state.block_info.gas_price,
        sequencer_address=starknet_service.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

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
    }]

    # execute order
    (batch_id_1, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
    # assert open_interest_response.result.res == to64x61(5)

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
        "life_cycle": order_life_cycles["close"],
        "order_type": order_types["limit"]
    }, {
        "quantity": 3,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    (batch_id_2, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_2, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
    # assert open_interest_response.result.res == to64x61(2)


@pytest.mark.asyncio
async def test_opening_and_closing_full_orders_with_leverage(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

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
    }]

    # execute order
    (batch_id_1, _) = complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

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
        "life_cycle": order_life_cycles["close"],
        "order_type": order_types["limit"]
    }, {
        "quantity": 1.523,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    (batch_id_2, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_2, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
    # assert open_interest_response.result.res == to64x61(2)


@pytest.mark.asyncio
async def test_opening_and_closing_three_orders_full_with_leverage(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

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
    }]

    # execute order
    (batch_id_1, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

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
        "life_cycle": order_life_cycles["close"],
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.53,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    (batch_id_2, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_2, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
    # assert open_interest_response.result.res == to64x61(2)


@pytest.mark.asyncio
async def test_IoC_orders(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

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
        "order_type": order_types["limit"],
        "time_in_force": order_time_in_force["immediate_or_cancel"]
    }, {
        "quantity": 0.81,
        "direction": order_direction["short"],
    }]

    # execute order
    (batch_id_1, complete_orders_1) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
    # assert from64x61(open_interest_response.result.res) == 2.81

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
    }]

    error_at_index = 0

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=1, error_code=f"0520:", error_at_index=error_at_index, param_2=to64x61(1.19))


@pytest.mark.asyncio
async def test_opening_partial_orders(trading_test_initializer):
    _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

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
        "leverage": 1,
        "order_type": order_types["limit"]
    }, {
        "quantity": 0.81,
        "leverage": 1,
        "direction": order_direction["short"],
    }]

    # execute order
    (batch_id_1, complete_orders_1) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

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
    }]

    # execute order
    (batch_id_2, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_2, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
    # assert pytest.approx(
    #     from64x61(open_interest_response.result.res), abs=1e-6) == 4.81


# @pytest.mark.asyncio
# async def test_closing_partial_orders(trading_test_initializer):
#     _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

#     ##############################
#     ### Close orders partially ###
#     ##############################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 10000
#     bob_balance = 10000
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
#         "life_cycle": order_life_cycles["close"],
#         "direction": order_direction["short"],
#         "order_type": order_types["limit"]
#     }, {
#         "quantity": 0.343,
#         "direction": order_direction["long"],
#     }]

#     user_short = bob_test.get_position(
#         market_id=market_id_1, direction=order_direction["short"])

#     # execute order
#     (_, complete_orders_1) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)

#     user_short = bob_test.get_position(
#         market_id=market_id_1, direction=order_direction["short"])
#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
#     # assert pytest.approx(
#     #     from64x61(open_interest_response.result.res), abs=1e-6) == 4.81

#     ###############################
#     ### Close orders partially ###
#     ##############################
#     # Batch params for OPEN orders
#     quantity_locked_2 = 1.656
#     oracle_price_2 = 1002.87

#     # Create orders
#     orders_2 = [{
#         "order_id": complete_orders_1[0]["order_id"]
#     }, {
#         "quantity": 1.9,
#         "direction": order_direction["long"],
#     }]

#     # execute order
#     (_, complete_orders_1) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     # open_interest_response = await trading_stats.get_open_interest(BTC_USD_ID).call()
#     # assert pytest.approx(
#     #     from64x61(open_interest_response.result.res), abs=1e-6) == 4.81


# @pytest.mark.asyncio
# async def test_opening_and_closing_full_orders_different_market(trading_test_initializer):
#     _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 2321.3428549
#     bob_balance = 4535.98429831
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 4.5
#     market_id_1 = ETH_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 123.45

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "market_id": ETH_USD_ID,
#         "quantity": 4.5,
#         "price": 120.2,
#         "order_type": order_types["limit"]
#     }, {
#         "market_id": ETH_USD_ID,
#         "quantity": 4.5,
#         "price": 120.2,
#         "direction": order_direction["short"],
#     }]

#     # execute order
#     complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     # open_interest_response = await trading_stats.get_open_interest(ETH_USD_ID).call()
#     # assert from64x61(open_interest_response.result.res) == 4.5

#     ###################
#     ### Close orders ##
#     ###################
#     # Batch params for OPEN orders
#     quantity_locked_2 = 1.523
#     oracle_price_2 = 130.87

#     # Create orders
#     orders_2 = [{
#         "market_id": ETH_USD_ID,
#         "quantity": 4.5,
#         "price": 130.2,
#         "direction": order_direction["short"],
#         "life_cycle": order_life_cycles["close"],
#         "order_type": order_types["limit"]
#     }, {
#         "market_id": ETH_USD_ID,
#         "quantity": 4.5,
#         "price": 130.2,
#         "life_cycle": order_life_cycles["close"],
#     }]

#     # execute order
#     complete_orders_1 = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     # open_interest_response = await trading_stats.get_open_interest(ETH_USD_ID).call()
#     # assert pytest.approx(
#     #     from64x61(open_interest_response.result.res), abs=1e-6) == 2.977


# @pytest.mark.asyncio
# async def test_placing_order_directly(trading_test_initializer):
#     _, _, admin1, _, alice, bob, _, dave, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _ = trading_test_initializer

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 2321.3428549
#     bob_balance = 4535.98429831
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 4.5
#     market_id_1 = ETH_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 123.45

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     params = [
#         36913743897347031862778619449, 556715728833533465056602594347606394, 2, 300220759799622926336, 10376293541461622784, 2305843009213693952, 11529215046068469760, 2, 1, 0, 2, 0,
#         2022636113203008365857965845582934391243391428823771186281133992973234911008, 3145510324462252454033893057773896499982168619823607300721129275918411551641,
#         10376293541461622784,
#         300220759799622926336,
#         150110379899811463168,
#         150110379899811463168,
#         556715728833533465056602594347606394,
#         0
#     ]

#     await assert_revert(
#         dave_signer.send_transaction(
#             dave, alice.contract_address, "execute_order", params),
#         "0002: 36913743897347031862778619449 556715728833533465056602594347606394"
#     )


# @pytest.mark.asyncio
# async def test_closing_more_than_parent_size(trading_test_initializer):
#     _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, _ = trading_test_initializer

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 10000
#     bob_balance = 10000
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 3
#     market_id_1 = BTC_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 1000

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "quantity": 3,
#         "order_type": order_types["limit"]
#     }, {
#         "quantity": 3,
#         "direction": order_direction["short"],
#     }]

#     # execute order
#     (batch_id_1, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
#     await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     ###################
#     ### Close orders ##
#     ###################
#     # Batch params for OPEN orders
#     quantity_locked_2 = 4
#     oracle_price_2 = 1000

#     # Create orders
#     orders_2 = [{
#         "quantity": 4,
#         "direction": order_direction["short"],
#         "life_cycle": order_life_cycles["close"],
#         "order_type": order_types["limit"]
#     }, {
#         "quantity": 4,
#         "life_cycle": order_life_cycles["close"],
#     }]

#     error_at_index = 0
#     # execute order
#     await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=1, error_code="0003:", error_at_index=error_at_index, param_2=to64x61(4))


# @pytest.mark.asyncio
# async def test_invalid_liquidation(trading_test_initializer):
#     _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, _ = trading_test_initializer

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 10000
#     bob_balance = 10000
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 3
#     market_id_1 = BTC_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 1000

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "quantity": 3,
#         "order_type": order_types["limit"],
#         "leverage": 3
#     }, {
#         "quantity": 3,
#         "direction": order_direction["short"],
#         "leverage": 3
#     }]

#     # execute order
#     (batch_id_1, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
#     await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     ###################
#     ### Close orders ##
#     ###################
#     # Batch params for OPEN orders
#     quantity_locked_2 = 3
#     oracle_price_2 = 1500

#     # Create orders
#     orders_2 = [{
#         "quantity": 3,
#         "price": 1500,
#         "direction": order_direction["short"],
#         "life_cycle": order_life_cycles["close"],
#         "order_type": order_types["limit"],
#     }, {
#         "quantity": 3,
#         "price": 1500,
#         "life_cycle": order_life_cycles["close"],
#         "order_type": order_types["liquidation"]
#     }]

#     error_at_index = 1
#     # execute order
#     await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=1, error_code="0004:", error_at_index=error_at_index, param_2=market_id_1)


# @pytest.mark.asyncio
# async def test_invalid_deleverage(trading_test_initializer):
#     _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, _ = trading_test_initializer

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 10000
#     bob_balance = 10000
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 3
#     market_id_1 = BTC_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 1000

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "quantity": 3,
#         "order_type": order_types["limit"],
#         "leverage": 3
#     }, {
#         "quantity": 3,
#         "direction": order_direction["short"],
#         "leverage": 3
#     }]

#     # execute order
#     (batch_id_1, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
#     await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     ###################
#     ### Close orders ##
#     ###################
#     # Batch params for OPEN orders
#     quantity_locked_2 = 3
#     oracle_price_2 = 1500

#     # Create orders
#     orders_2 = [{
#         "quantity": 3,
#         "price": 1500,
#         "direction": order_direction["short"],
#         "life_cycle": order_life_cycles["close"],
#         "order_type": order_types["limit"],
#     }, {
#         "quantity": 3,
#         "price": 1500,
#         "life_cycle": order_life_cycles["close"],
#         "order_type": order_types["deleverage"]
#     }]

#     error_at_index = 1
#     # execute order
#     await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=1, error_code="0004:", error_at_index=error_at_index, param_2=market_id_1)


# @pytest.mark.asyncio
# async def test_opening_partial_orders_multiple(trading_test_initializer):
#     _, python_executor, admin1, _, alice, bob, charlie, _, _, _, _, alice_test, bob_test, charlie_test, _, _, _, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats = trading_test_initializer

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Sufficient balance for users
#     alice_balance = 5000
#     bob_balance = 5000
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 1
#     market_id_1 = BTC_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 1000

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "quantity": 2,
#         "order_type": order_types["limit"]
#     }, {
#         "quantity": 1,
#         "direction": order_direction["short"],
#     }]

#     # execute order
#     (batch_id_1, complete_orders_1) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
#     await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

#     ##########################
#     ### Open orders Partial ##
#     ##########################
#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob, charlie]
#     users_test = [alice_test, bob_test, charlie_test]

#     # Sufficient balance for users
#     alice_balance = 5000
#     bob_balance = 5000
#     charlie_balance = 5000
#     balance_array = [alice_balance, bob_balance, charlie_balance]

#     # Batch params for OPEN orders
#     quantity_locked_2 = 2
#     market_id_2 = BTC_USD_ID
#     asset_id_2 = AssetID.USDC
#     oracle_price_2 = 1000

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_2 = [{
#         "order_id": complete_orders_1[0]["order_id"]
#     }, {
#         "quantity": 1,
#         "order_type": order_types["limit"]
#     },   {
#         "quantity": 2,
#         "direction": order_direction["short"],
#     }]

#     # execute order
#     (batch_id_2, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, timestamp=from64x61(timestamp), is_reverted=0, error_code=0)
#     await check_batch_status(batch_id=batch_id_2, trading=trading, is_executed=1)

#     # check balances
#     await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_2)
#     await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_2)
#     await compare_user_positions(users=users, users_test=users_test, market_id=market_id_2)


# @pytest.mark.asyncio
# async def test_revert_if_parent_position_is_empty(trading_test_initializer):
#     _, python_executor, admin1, _, alice, bob, _, _, _, _, _, alice_test, bob_test, _, _, _, _, _, _, _, trading, _, _, _, _, _, _, _ = trading_test_initializer

#     ###################
#     ### Open orders ##
#     ###################
#     # List of users
#     users = [alice, bob]
#     users_test = [alice_test, bob_test]

#     # Insufficient balance for users
#     alice_balance = 10000
#     bob_balance = 10000
#     balance_array = [alice_balance, bob_balance]

#     # Batch params for OPEN orders
#     quantity_locked_1 = 1
#     market_id_1 = BTC_USD_ID
#     asset_id_1 = AssetID.USDC
#     oracle_price_1 = 1000

#     # Set balance in Starknet & Python
#     await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

#     # Create orders
#     orders_1 = [{
#         "quantity": 1,
#         "order_type": order_types["limit"],
#         "life_cycle": order_life_cycles["close"]
#     }, {
#         "quantity": 2,
#         "direction": order_direction["short"],
#         "time_in_force": order_time_in_force["fill_or_kill"]

#     }]

#     error_at_index = 0
#     # execute order
#     await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=from64x61(timestamp), is_reverted=1, error_code=f"0517:", error_at_index=error_at_index, param_2=order_direction["short"])
