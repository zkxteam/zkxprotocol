from copyreg import constructor
import pytest
import asyncio
import time
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, str_to_felt, to64x61, from64x61, PRIME
from starkware.starknet.testing.contract import StarknetContract
from utils_trading import (
    User, Liquidator, OrderExecutor,
    order_direction, order_types, side, fund_mapping,
    set_balance, execute_and_compare, mark_under_collateralized_position,
    compare_fund_balances, compare_user_balances, compare_user_positions, compare_debugging_values, compare_liquidatable_position, compare_margin_info
)
from utils_links import DEFAULT_LINK_1, prepare_starknet_string
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
liquidator_private_key = 123456789987654326
liquidator_signer = Signer(liquidator_private_key)
daniel_signer = Signer(123456789987654327)
eduard_signer = Signer(123456789987654328)
gary_signer = Signer(123456789987654329)
felix_signer = Signer(123456789987654330)

maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_DAI_ID = str_to_felt("nxczijewihrewi")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
ETH_DAI_ID = str_to_felt("dsfjlkj3249jfkdl")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
DOGE_ID = str_to_felt("jdi2i8621hzmnc7324o")
TSLA_ID = str_to_felt("i39sk1nxlqlzcee")

timestamp = int(time.time())
timestamp_1 = timestamp + 10
timestamp_2 = timestamp + 61
timestamp_3 = timestamp_2 + 59
timestamp_4 = timestamp_2 + 61
timestamp_5 = timestamp_4 + 61
timestamp_6 = timestamp_5 + 61
timestamp_7 = timestamp_6 + 61
timestamp_8 = timestamp_7 + 61
timestamp_9 = timestamp_8 + 61


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
    # Deploy infrastructure (Part 1)
    admin1 = await starknet_service.deploy(ContractType.Account, [admin1_signer.public_key])
    admin2 = await starknet_service.deploy(ContractType.Account, [admin2_signer.public_key])
    liquidator = await starknet_service.deploy(ContractType.Account, [liquidator_signer.public_key])
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    fees = await starknet_service.deploy(ContractType.TradingFees, [registry.contract_address, 1])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])

    python_executor = OrderExecutor()
    python_liquidator = Liquidator()
    # Deploy user accounts
    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )

    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    alice_test = User(123456789987654323,
                      alice.contract_address, liquidator_private_key)

    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    bob_test = User(123456789987654324, bob.contract_address,
                    liquidator_private_key)

    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)
    charlie_test = User(123456789987654325,
                        charlie.contract_address, liquidator_private_key)

    daniel = await account_factory.deploy_ZKX_account(daniel_signer.public_key)
    daniel_test = User(123456789987654327,
                       daniel.contract_address, liquidator_private_key)

    eduard = await account_factory.deploy_ZKX_account(eduard_signer.public_key)
    eduard_test = User(123456789987654328,
                       eduard.contract_address, liquidator_private_key)

    gary = await account_factory.deploy_ZKX_account(gary_signer.public_key)
    gary_test = User(123456789987654329,
                     gary.contract_address, liquidator_private_key)

    felix = await account_factory.deploy_ZKX_account(felix_signer.public_key)
    felix_test = User(123456789987654330,
                      felix.contract_address, liquidator_private_key)

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
    liquidityFund = await starknet_service.deploy(ContractType.LiquidityFund, [registry.contract_address, 1])
    trading = await starknet_service.deploy(ContractType.Trading, [registry.contract_address, 1])
    liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
    insuranceFund = await starknet_service.deploy(ContractType.InsuranceFund, [registry.contract_address, 1])
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [registry.contract_address, 1])
    marketPrices = await starknet_service.deploy(ContractType.MarketPrices, [registry.contract_address, 1])
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
    user_stats = await starknet_service.deploy(ContractType.UserStats, [registry.contract_address, 1])

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAssets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageMarkets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFeeDetails, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageFunds, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageCollateralPrices, True])

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # add user accounts to account registry
    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [admin1.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [admin2.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [alice.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [bob.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [charlie.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [daniel.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [eduard.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [gary.contract_address])

    await admin1_signer.send_transaction(
        admin1, account_registry.contract_address, 'add_to_account_registry', [felix.contract_address])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Asset, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Market, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.FeeDiscount, 1, feeDiscount.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.TradingFees, 1, fees.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Trading, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.FeeBalance, 1, feeBalance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Holding, 1, holding.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.LiquidityFund, 1, liquidityFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.InsuranceFund, 1, insuranceFund.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountRegistry, 1, account_registry.contract_address])
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

    # Add assets
    BTC_properties = build_asset_properties(
        id=AssetID.BTC,
        short_name=str_to_felt("BTC"),
        asset_version=0,
        is_tradable=1,
        is_collateral=0,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', BTC_properties)

    ETH_properties = build_asset_properties(
        id=AssetID.ETH,
        short_name=str_to_felt("ETH"),
        asset_version=0,
        is_tradable=1,
        is_collateral=0,
        token_decimal=18
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', ETH_properties)

    USDC_properties = build_asset_properties(
        id=AssetID.USDC,
        short_name=str_to_felt("USDC"),
        asset_version=0,
        is_tradable=0,
        is_collateral=1,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', USDC_properties)

    DAI_properties = build_asset_properties(
        id=AssetID.DAI,
        short_name=str_to_felt("DAI"),
        asset_version=0,
        is_tradable=0,
        is_collateral=1,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', DAI_properties)

    # Add markets
    BTC_USD_properties = MarketProperties(
        id=BTC_USD_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.USDC,
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        tick_precision=0,
        step_size=1,
        step_precision=0,
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(10),
        maintenance_margin_fraction=to64x61(0.075),
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', BTC_USD_properties.to_params_list())
    python_executor.set_market_details(
        market_id=BTC_USD_ID, details=BTC_USD_properties.to_dict())

    ETH_USD_properties = MarketProperties(
        id=ETH_USD_ID,
        asset=AssetID.ETH,
        asset_collateral=AssetID.USDC,
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        tick_precision=0,
        step_size=1,
        step_precision=0,
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(10),
        maintenance_margin_fraction=to64x61(0.075),
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', ETH_USD_properties.to_params_list())
    python_executor.set_market_details(
        market_id=ETH_USD_ID, details=ETH_USD_properties.to_dict())

    # Add markets
    BTC_DAI_properties = MarketProperties(
        id=BTC_DAI_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.DAI,
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        tick_precision=0,
        step_size=1,
        step_precision=0,
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(10),
        maintenance_margin_fraction=to64x61(0.075),
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', BTC_DAI_properties.to_params_list())
    python_executor.set_market_details(
        market_id=BTC_DAI_ID, details=BTC_DAI_properties.to_dict())

    ETH_DAI_properties = MarketProperties(
        id=ETH_DAI_ID,
        asset=AssetID.ETH,
        asset_collateral=AssetID.DAI,
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        tick_precision=0,
        step_size=1,
        step_precision=0,
        minimum_order_size=to64x61(0.0001),
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(10),
        maintenance_margin_fraction=to64x61(0.075),
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', ETH_DAI_properties.to_params_list())
    python_executor.set_market_details(
        market_id=ETH_DAI_ID, details=ETH_DAI_properties.to_dict())

    # Fund the Holding contract
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.DAI, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.DAI, to64x61(1000000)])

    # Fund the Liquidity fund contract
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.DAI, new_balance=1000000)
    python_executor.set_fund_balance(
        fund=fund_mapping["insurance_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    python_executor.set_fund_balance(
        fund=fund_mapping["insurance_fund"], asset_id=AssetID.DAI, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.DAI, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [AssetID.DAI, to64x61(1000000)])

    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund, alice_test, bob_test, charlie_test, python_executor, python_liquidator, feeBalance, liquidityFund, eduard_test, daniel_test, gary, felix, gary_test, felix_test, marketPrices, starknet_service


async def set_asset_price_by_trading(starknet_service, admin: StarknetContract, trading: StarknetContract, python_executor: OrderExecutor, new_timestamp: int,  gary: StarknetContract, felix: StarknetContract, gary_test: User, felix_test: User, market_id: int, collateral_id: int, price: float):

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1,
        block_timestamp=new_timestamp,
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    # List of users
    users = [gary, felix]
    users_test = [gary_test, felix_test]

    # Collaterals
    collateral_id_1 = collateral_id

    # Sufficient balance for users
    gary_balance = 1000000
    felix_balance = 1000000

    balance_array = [gary_balance, felix_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = market_id
    oracle_price_1 = price

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin, users=users, users_test=users_test, balance_array=balance_array, asset_id=collateral_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": price,
        "market_id": market_id_1,
        "order_type": order_types["limit"],
    }, {
        "quantity": 1,
        "price": price,
        "market_id": market_id_1,
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0, timestamp=new_timestamp)


@pytest.mark.asyncio
async def test_get_account_info(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insurance,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, fee_balance, liquidity, eduard_test, daniel_test,  gary, felix, gary_test, felix_test, marketPrices, starknet_service = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [bob, alice]
    users_test = [bob_test, alice_test]

    # Collaterals
    collateral_id_1 = AssetID.USDC

    # Sufficient balance for users
    alice_balance_usdc = 610
    bob_balance_usdc = 6100

    balance_array_usdc = [bob_balance_usdc, alice_balance_usdc]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 5000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array_usdc, asset_id=collateral_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 5000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
        "leverage": 2,
    }, {
        "quantity": 1,
        "price": 5000,
        "leverage": 10,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0, timestamp=timestamp)

    # compare
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)

    # compare margin info
    await compare_margin_info(user=alice, user_test=alice_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)
    await compare_margin_info(user=bob, user_test=bob_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)
    #################################################
    ######## Alice's liquidation result USDC ########
    #################################################
    await mark_under_collateralized_position(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=alice, user_test=alice_test, liquidate=liquidate, collateral_id=collateral_id_1, order_executor=python_executor, timestamp=timestamp)

    await compare_debugging_values(liquidate=liquidate, liquidator=python_liquidator)
    await compare_liquidatable_position(user=alice, user_test=alice_test, collateral_id=collateral_id_1)

    info = await alice.get_account_info(AssetID.USDC).call()
    print("Account info: ", info.result)

    ################################################
    ####### Bob's liquidation result USDC ##########
    ################################################
    await mark_under_collateralized_position(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=bob, user_test=bob_test, liquidate=liquidate, collateral_id=collateral_id_1, order_executor=python_executor, timestamp=timestamp)

    await compare_debugging_values(liquidate=liquidate, liquidator=python_liquidator)
    await compare_liquidatable_position(user=bob, user_test=bob_test, collateral_id=collateral_id_1)

    # ###### Opening of Orders 2 #######
    # Batch params for OPEN orders 2
    quantity_locked_2 = 0.02
    market_id_2 = BTC_USD_ID
    asset_id_2 = AssetID.USDC
    oracle_price_2 = 5000

    orders_2 = [{
        "quantity": 0.02,
        "market_id": BTC_USD_ID,
        "price": 5000,
        "order_type": order_types["limit"],
        "leverage": 1,
    }, {
        "quantity": 0.02,
        "market_id": BTC_USD_ID,
        "price": 5000,
        "direction": order_direction["short"],
        "leverage": 1,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0, timestamp=timestamp)

    # compare
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_2)
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_2)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)

    # compare margin info
    await compare_margin_info(user=alice, user_test=alice_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)
    await compare_margin_info(user=bob, user_test=bob_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp)

    ###################################################
    ######## Alice's liquidation result USDC 2 ########
    ###################################################
    await mark_under_collateralized_position(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=alice, user_test=alice_test, liquidate=liquidate, collateral_id=collateral_id_1, order_executor=python_executor, timestamp=timestamp)

    await compare_debugging_values(liquidate=liquidate, liquidator=python_liquidator)
    await compare_liquidatable_position(user=alice, user_test=alice_test, collateral_id=collateral_id_1)

    info = await alice.get_account_info(AssetID.USDC).call()
    print("Account info: ", info.result)

    await set_asset_price_by_trading(starknet_service=starknet_service, admin=admin1, trading=trading, python_executor=python_executor, new_timestamp=timestamp_2,  gary=gary,
                                     felix=felix, gary_test=gary_test, felix_test=felix_test, market_id=market_id_1, collateral_id=collateral_id_1, price=4000)

    await mark_under_collateralized_position(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=alice, user_test=alice_test, liquidate=liquidate, collateral_id=collateral_id_1, order_executor=python_executor, timestamp=timestamp)

    await compare_debugging_values(liquidate=liquidate, liquidator=python_liquidator)
    await compare_liquidatable_position(user=alice, user_test=alice_test, collateral_id=collateral_id_1)

    info = await alice.get_account_info(AssetID.USDC).call()
    print("Account info: ", info.result)
