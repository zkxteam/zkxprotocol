import pytest
import asyncio
import time
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, str_to_felt, from64x61, to64x61, assert_revert, PRIME, PRIME_HALF, assert_event_with_custom_keys_emitted
from utils_trading import User, Liquidator,order_direction, order_types, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, check_batch_status, get_safe_amount_to_withdraw_python, compare_margin_info, compare_markets_array, side
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

timestamp = int(time.time())
timestamp1 = int(time.time()) + 61
timestamp2 = timestamp1 + 61
timestamp3 = timestamp2 + 61
timestamp4 = timestamp3 + 121


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
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry', [eduard.contract_address])
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
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(3),
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
        maintenance_margin_fraction=1,
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', TSLA_USD_properties.to_params_list())

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
    return starknet_service.starknet, python_executor, admin1, admin2, alice, bob, charlie, dave, eduard, felix, gary, alice_test, bob_test, charlie_test, eduard_test, felix_test, gary_test, adminAuth, fees, asset, trading, marketPrices, fixed_math, holding, feeBalance, liquidity, insurance, trading_stats, python_liquidator


@pytest.mark.asyncio
async def test_for_risk_while_opening_order(trading_test_initializer):
    starknet_service, python_executor, admin1, _, alice, bob, charlie, _, eduard, felix, gary, alice_test, bob_test, charlie_test, eduard_test, felix_test, gary_test, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats, python_liquidator = trading_test_initializer
    
    ### Open orders to set price ###

    # List of users
    users = [felix, gary]
    users_test = [felix_test, gary_test]

    # Sufficient balance for users
    felix_balance = 200
    gary_balance = 200
    balance_array = [felix_balance, gary_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 100

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 100,
        "order_type": order_types["limit"],
        "leverage": 1
    }, {
        "quantity": 1,
        "price": 100,
        "leverage": 1,
        "direction": order_direction["short"],
    }]

    # execute order
    (batch_id_1, _, info) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, timestamp=timestamp)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    starknet_service.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp1, gas_price=starknet_service.state.state.block_info.gas_price,
        sequencer_address=starknet_service.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ### Open orders Alice and Bob ###

    # List of users
    users = [alice, bob]
    users_test = [alice_test, bob_test]

    # Sufficient balance for users
    alice_balance = 155
    bob_balance = 1100
    balance_array = [alice_balance, bob_balance]

    # Batch params for OPEN orders
    quantity_locked_2 = 10
    market_id_2 = BTC_USD_ID
    asset_id_2 = AssetID.USDC
    oracle_price_2 = 100

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_2)

    # Create orders
    orders_2 = [{
        "quantity": 10,
        "price": 100,
        "order_type": order_types["limit"],
        "leverage": 10
    }, {
        "quantity": 10,
        "price": 100,
        "leverage": 1,
        "direction": order_direction["short"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0, timestamp=timestamp1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_2)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_2)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_2)

    withdrawable_starknet = await alice.get_safe_amount_to_withdraw(AssetID.USDC).call()
    withdrawable_python = get_safe_amount_to_withdraw_python(alice_test, python_liquidator, python_executor, AssetID.USDC, timestamp1)

    assert from64x61(withdrawable_starknet.result.safe_withdrawal_amount) == pytest.approx(withdrawable_python[0], abs=1e-3)
    assert from64x61(withdrawable_starknet.result.withdrawable_amount) == pytest.approx(withdrawable_python[1], abs=1e-3)

    starknet_service.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp2, gas_price=starknet_service.state.state.block_info.gas_price,
        sequencer_address=starknet_service.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ### Open orders to set price ###

    # List of users
    users = [felix, gary]
    users_test = [felix_test, gary_test]

    # Sufficient balance for users
    felix_balance = 250
    gary_balance = 250
    balance_array = [felix_balance, gary_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 98

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 98,
        "order_type": order_types["limit"],
        "leverage": 1
    }, {
        "quantity": 1,
        "price": 98,
        "leverage": 1,
        "direction": order_direction["short"],
    }]

    # execute order
    (batch_id_1, _, info) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, timestamp=timestamp2)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)

    withdrawable_starknet = await alice.get_safe_amount_to_withdraw(AssetID.USDC).call()
    withdrawable_python = get_safe_amount_to_withdraw_python(alice_test, python_liquidator, python_executor, AssetID.USDC, timestamp2)

    assert from64x61(withdrawable_starknet.result.safe_withdrawal_amount) == pytest.approx(withdrawable_python[0], abs=1e-3)
    assert from64x61(withdrawable_starknet.result.withdrawable_amount) == pytest.approx(withdrawable_python[1], abs=1e-3)

    starknet_service.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp3, gas_price=starknet_service.state.state.block_info.gas_price,
        sequencer_address=starknet_service.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ### Open orders to set price ###

    # List of users
    users = [felix, gary]
    users_test = [felix_test, gary_test]

    # Sufficient balance for users
    felix_balance = 600
    gary_balance = 600
    balance_array = [felix_balance, gary_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 91

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 91,
        "order_type": order_types["limit"],
        "leverage": 1
    }, {
        "quantity": 1,
        "price": 91,
        "leverage": 1,
        "direction": order_direction["short"],
    }]

    # execute order
    (batch_id_1, _, info) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, timestamp=timestamp3)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)

    withdrawable_starknet = await alice.get_safe_amount_to_withdraw(AssetID.USDC).call()
    withdrawable_python = get_safe_amount_to_withdraw_python(alice_test, python_liquidator, python_executor, AssetID.USDC, timestamp3)

    assert from64x61(withdrawable_starknet.result.safe_withdrawal_amount) == pytest.approx(withdrawable_python[0], abs=1e-3)
    assert from64x61(withdrawable_starknet.result.withdrawable_amount) == pytest.approx(withdrawable_python[1], abs=1e-3)

    starknet_service.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp4, gas_price=starknet_service.state.state.block_info.gas_price,
        sequencer_address=starknet_service.state.state.block_info.sequencer_address,
        starknet_version=STARKNET_VERSION
    )

    ### Open orders to set price ###

    # List of users
    users = [felix, gary]
    users_test = [felix_test, gary_test]

    # Sufficient balance for users
    felix_balance = 600
    gary_balance = 600
    balance_array = [felix_balance, gary_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 1
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 85

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 85,
        "order_type": order_types["limit"],
        "leverage": 1
    }, {
        "quantity": 1,
        "price": 85,
        "leverage": 1,
        "direction": order_direction["short"],
    }]

    # execute order
    (batch_id_1, complete_orders_1, info) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, timestamp=timestamp4)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)
    print("events:", info.call_info.internal_calls[0])
    # assert_event_with_custom_keys_emitted(
    #     tx_exec_info=info,
    #     from_address=felix.contract_address,
    #     keys=[str_to_felt('trade')],
    #     data=[complete_orders_1[0]["order_id"], #order_id
    #           market_id_1, #market_id
    #           order_direction["long"], #request.direction
    #           to64x61(1), #size
    #           order_types["limit"], #request.order_type
    #           side["buy"], #request.side
    #           to64x61(85), #execution_price
    #           0, #pnl
    #           1, #side
    #           0, #opening_fee
    #           1 #is_final
    #           ],
    #     order=6
    # )
    print("orders:", complete_orders_1)
    assert_event_with_custom_keys_emitted(
        tx_exec_info=info,
        from_address=gary.contract_address,
        keys=[str_to_felt('trade')],
        data=[complete_orders_1[1]["order_id"], #order_id
              market_id_1, #market_id
              order_direction["short"], #request.direction
              to64x61(1), #size
              order_types["market"], #request.order_type
              side["buy"], #request.side
              to64x61(85), #execution_price
              3618502788666131213697322783095070105623107215331596699972996997757817185996, #pnl
              2, #side
              3618502788666131213697322783095070105623107215331596699972996997757817185996, #opening_fee
              1 #is_final
              ],
        order=10
    )

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)

    withdrawable_starknet = await alice.get_safe_amount_to_withdraw(AssetID.USDC).call()
    print("starknet: ", withdrawable_starknet.result)
    withdrawable_python = get_safe_amount_to_withdraw_python(alice_test, python_liquidator, python_executor, AssetID.USDC, timestamp4)
    print("python: ", withdrawable_python)

    assert from64x61(withdrawable_starknet.result.safe_withdrawal_amount) == pytest.approx(withdrawable_python[0], abs=1e-3)
    assert from64x61(withdrawable_starknet.result.withdrawable_amount) == pytest.approx(withdrawable_python[1], abs=1e-3)


@ pytest.mark.asyncio
async def test_closing_more_than_parent_size_should_pass(trading_test_initializer):
    starknet_service, python_executor, admin1, _, alice, bob, charlie, _, eduard, felix, gary, alice_test, bob_test, charlie_test, eduard_test, felix_test, gary_test, _, _, _, trading, _, _, holding, fee_balance, liquidity, insurance, trading_stats, python_liquidator = trading_test_initializer
    
    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [charlie, eduard]
    users_test = [charlie_test, eduard_test]

    # Sufficient balance for users
    charlie_balance = 10000
    eduard_balance = 10000
    balance_array = [charlie_balance, eduard_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 3
    market_id_1 = ETH_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 3,
        "order_type": order_types["limit"],
        "market_id": ETH_USD_ID,
    }, {
        "quantity": 3,
        "direction": order_direction["short"],
        "market_id": ETH_USD_ID,
    }]

    # execute order
    (batch_id_1, _, _) = await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, timestamp=timestamp4, is_reverted=0, error_code=0)
    await check_batch_status(batch_id=batch_id_1, trading=trading, is_executed=1)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    # compare margins
    await compare_margin_info(user=charlie, user_test=charlie_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp4)
    await compare_margin_info(user=eduard, user_test=eduard_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp4)

    ###################
    ### Close orders ##
    ###################
    # Batch params for OPEN orders
    quantity_locked_2 = 4
    oracle_price_2 = 1000

    # Create orders
    orders_2 = [{
        "quantity": 4,
        "side": side["sell"],
        "order_type": order_types["limit"],
        "market_id": ETH_USD_ID,
    }, {
        "quantity": 4,
        "direction": order_direction["short"],
        "side": side["sell"],
        "market_id": ETH_USD_ID,
    }]

    error_at_index = 0
    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_1, oracle_price=oracle_price_2, trading=trading, timestamp=timestamp4, is_reverted=0)

    # compare margins
    await compare_margin_info(user=charlie, user_test=charlie_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp4)
    await compare_margin_info(user=eduard, user_test=eduard_test, order_executor=python_executor, collateral_id=asset_id_1, timestamp=timestamp4)
