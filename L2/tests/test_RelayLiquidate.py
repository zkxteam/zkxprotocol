from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, str_to_felt, from64x61, to64x61
from utils_trading import (
    User, Liquidator, OrderExecutor,
    order_direction, order_types, order_life_cycles, fund_mapping,
    set_balance, execute_and_compare, check_liquidation,
    compare_fund_balances, compare_user_balances, compare_user_positions, compare_liquidatable_position
)
from utils_links import DEFAULT_LINK_1, prepare_starknet_string
from utils_asset import AssetID, build_asset_properties
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

maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
DOGE_ID = str_to_felt("jdi2i8621hzmnc7324o")
TSLA_ID = str_to_felt("i39sk1nxlqlzcee")


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
    liquidityFund = await starknet_service.deploy(ContractType.LiquidityFund, [registry.contract_address, 1])
    trading = await starknet_service.deploy(ContractType.Trading, [registry.contract_address, 1])
    liquidate = await starknet_service.deploy(ContractType.Liquidate, [registry.contract_address, 1])
    insuranceFund = await starknet_service.deploy(ContractType.InsuranceFund, [registry.contract_address, 1])
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [registry.contract_address, 1])
    marketPrices = await starknet_service.deploy(ContractType.MarketPrices, [registry.contract_address, 1])
    collateral_prices = await starknet_service.deploy(ContractType.CollateralPrices, [registry.contract_address, 1])
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
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.CollateralPrices, 1, collateral_prices.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.AccountRegistry, 1, account_registry.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Liquidate, 1, liquidate.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.MarketPrices, 1, marketPrices.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Hightide, 1, hightide.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.TradingStats, 1, trading_stats.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.UserStats, 1, user_stats.contract_address])

    # Deploy relay contracts with appropriate indexes
    relay_trading = await starknet_service.deploy(ContractType.RelayTrading, [
        registry.contract_address,
        1,
        ContractIndex.Trading
    ])
    relay_asset = await starknet_service.deploy(ContractType.RelayAsset, [
        registry.contract_address,
        1,
        ContractIndex.Asset
    ])
    relay_holding = await starknet_service.deploy(ContractType.RelayHolding, [
        registry.contract_address,
        1,
        ContractIndex.Holding
    ])
    relay_feeBalance = await starknet_service.deploy(ContractType.RelayFeeBalance, [
        registry.contract_address,
        1,
        ContractIndex.FeeBalance
    ])
    relay_fees = await starknet_service.deploy(ContractType.RelayTradingFees, [
        registry.contract_address,
        1,
        ContractIndex.TradingFees
    ])
    relay_liquidate = await starknet_service.deploy(ContractType.RelayLiquidate, [
        registry.contract_address,
        1,
        ContractIndex.Liquidate
    ])

    # Give permissions to relays
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_trading.contract_address, ManagerAction.MasterAdmin, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, ManagerAction.ManageAssets, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_holding.contract_address, ManagerAction.ManageFunds, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_feeBalance.contract_address, ManagerAction.ManageFeeDetails, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_fees.contract_address, ManagerAction.ManageFeeDetails, True])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageCollateralPrices, True])

    # Add base fee and discount in Trading Fee contract
    base_fee_maker1 = to64x61(0.0002)
    base_fee_taker1 = to64x61(0.0005)
    await admin1_signer.send_transaction(admin1, relay_fees.contract_address, 'update_base_fees', [1, 0, base_fee_maker1, base_fee_taker1])
    base_fee_maker2 = to64x61(0.00015)
    base_fee_taker2 = to64x61(0.0004)
    await admin1_signer.send_transaction(admin1, relay_fees.contract_address, 'update_base_fees', [2, 1000, base_fee_maker2, base_fee_taker2])
    base_fee_maker3 = to64x61(0.0001)
    base_fee_taker3 = to64x61(0.00035)
    await admin1_signer.send_transaction(admin1, relay_fees.contract_address, 'update_base_fees', [3, 5000, base_fee_maker3, base_fee_taker3])
    discount1 = to64x61(0.03)
    await admin1_signer.send_transaction(admin1, relay_fees.contract_address, 'update_discount', [1, 0, discount1])
    discount2 = to64x61(0.05)
    await admin1_signer.send_transaction(admin1, relay_fees.contract_address, 'update_discount', [2, 1000, discount2])
    discount3 = to64x61(0.1)
    await admin1_signer.send_transaction(admin1, relay_fees.contract_address, 'update_discount', [3, 5000, discount3])

    # Add assets
    BTC_properties = build_asset_properties(
        id=AssetID.BTC,
        short_name=str_to_felt("BTC"),
        asset_version=0,
        is_tradable=1,
        is_collateral=0,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'add_asset', BTC_properties)

    ETH_properties = build_asset_properties(
        id=AssetID.ETH,
        short_name=str_to_felt("ETH"),
        asset_version=0,
        is_tradable=1,
        is_collateral=0,
        token_decimal=18
    )
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'add_asset', ETH_properties)

    call_counter = await relay_asset.get_call_counter(
        admin1.contract_address, str_to_felt('add_asset')
    ).call()
    assert call_counter.result.count == 2

    USDC_properties = build_asset_properties(
        id=AssetID.USDC,
        short_name=str_to_felt("USDC"),
        asset_version=0,
        is_tradable=0,
        is_collateral=1,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'add_asset', USDC_properties)

    UST_properties = build_asset_properties(
        id=AssetID.UST,
        short_name=str_to_felt("UST"),
        asset_version=0,
        is_tradable=0,
        is_collateral=1,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'add_asset', UST_properties)

    # Check RelayAsset contract
    hash_list = await relay_asset.get_caller_hash_list(admin1.contract_address).call()
    assert len(hash_list.result.hash_list) == 4

    call_counter = await relay_asset.get_call_counter(
        admin1.contract_address, str_to_felt('add_asset')
    ).call()
    assert call_counter.result.count == 4

    # Update collateral prices
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.USDC, to64x61(1)])
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.UST, to64x61(1)])

    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USD_ID, AssetID.BTC, AssetID.USDC, to64x61(10), 1, 0, 10, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), to64x61(0.075), 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [ETH_USD_ID, AssetID.ETH, AssetID.USDC, to64x61(10), 1, 0, 10, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))

    # Fund the Holding contract
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, relay_holding.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, relay_holding.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    # Fund the Liquidity fund contract
    # Fund the Liquidity fund contract
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    python_executor.set_fund_balance(
        fund=fund_mapping["insurance_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])

    # Set the threshold for oracle price in Trading contract
    await admin1_signer.send_transaction(admin1, trading.contract_address, 'set_threshold_percentage', [to64x61(5)])

    # return relay versions of fees, asset, trading, holding, feeBalance, liquidate
    return (adminAuth, relay_fees, admin1, admin2, relay_asset,
            relay_trading, alice, bob, charlie, daniel, eduard, liquidator,
            fixed_math, relay_holding, relay_feeBalance, relay_liquidate, insuranceFund,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, feeBalance, liquidityFund, eduard_test, daniel_test)


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insurance,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, fee_balance, liquidity, eduard_test, daniel_test = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [bob, alice]
    users_test = [bob_test, alice_test]

    # Collaterals
    collateral_id_1 = AssetID.USDC
    collateral_id_2 = AssetID.UST

    # Sufficient balance for users
    alice_balance_usdc = 5500
    alice_balance_ust = 1000
    bob_balance_usdc = 6000
    bob_balance_ust = 5500

    balance_array_usdc = [bob_balance_usdc, alice_balance_usdc]
    balance_array_ust = [bob_balance_ust, alice_balance_ust]

    # Batch params for OPEN orders
    quantity_locked_1 = 2
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 5000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array_usdc, asset_id=collateral_id_1)
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array_ust, asset_id=collateral_id_2)

    # Create orders
    orders_1 = [{
        "quantity": 2,
        "price": 5000,
        "order_type": order_types["limit"],
        "leverage": 2,
    }, {
        "quantity": 2,
        "price": 5000,
        "direction": order_direction["short"],
        "leverage": 2,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0)

    # compare
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)

    ##############################################
    ######## Alice's liquidation result 1 ########
    ##############################################
    market_prices_1 = [{
        "market_id": BTC_USD_ID,
        "asset_price": 5000,
        "collateral_price": 1.05
    }]

    collateral_prices_1 = [{
        "collateral_id": AssetID.USDC,
        "collateral_price": 1.05
    }, {
        "collateral_id": AssetID.UST,
        "collateral_price": 0.05
    }]

    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=alice,
                            user_test=alice_test, market_prices=market_prices_1, collateral_prices=collateral_prices_1, liquidate=liquidate)

    await compare_liquidatable_position(user=alice, user_test=alice_test)

    ##############################################
    ######## Bob's liquidation result 1 ##########
    ##############################################

    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=bob,
                            user_test=bob_test, market_prices=market_prices_1, collateral_prices=collateral_prices_1, liquidate=liquidate)
    await compare_liquidatable_position(user=bob, user_test=bob_test)

    # ###### Opening of Orders 2 #######
    # Batch params for OPEN orders 2
    quantity_locked_2 = 3
    market_id_2 = ETH_USD_ID
    asset_id_2 = AssetID.USDC
    oracle_price_2 = 100

    orders_2 = [{
        "quantity": 3,
        "market_id": ETH_USD_ID,
        "price": 100,
        "order_type": order_types["limit"],
        "leverage": 3,
    }, {
        "quantity": 3,
        "market_id": ETH_USD_ID,
        "price": 100,
        "direction": order_direction["short"],
        "leverage": 3,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_2, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0)

    # compare
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_2)
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_2)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)

    ##############################################
    ######## Alice's liquidation result 2 ########
    ##############################################

    market_prices_2 = [{
        "market_id": BTC_USD_ID,
        "asset_price": 5000,
        "collateral_price": 1.05
    }, {
        "market_id": ETH_USD_ID,
        "asset_price": 100,
        "collateral_price": 1.05
    }]

    collateral_prices_2 = [{
        "collateral_id": AssetID.USDC,
        "collateral_price": 1.05
    }, {
        "collateral_id": AssetID.UST,
        "collateral_price": 0.05
    }]

    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=alice,
                            user_test=alice_test, market_prices=market_prices_2, collateral_prices=collateral_prices_2, liquidate=liquidate)
    await compare_liquidatable_position(user=alice, user_test=alice_test)
    await compare_liquidatable_position(user=alice, user_test=alice_test)

    ##############################################
    ######## Bob's liquidation result 2 ##########
    ##############################################
    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=bob,
                            user_test=bob_test, market_prices=market_prices_2, collateral_prices=collateral_prices_2, liquidate=liquidate)
    await compare_liquidatable_position(user=bob, user_test=bob_test)


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insurance,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, fee_balance, liquidity, eduard_test, daniel_test = adminAuth_factory

    ##############################################
    ######## Alice's liquidation result 3 ########
    ##############################################

    market_prices_1 = [{
        "market_id": BTC_USD_ID,
        "asset_price": 8000.5,
        "collateral_price": 1.05
    }, {
        "market_id": ETH_USD_ID,
        "asset_price": 100,
        "collateral_price": 1.05
    }]

    collateral_prices_1 = [{
        "collateral_id": AssetID.USDC,
        "collateral_price": 1.05
    }, {
        "collateral_id": AssetID.UST,
        "collateral_price": 0.05
    }]

    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=alice,
                            user_test=alice_test, market_prices=market_prices_1, collateral_prices=collateral_prices_1, liquidate=liquidate)
    await compare_liquidatable_position(user=alice, user_test=alice_test)


@pytest.mark.asyncio
async def test_liquidation_flow(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insurance,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, fee_balance, liquidity, eduard_test, daniel_test = adminAuth_factory

    ###################
    # List of users
    users = [charlie, alice]
    users_test = [charlie_test, alice_test]

    # Sufficient balance for users
    charlie_balance = 8000
    balance_array = [charlie_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 2
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 7357.5

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=[charlie], users_test=[charlie_test], balance_array=balance_array, asset_id=asset_id_1)

    ####### Liquidation Order 1#######
    # Create orders
    orders_1 = [{
        "quantity": 2,
        "price": 7357.5,
        "leverage": 2,
        "direction": order_direction["short"],
        "order_type": order_types["limit"],
    }, {
        "quantity": 2,
        "price": 7357.5,
        "direction": order_direction["long"],
        "order_type": order_types["liquidation"],
        "liquidator_address": liquidator.contract_address,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0)

    # compare
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_liquidatable_position(user=alice, user_test=alice_test)


@pytest.mark.asyncio
async def test_liquidation_flow_underwater(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insurance,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, fee_balance, liquidity, eduard_test, daniel_test = adminAuth_factory

    ##############################################
    ######## Charlie's liquidation result 1 ######
    ##############################################
    market_prices_1 = [{
        "market_id": BTC_USD_ID,
        "asset_price": 11500,
        "collateral_price": 1.05
    }]

    collateral_prices_1 = [{
        "collateral_id": AssetID.USDC,
        "collateral_price": 1.05
    }]

    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=charlie,
                            user_test=charlie_test, market_prices=market_prices_1, collateral_prices=collateral_prices_1, liquidate=liquidate)
    await compare_liquidatable_position(user=charlie, user_test=charlie_test)

    # ####### Liquidation Order 2#######
    ###################
    # List of users
    users = [alice, charlie]
    users_test = [alice_test, charlie_test]

    # Sufficient balances for the users
    alice_balance = 13000

    # Batch params for OPEN orders
    quantity_locked_1 = 2
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 11500

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=[alice], users_test=[alice_test], balance_array=[alice_balance], asset_id=asset_id_1)

    ####### Liquidation Order 1#######
    # Create orders
    orders_1 = [{
        "quantity": 2,
        "price": 11500,
        "leverage": 2,
        "direction": order_direction["short"],
        "order_type": order_types["limit"],
    }, {
        "quantity": 2,
        "price": 11500,
        "direction": order_direction["long"],
        "order_type": order_types["liquidation"],
        "liquidator_address": liquidator.contract_address,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0)

    # compare
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_liquidatable_position(user=alice, user_test=alice_test)


@pytest.mark.asyncio
async def test_deleveraging_flow(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insurance,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, fee_balance, liquidity, eduard_test, daniel_test = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users = [eduard, daniel]
    users_test = [eduard_test, daniel_test]

    # Sufficient balance for users
    eduard_balance = 1500
    daniel_balance = 5500
    balance_array = [eduard_balance, daniel_balance]

    # Batch params for OPEN orders
    quantity_locked_1 = 5
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1000

    # Set balance in Starknet & Python
    await set_balance(admin_signer=admin1_signer, admin=admin1, users=users, users_test=users_test, balance_array=balance_array, asset_id=asset_id_1)

    # Create orders
    orders_1 = [{
        "quantity": 5,
        "price": 1000,
        "direction": order_direction["short"],
        "leverage": 5,
        "order_type": order_types["limit"],
    }, {
        "quantity": 5,
        "price": 1000,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)

    ########################################
    ######## Check for deleveraging ########
    ########################################

    market_prices_1 = [{
        "market_id": BTC_USD_ID,
        "asset_price": 1250,
        "collateral_price": 1.05
    }]

    collateral_prices_1 = [{
        "collateral_id": AssetID.USDC,
        "collateral_price": 1.05
    }]

    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=eduard,
                            user_test=eduard_test, market_prices=market_prices_1, collateral_prices=collateral_prices_1, liquidate=liquidate)
    await compare_liquidatable_position(user=eduard, user_test=eduard_test)

    ####### Opening of Deleveraged Order #######
    # List of users
    users = [daniel, eduard]
    users_test = [daniel_test, eduard_test]

    # Batch params
    quantity_locked_1 = 1.94545454
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1250

    # Create orders
    orders_1 = [{
        "quantity": 1.9454545454,
        "price": 1250,
        "order_type": order_types["limit"],
        "life_cycle": order_life_cycles["close"],
        "direction": order_direction["short"]
    }, {
        "quantity": 1.9454545454,
        "price": 1250,
        "leverage": 5,
        "order_type": order_types["deleverage"],
        "liquidator_address": liquidator.contract_address,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    # check balances
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)
    await compare_liquidatable_position(user=eduard, user_test=eduard_test)

    eduard_balance_usdc = await eduard.get_balance(AssetID.USDC).call()
    print("eduard usdc balance is...", from64x61(
        eduard_balance_usdc.result.res))

    assert from64x61(eduard_balance_usdc.result.res) == pytest.approx(
        499.03000000000003, abs=1e-3)

    daniel_balance_usdc = await daniel.get_balance(AssetID.USDC).call()
    print("Daniel usdc balance is...", from64x61(
        daniel_balance_usdc.result.res))

    assert from64x61(daniel_balance_usdc.result.res) == pytest.approx(
        2929.393181818182, abs=1e-3)

    eduard_amount_to_be_sold = await eduard.get_deleveragable_or_liquidatable_position().call()
    eduard_position = eduard_amount_to_be_sold.result.position
    assert from64x61(
        eduard_position.amount_to_be_sold) == pytest.approx(0, abs=1e-3)


@pytest.mark.asyncio
async def test_liquidation_after_deleveraging_flow(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insurance,  alice_test, bob_test, charlie_test, python_executor, python_liquidator, fee_balance, liquidity, eduard_test, daniel_test = adminAuth_factory

    ##############################################
    ######## Check for liquidation ##########
    ##############################################
    market_prices_1 = [{
        "market_id": BTC_USD_ID,
        "asset_price": 1800,
        "collateral_price": 1.05
    }]

    collateral_prices_1 = [{
        "collateral_id": AssetID.USDC,
        "collateral_price": 1.05
    }]
    await check_liquidation(zkx_node_signer=liquidator_signer, zkx_node=liquidator, liquidator=python_liquidator, user=eduard,
                            user_test=eduard_test, market_prices=market_prices_1, collateral_prices=collateral_prices_1, liquidate=liquidate)
    await compare_liquidatable_position(user=eduard, user_test=eduard_test)

    ####### Liquidation Order #######
    ###################
    # List of users
    users = [daniel, eduard]
    users_test = [daniel_test, eduard_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 3.054545454
    market_id_1 = BTC_USD_ID
    asset_id_1 = AssetID.USDC
    oracle_price_1 = 1800

    ####### Liquidation Order 1#######
    # Create orders
    orders_1 = [{
        "quantity": 3.054545454,
        "price": 1800,
        "leverage": 2,
        "direction": order_direction["short"],
        "order_type": order_types["limit"],
    }, {
        "quantity": 3.054545454,
        "price": 1800,
        "order_type": order_types["liquidation"],
        "liquidator_address": liquidator.contract_address,
        "life_cycle": order_life_cycles["close"],
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0, error_at_index=0, param_2=0)

    # compare
    await compare_user_positions(users=users, users_test=users_test, market_id=market_id_1)
    await compare_user_balances(users=users, user_tests=users_test, asset_id=asset_id_1)
    await compare_fund_balances(executor=python_executor, holding=holding, liquidity=liquidity, fee_balance=fee_balance, insurance=insurance, asset_id=asset_id_1)
    await compare_liquidatable_position(user=eduard, user_test=eduard_test)
