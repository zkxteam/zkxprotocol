from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import ContractIndex, ManagerAction, Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, print_parsed_positions, print_parsed_collaterals, felt_to_str
from utils_trading import User, order_direction, order_types, order_time_in_force, order_side, order_life_cycles, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, Liquidator, get_user_balance
from utils_links import DEFAULT_LINK_1, prepare_starknet_string
from utils_asset import AssetID, build_asset_properties
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)
liquidator_signer = Signer(123456789987654326)
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
    alice_test = User(123456789987654323, alice.contract_address)
    print(alice.contract_address)

    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    bob_test = User(123456789987654324, bob.contract_address)
    print(bob.contract_address)

    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)
    charlie_test = User(123456789987654325, charlie.contract_address)

    daniel = await account_factory.deploy_ZKX_account(daniel_signer.public_key)
    eduard = await account_factory.deploy_ZKX_account(eduard_signer.public_key)

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

    UST_properties = build_asset_properties(
        id=AssetID.UST,
        short_name=str_to_felt("UST"),
        asset_version=0,
        is_tradable=0,
        is_collateral=1,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', UST_properties)

    # Update collateral prices
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.USDC, to64x61(1)])
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [AssetID.UST, to64x61(1)])

    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USD_ID, AssetID.BTC, AssetID.USDC, to64x61(10), 1, 0, 10, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), to64x61(0.075), 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [ETH_USD_ID, AssetID.ETH, AssetID.USDC, to64x61(10), 1, 0, 10, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), to64x61(0.075), 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))

    # Fund the Holding contract
    # Fund the Holding contract
    python_executor.set_fund_balance(
        fund=fund_mapping["holding_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    # Fund the Liquidity fund contract
    python_executor.set_fund_balance(
        fund=fund_mapping["liquidity_fund"], asset_id=AssetID.USDC, new_balance=1000000)
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidityFund.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    # Set the balance of admin1 and admin2
    # await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [AssetID.USDC, to64x61(1000000)])
    # await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [AssetID.USDC, to64x61(1000000)])

    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund, alice_test, bob_test, charlie_test, python_executor, python_liquidator


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_1(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund,  alice_test, bob_test, charlie_test, python_executor, python_liquidator = adminAuth_factory

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

    alice_balance_usdc = await get_user_balance(alice, AssetID.USDC)
    print("alice_balance", alice_balance_usdc)

    bob_balance_usdc = await get_user_balance(bob, AssetID.USDC)
    print("bob_balance", bob_balance_usdc)
    # Create orders
    orders_1 = [{
        "quantity": 2,
        "price": 5000,
        "order_type": order_types["limit"],
        "leverage": 2,
    }, {
        "quantity": 2,
        "direction": order_direction["short"],
        "side": order_side["taker"],
        "leverage": 2,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_message=0)

    alice_balance_usdc = await get_user_balance(alice, AssetID.USDC)
    print("alice_balance", alice_balance_usdc)

    bob_balance_usdc = await get_user_balance(bob, AssetID.USDC)
    print("bob_balance", bob_balance_usdc)

    orderState1 = await alice.get_position_data(market_id_=market_id_1, direction_=order_direction["short"]).call()
    res1 = list(orderState1.result.res)

    print(orderState1)

    orderState2 = await bob.get_position_data(market_id_=market_id_1, direction_=order_direction["long"]).call()
    res2 = list(orderState2.result.res)

    print(orderState2)

    ##############################################
    ######## Alice's liquidation result 1 ##########
    ##############################################

    liquidate_result_alice = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        alice.contract_address,
        # 1 Position + 2 Collaterals
        3,
        # Position 1 - BTC short
        AssetID.BTC,
        AssetID.USDC,
        to64x61(5000),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        AssetID.USDC,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        AssetID.UST,
        0,
        to64x61(0.05)
    ])
    print("liquidation resul...", liquidate_result_alice.call_info.retdata[1], " ",
          liquidate_result_alice.call_info.retdata[2])
    print(liquidate_result_alice.call_info.retdata)

    assert liquidate_result_alice.call_info.retdata[1] == 0
    assert liquidate_result_alice.call_info.retdata[4:] == res1

    alice_balance_usdc = await alice.get_balance(AssetID.USDC).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    assert from64x61(alice_balance_usdc.result.res) == 495.15

    alice_balance_ust = await alice.get_balance(AssetID.UST).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 787.5

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    # assert from64x61(alice_acc_value.result.res) == 5819.9075

    ##############################################
    ######## Bob's liquidation result 1 ##########
    ##############################################

    liquidate_result_bob = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        bob.contract_address,
        # 1 Position + 2 Collaterals
        3,
        # Position 1 - BTC long
        AssetID.BTC,
        AssetID.USDC,
        to64x61(5000),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        AssetID.USDC,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        AssetID.UST,
        0,
        to64x61(0.05)
    ])

    print("liquidation resul...", liquidate_result_bob.call_info.retdata[1],
          liquidate_result_bob.call_info.retdata[2])

    assert liquidate_result_bob.call_info.retdata[1] == 0
    print(liquidate_result_bob.call_info.retdata[4:]) == res2

    bob_balance_usdc = await bob.get_balance(AssetID.USDC).call()
    print("Bob usdc balance is...", from64x61(bob_balance_usdc.result.res))

    assert from64x61(bob_balance_usdc.result.res) == 998.0600000000001

    bob_balance_ust = await bob.get_balance(AssetID.UST).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintenance = await liquidate.return_maintenance().call()
    print("Bob maintenance requirement:",
          from64x61(bob_maintenance.result.res))

    assert from64x61(bob_maintenance.result.res) == 787.5

    bob_acc_value = await liquidate.return_acc_value().call()
    print("bob acc value:", from64x61(bob_acc_value.result.res))

    # assert from64x61(bob_acc_value.result.res) == 6572.963000000001

    # ###### Opening of Orders 2 #######
    # Batch params for OPEN orders 2
    quantity_locked_2 = 3
    market_id_2 = ETH_USD_ID
    asset_id_2 = AssetID.USDC
    oracle_price_2 = 100

    orders_1 = [{
        "quantity": 3,
        "market_id": ETH_USD_ID,
        "price": 100,
        "order_type": order_types["limit"],
        "leverage": 3,
    }, {
        "quantity": 3,
        "market_id": ETH_USD_ID,
        "side": order_side["taker"],
        "direction": order_direction["short"],
        "leverage": 3,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_2, market_id=market_id_2, oracle_price=oracle_price_2, trading=trading, is_reverted=0, error_message=0)

    orderState3 = await alice.get_position_data(market_id_=market_id_2, direction_=order_direction["short"]).call()
    res3 = list(orderState3.result.res)

    orderState4 = await bob.get_position_data(market_id_=market_id_2, direction_=order_direction["long"]).call()
    res4 = list(orderState4.result.res)

    print("Alice positions: ")
    alice_positions = await alice.get_positions().call()
    alice_parsed_positions = list(alice_positions.result.positions_array)
    print_parsed_positions(alice_parsed_positions)

    print("Bob positions: ")
    bob_positions = await alice.get_positions().call()
    bob_parsed_positions = list(bob_positions.result.positions_array)
    print_parsed_positions(bob_parsed_positions)

    print("Alice collaterals :")
    alice_collaterals = await alice.return_array_collaterals().call()
    alice_collaterals_parsed = list(alice_collaterals.result.array_list)
    print_parsed_collaterals(alice_collaterals_parsed)

    print("Bob collaterals :")
    bob_collaterals = await bob.return_array_collaterals().call()
    bob_collaterals_parsed = list(bob_collaterals.result.array_list)
    print_parsed_collaterals(bob_collaterals_parsed)

    # ##############################################
    # ######## Alice's liquidation result 2 ##########
    # ##############################################

    liquidate_result_alice = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        alice.contract_address,
        # 2 Position + 2 Collaterals
        4,
        # Position 1 - BTC short
        AssetID.BTC,
        AssetID.USDC,
        to64x61(5000),
        to64x61(1.05),
        # Position 2 - ETH short
        AssetID.ETH,
        AssetID.USDC,
        to64x61(100),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        AssetID.USDC,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        AssetID.UST,
        0,
        to64x61(0.05)
    ])
    print("liquidation resul...", liquidate_result_alice.call_info.retdata[1], " ",
          liquidate_result_alice.call_info.retdata[2])

    assert liquidate_result_alice.call_info.retdata[1] == 0
    assert liquidate_result_alice.call_info.retdata[4:] == res3

    alice_balance_usdc = await alice.get_balance(AssetID.USDC).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    assert from64x61(alice_balance_usdc.result.res) == 395.0045

    alice_balance_ust = await alice.get_balance(AssetID.UST).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    assert from64x61(alice_maintenance.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    # assert from64x61(alice_acc_value.result.res) == 5819.754725000001

    ##############################################
    ######## Bob's liquidation result 2 ##########
    ##############################################
    liquidate_result_bob = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        bob.contract_address,
        # 2 Position + 2 Collaterals
        4,
        # Position 1 - BTC long
        AssetID.BTC,
        AssetID.USDC,
        to64x61(5000),
        to64x61(1.05),
        # Position 2 - ETH long
        AssetID.ETH,
        AssetID.USDC,
        to64x61(100),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        AssetID.USDC,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        AssetID.UST,
        0,
        to64x61(0.05)
    ])

    print("liquidation resul...", liquidate_result_bob.call_info.retdata[1],
          liquidate_result_bob.call_info.retdata[2])

    assert liquidate_result_bob.call_info.retdata[1] == 0
    assert liquidate_result_alice.call_info.retdata[4:] == res4

    bob_balance_usdc = await bob.get_balance(AssetID.USDC).call()
    print("Bob usdc balance is...", from64x61(bob_balance_usdc.result.res))

    assert from64x61(bob_balance_usdc.result.res) == 898.0018

    bob_balance_ust = await bob.get_balance(AssetID.UST).call()
    print("Bob ust balance is...", from64x61(bob_balance_ust.result.res))

    assert from64x61(bob_balance_ust.result.res) == 5500

    bob_maintenance = await liquidate.return_maintenance().call()
    print("Bob maintenance requirement:",
          from64x61(bob_maintenance.result.res))

    assert from64x61(bob_maintenance.result.res) == 811.125

    bob_acc_value = await liquidate.return_acc_value().call()
    print("bob acc value:", from64x61(bob_acc_value.result.res))

    # assert from64x61(bob_acc_value.result.res) == 6572.90189


@pytest.mark.asyncio
async def test_should_calculate_correct_liq_ratio_2(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund,  alice_test, bob_test, charlie_test, python_executor, python_liquidator = adminAuth_factory

    ##############################################
    ######## Alice's liquidation result 3 ##########
    ##############################################

    liquidate_result_alice = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
        alice.contract_address,
        # 2 Position + 2 Collaterals
        4,
        # Position 1 - BTC short
        AssetID.BTC,
        AssetID.USDC,
        to64x61(8000.5),
        to64x61(1.05),
        # Position 2 - ETH short
        AssetID.ETH,
        AssetID.USDC,
        to64x61(100),
        to64x61(1.05),
        # Collateral 1 - USDC
        0,
        AssetID.USDC,
        0,
        to64x61(1.05),
        # Collateral 2 - UST
        0,
        AssetID.UST,
        0,
        to64x61(0.05)
    ])
    # print("liquidation result alice liquidated...", liquidate_result_alice.call_info.retdata[1], " ",
    #       liquidate_result_alice.call_info.retdata[2])

    # assert liquidate_result_alice.call_info.retdata[1] == 1
    # assert liquidate_result_alice.call_info.retdata[2] == BTC_USD_ID
    # assert liquidate_result_alice.call_info.retdata[3] == 0

    alice_balance_usdc = await alice.get_balance(AssetID.USDC).call()
    print("Alice usdc balance is...", from64x61(alice_balance_usdc.result.res))

    # assert from64x61(alice_balance_usdc.result.res) == 395.0045

    alice_balance_ust = await alice.get_balance(AssetID.UST).call()
    print("Alice ust balance is...", from64x61(alice_balance_ust.result.res))

    # assert from64x61(alice_balance_ust.result.res) == 1000

    alice_maintenance = await liquidate.return_maintenance().call()
    print("Alice maintenance requirement:",
          from64x61(alice_maintenance.result.res))

    # assert from64x61(alice_maintenance.result.res) == 811.125

    alice_acc_value = await liquidate.return_acc_value().call()
    print("Alice acc value:", from64x61(alice_acc_value.result.res))

    pnls = await liquidate.return_position_value(index=1).call()
    print("Alice pnl value:", from64x61(pnls.result.res))

    pnls = await liquidate.return_position_value(index=2).call()
    print("Alice pnl value:", from64x61(pnls.result.res))

    # assert from64x61(alice_acc_value.result.res) == -481.295275

    orderState1 = await alice.get_deleveragable_or_liquidatable_position().call()
    res1 = orderState1.result.position
    # assert res1.market_id == liquidate_result_alice.call_info.retdata[2]
    # assert res1.direction == liquidate_result_alice.call_info.retdata[3]


# @pytest.mark.asyncio
# async def test_liquidation_flow(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

#     charlie_usdc = to64x61(8000)
#     await admin2_signer.send_transaction(admin2, charlie.contract_address, 'set_balance', [AssetID.USDC, charlie_usdc])

#     insurance_balance_before = await insuranceFund.balance(asset_id_=AssetID.USDC).call()
#     print("insurance balance before:", from64x61(
#         insurance_balance_before.result.amount))

#     alice_curr_balance_before = await alice.get_balance(AssetID.USDC).call()
#     print("alice balance before:", from64x61(
#         alice_curr_balance_before.result.res))

#     ####### Liquidation Order 1#######
#     size = to64x61(2)
#     marketID_1 = BTC_USD_ID

#     order_id_1 = str_to_felt("0jfds78324sjxz")
#     assetID_1 = AssetID.BTC
#     collateralID_1 = AssetID.USDC
#     price1 = to64x61(7357.5)
#     stopPrice1 = 0
#     orderType1 = 3
#     position1 = to64x61(2)
#     direction1 = 1
#     closeOrder1 = 1
#     leverage1 = to64x61(1)
#     liquidatorAddress1 = liquidator.contract_address

#     order_id_2 = str_to_felt("sadfjkh2178")
#     assetID_2 = AssetID.BTC
#     collateralID_2 = AssetID.USDC
#     price2 = to64x61(7357.5)
#     stopPrice2 = 0
#     orderType2 = 0
#     position2 = to64x61(2)
#     direction2 = 0
#     closeOrder2 = 0
#     leverage2 = to64x61(2)
#     liquidatorAddress2 = 0

#     execution_price1 = to64x61(7357.5)

#     hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
#                                 price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
#     hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
#                                 price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

#     signed_message1 = liquidator_signer.sign(hash_computed1)
#     signed_message2 = charlie_signer.sign(hash_computed2)

#     diff1 = to64x61(5000) - execution_price1

#     pnl1 = await fixed_math.Math64x61_mul(diff1, size).call()
#     net_acc_value = pnl1.result.res + to64x61(5000)
#     print("Alice's net_acc_value: ", from64x61(net_acc_value))

#     res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
#         size,
#         execution_price1,
#         marketID_1,
#         2,
#         alice.contract_address, signed_message1[0], signed_message1[
#             1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 1,
#         charlie.contract_address, signed_message2[0], signed_message2[
#             1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 0,
#     ])

#     orderState1 = await alice.get_position_data(market_id_=marketID_1, direction_=0).call()
#     res1 = list(orderState1.result.res)

#     assert res1 == [
#         to64x61(5000),
#         0,
#         to64x61(0),
#         to64x61(0),
#         to64x61(2)
#     ]

#     orderState2 = await charlie.get_position_data(market_id_=marketID_1, direction_=direction2).call()
#     res2 = list(orderState2.result.res)
#     print(res2)

#     assert res2 == [
#         execution_price1,
#         position2,
#         to64x61(7357.5),
#         to64x61(7357.5),
#         leverage2
#     ]

#     print("Alice positions: ")
#     alice_positions = await alice.get_positions().call()
#     alice_parsed_positions = list(alice_positions.result.positions_array)
#     print_parsed_positions(alice_parsed_positions)

#     insurance_balance = await insuranceFund.balance(asset_id_=AssetID.USDC).call()
#     print("insurance balance after:", from64x61(
#         insurance_balance.result.amount))

#     alice_curr_balance = await alice.get_balance(AssetID.USDC).call()
#     print("alice balance after", from64x61(alice_curr_balance.result.res))

#     assert from64x61(insurance_balance.result.amount) == from64x61(
#         net_acc_value)
#     assert alice_curr_balance.result.res == alice_curr_balance_before.result.res


# @pytest.mark.asyncio
# async def test_liquidation_flow_underwater(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

#     ##############################################
#     ######## Charlie's liquidation result 1 ##########
#     ##############################################

#     liquidate_result_charlie = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
#         charlie.contract_address,
#         # 1 Position + 1 Collateral
#         2,
#         # Position 1 - BTC short
#         AssetID.BTC,
#         AssetID.USDC,
#         to64x61(11500),
#         to64x61(1.05),
#         # Collateral 1 - USDC
#         0,
#         AssetID.USDC,
#         0,
#         to64x61(1.05),
#     ])
#     print("liquidation result of charlie...",
#           liquidate_result_charlie.call_info.retdata[1], " ", liquidate_result_charlie.call_info.retdata[2])

#     assert liquidate_result_charlie.call_info.retdata[1] == 1
#     assert liquidate_result_charlie.call_info.retdata[2] == BTC_USD_ID
#     assert liquidate_result_charlie.call_info.retdata[3] == 0

#     charlie_balance_usdc = await charlie.get_balance(AssetID.USDC).call()
#     print("Charlie usdc balance is...", from64x61(
#         charlie_balance_usdc.result.res))

#     assert from64x61(charlie_balance_usdc.result.res) == 639.64529

#     charlie_maintenance = await liquidate.return_maintenance().call()
#     print("Charlie maintenance requirement:",
#           from64x61(charlie_maintenance.result.res))

#     assert from64x61(charlie_maintenance.result.res) == 1158.80625

#     charlie_acc_value = await liquidate.return_acc_value().call()
#     print("Charlie acc value:", from64x61(charlie_acc_value.result.res))

#     assert from64x61(charlie_acc_value.result.res) == -302.2474455

#     ###################

#     alice_usdc = to64x61(13000)
#     await admin2_signer.send_transaction(admin2, alice.contract_address, 'set_balance', [AssetID.USDC, alice_usdc])

#     await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])

#     insurance_balance_before = await insuranceFund.balance(asset_id_=AssetID.USDC).call()
#     print("insurance balance before:", from64x61(
#         insurance_balance_before.result.amount))

#     charlie_curr_balance_before = await charlie.get_balance(AssetID.USDC).call()
#     print("charlie balance before:", from64x61(
#         charlie_curr_balance_before.result.res))

#     ####### Liquidation Order 2#######
#     size = to64x61(2)
#     marketID_1 = BTC_USD_ID

#     order_id_1 = str_to_felt("3j432gsd8324sjxz")
#     assetID_1 = AssetID.BTC
#     collateralID_1 = AssetID.USDC
#     price1 = to64x61(11500)
#     stopPrice1 = 0
#     orderType1 = 3
#     position1 = to64x61(2)
#     direction1 = 1
#     closeOrder1 = 1
#     leverage1 = to64x61(2)
#     liquidatorAddress1 = liquidator.contract_address

#     order_id_2 = str_to_felt("5489sdksjkh2178")
#     assetID_2 = AssetID.BTC
#     collateralID_2 = AssetID.USDC
#     price2 = to64x61(11500)
#     stopPrice2 = 0
#     orderType2 = 0
#     position2 = to64x61(2)
#     direction2 = 0
#     closeOrder2 = 0
#     parentOrder2 = 0
#     leverage2 = to64x61(2)
#     liquidatorAddress2 = 0

#     execution_price1 = to64x61(11500)

#     hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
#                                 price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
#     hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
#                                 price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

#     signed_message1 = liquidator_signer.sign(hash_computed1)
#     signed_message2 = alice_signer.sign(hash_computed2)

#     diff1 = to64x61(7357.5) - execution_price1

#     adjusted_price1 = to64x61(7357.5 + from64x61(diff1))
#     leveraged_amount_out1 = await fixed_math.Math64x61_mul(adjusted_price1, size).call()
#     value_to_be_returned1 = to64x61(7357.5) - leveraged_amount_out1.result.res

#     res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
#         size,
#         execution_price1,
#         marketID_1,
#         2,
#         charlie.contract_address, signed_message1[0], signed_message1[
#             1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 1,
#         alice.contract_address, signed_message2[0], signed_message2[
#             1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 0,
#     ])

#     orderState1 = await charlie.get_position_data(market_id_=marketID_1, direction_=0).call()
#     res1 = list(orderState1.result.res)
#     assert res1 == [
#         to64x61(7357.5),
#         0,
#         to64x61(0),
#         to64x61(0),
#         leverage1
#     ]

#     orderState2 = await alice.get_position_data(market_id_=marketID_1, direction_=direction2).call()
#     res2 = list(orderState2.result.res)
#     assert res2 == [
#         execution_price1,
#         position2,
#         to64x61(11500),
#         to64x61(11500),
#         leverage2
#     ]

#     print("Alice positions: ")
#     alice_positions = await alice.get_positions().call()
#     alice_parsed_positions = list(alice_positions.result.positions_array)
#     print_parsed_positions(alice_parsed_positions)

#     insurance_balance = await insuranceFund.balance(asset_id_=AssetID.USDC).call()
#     print("insurance balance after:", from64x61(
#         insurance_balance.result.amount))

#     charlie_curr_balance = await charlie.get_balance(AssetID.USDC).call()
#     print("charlie balance after", from64x61(charlie_curr_balance.result.res))

#     assert charlie_curr_balance.result.res == to64x61(0)


# # @pytest.mark.asyncio
# # async def test_deleveraging_flow(adminAuth_factory):
# #     adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

# #     await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])

# #     eduard_usdc = to64x61(1500)
# #     await admin2_signer.send_transaction(admin2, eduard.contract_address, 'set_balance', [AssetID.USDC, eduard_usdc])

# #     daniel_usdc = to64x61(5500)
# #     await admin2_signer.send_transaction(admin2, daniel.contract_address, 'set_balance', [AssetID.USDC, daniel_usdc])

# #     insurance_balance_before = await insuranceFund.balance(asset_id_=AssetID.USDC).call()
# #     print("insurance balance before:", from64x61(
# #         insurance_balance_before.result.amount))

# #     ####### Opening of Orders #######
# #     size = to64x61(5)
# #     marketID_1 = BTC_USD_ID

# #     order_id_1 = str_to_felt("343uofdsjxz")
# #     assetID_1 = AssetID.BTC
# #     collateralID_1 = AssetID.USDC
# #     price1 = to64x61(1000)
# #     stopPrice1 = 0
# #     orderType1 = 0
# #     position1 = to64x61(5)
# #     direction1 = 0
# #     closeOrder1 = 0
# #     leverage1 = to64x61(5)
# #     liquidatorAddress1 = 0

# #     order_id_2 = str_to_felt("wer4iljemn")
# #     assetID_2 = AssetID.BTC
# #     collateralID_2 = AssetID.USDC
# #     price2 = to64x61(1000)
# #     stopPrice2 = 0
# #     orderType2 = 0
# #     position2 = to64x61(5)
# #     direction2 = 1
# #     closeOrder2 = 0
# #     leverage2 = to64x61(1)
# #     liquidatorAddress2 = 0

# #     execution_price1 = to64x61(1000)

# #     hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
# #                                 price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
# #     hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
# #                                 price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

# #     signed_message1 = eduard_signer.sign(hash_computed1)
# #     signed_message2 = daniel_signer.sign(hash_computed2)

# #     res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
# #         size,
# #         execution_price1,
# #         marketID_1,
# #         2,
# #         eduard.contract_address, signed_message1[0], signed_message1[
# #             1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
# #         daniel.contract_address, signed_message2[0], signed_message2[
# #             1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
# #     ])

# #     orderState1 = await eduard.get_position_data(market_id_=marketID_1, direction_=direction1).call()
# #     res1 = list(orderState1.result.res)

# #     assert res1 == [
# #         execution_price1,
# #         position1,
# #         to64x61(1000),
# #         to64x61(4000),
# #         leverage1
# #     ]

# #     orderState2 = await daniel.get_position_data(market_id_=marketID_1, direction_=direction2).call()
# #     res2 = list(orderState2.result.res)

# #     assert res2 == [
# #         execution_price1,
# #         position2,
# #         to64x61(5000),
# #         to64x61(0),
# #         leverage2
# #     ]

# #     print("Eduard positions: ")
# #     eduard_positions = await eduard.get_positions().call()
# #     eduard_parsed_positions = list(eduard_positions.result.positions_array)
# #     print_parsed_positions(eduard_parsed_positions)

# #     print("Daniel positions: ")
# #     daniel_positions = await daniel.get_positions().call()
# #     daniel_parsed_positions = list(daniel_positions.result.positions_array)
# #     print_parsed_positions(daniel_parsed_positions)

# #     eduard_list_collaterals = await eduard.return_array_collaterals().call()
# #     eduard_list_collaterals_parsed = list(
# #         eduard_list_collaterals.result.array_list)

# #     print("eduard collaterals :", eduard_list_collaterals_parsed)

# #     daniel_list_collaterals = await daniel.return_array_collaterals().call()
# #     daniel_list_collaterals_parsed = list(
# #         daniel_list_collaterals.result.array_list)

# #     print("Daniel collaterals :", daniel_list_collaterals_parsed)

# #     eduard_balance_usdc = await eduard.get_balance(AssetID.USDC).call()
# #     print("eduard usdc balance is...", from64x61(
# #         eduard_balance_usdc.result.res))

# #     assert from64x61(eduard_balance_usdc.result.res) == 499.03000000000003

# #     daniel_balance_usdc = await daniel.get_balance(AssetID.USDC).call()
# #     print("Daniel usdc balance is...", from64x61(
# #         daniel_balance_usdc.result.res))

# #     assert from64x61(daniel_balance_usdc.result.res) == 497.575

# #     ##############################################
# #     ######## Check for deleveraging ##########
# #     ##############################################

# #     liquidate_result_eduard = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
# #         eduard.contract_address,
# #         # 1 Position + 1 Collateral
# #         2,
# #         # Position 1 - BTC short
# #         AssetID.BTC,
# #         AssetID.USDC,
# #         to64x61(1250),
# #         to64x61(1.05),
# #         # Collateral 1 - USDC
# #         0,
# #         AssetID.USDC,
# #         0,
# #         to64x61(1.05),
# #     ])
# #     print("liquidation result of eduard...",
# #           liquidate_result_eduard.call_info.retdata[1], " ", liquidate_result_eduard.call_info.retdata[2])

# #     assert liquidate_result_eduard.call_info.retdata[1] == 1
# #     assert liquidate_result_eduard.call_info.retdata[2] == marketID_1
# #     assert liquidate_result_eduard.call_info.retdata[3] == direction1

# #     eduard_maintenance = await liquidate.return_maintenance().call()
# #     print("eduard maintenance requirement:",
# #           from64x61(eduard_maintenance.result.res))

# #     assert from64x61(eduard_maintenance.result.res) == 393.75

# #     eduard_acc_value = await liquidate.return_acc_value().call()
# #     print("eduard acc value:", from64x61(eduard_acc_value.result.res))

# #     assert from64x61(eduard_acc_value.result.res) == 261.48150000000004

# #     eduard_amount_to_be_sold = await eduard.get_deleveragable_or_liquidatable_position().call()
# #     eduard_position = eduard_amount_to_be_sold.result.position
# #     print(eduard_position.amount_to_be_sold)
# #     print("eduard amount to be sold is...", from64x61(
# #         eduard_position.amount_to_be_sold))
# #     assert from64x61(eduard_position.amount_to_be_sold) == 1.9454545454545453

# #     ####### Opening of Deleveraged Order #######
# #     size2 = 4485912763379367865
# #     assert eduard_position.amount_to_be_sold == size2
# #     marketID_2 = BTC_USD_ID

# #     order_id_3 = str_to_felt("343uofdsswa")
# #     assetID_3 = AssetID.BTC
# #     collateralID_3 = AssetID.USDC
# #     price3 = to64x61(1250)
# #     stopPrice3 = 0
# #     orderType3 = 4
# #     position3 = 4485912763379367865
# #     direction3 = 1
# #     closeOrder3 = 1
# #     leverage3 = to64x61(5)
# #     liquidatorAddress3 = liquidator.contract_address

# #     order_id_4 = str_to_felt("rfdgljthi")
# #     assetID_4 = AssetID.BTC
# #     collateralID_4 = AssetID.USDC
# #     price4 = to64x61(1250)
# #     stopPrice4 = 0
# #     orderType4 = 0
# #     position4 = 4485912763379367865
# #     direction4 = 0
# #     closeOrder4 = 1
# #     leverage4 = to64x61(1)
# #     liquidatorAddress4 = 0

# #     execution_price2 = to64x61(1250)

# #     hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
# #                                 price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
# #     hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
# #                                 price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

# #     signed_message3 = liquidator_signer.sign(hash_computed3)
# #     signed_message4 = daniel_signer.sign(hash_computed4)

# #     res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
# #         size2,
# #         execution_price2,
# #         marketID_2,
# #         2,
# #         eduard.contract_address, signed_message3[0], signed_message3[
# #             1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, 1,
# #         daniel.contract_address, signed_message4[0], signed_message4[
# #             1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, 0,
# #     ])

# #     orderState3 = await eduard.get_position_data(market_id_=marketID_1, direction_=0).call()
# #     res3 = list(orderState3.result.res)
# #     print("eduard result:", res3)

# #     assert res3 == [
# #         execution_price1,
# #         7043302282689101895,
# #         to64x61(1000),
# #         5858937464320249909250,
# #         8164780473533943861
# #     ]

# #     orderState4 = await daniel.get_position_data(market_id_=marketID_1, direction_=1).call()
# #     res4 = list(orderState4.result.res)
# #     print("Daniel result:", res4)

# #     assert res4 == [
# #         execution_price1,
# #         7043302282689101895,
# #         7043302282689101895000,
# #         to64x61(0),
# #         leverage4
# #     ]

# #     print("Eduard positions: ")
# #     eduard_positions = await eduard.get_positions().call()
# #     eduard_parsed_positions = list(eduard_positions.result.positions_array)
# #     print_parsed_positions(eduard_parsed_positions)

# #     print("Daniel positions: ")
# #     daniel_positions = await daniel.get_positions().call()
# #     daniel_parsed_positions = list(daniel_positions.result.positions_array)
# #     print_parsed_positions(daniel_parsed_positions)

# #     eduard_balance_usdc = await eduard.get_balance(AssetID.USDC).call()
# #     print("eduard usdc balance is...", from64x61(
# #         eduard_balance_usdc.result.res))

# #     assert from64x61(eduard_balance_usdc.result.res) == 499.03000000000003

# #     daniel_balance_usdc = await daniel.get_balance(AssetID.USDC).call()
# #     print("Daniel usdc balance is...", from64x61(
# #         daniel_balance_usdc.result.res))

# #     assert from64x61(daniel_balance_usdc.result.res) == 2929.393181818182

# #     eduard_amount_to_be_sold = await eduard.get_deleveragable_or_liquidatable_position().call()
# #     eduard_position = eduard_amount_to_be_sold.result.position
# #     assert from64x61(eduard_position.amount_to_be_sold) == 0


# # @pytest.mark.asyncio
# # async def test_liquidation_after_deleveraging_flow(adminAuth_factory):
# #     adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, daniel, eduard, liquidator, fixed_math, holding, feeBalance, liquidate, insuranceFund = adminAuth_factory

# #     await admin1_signer.send_transaction(admin1, insuranceFund.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])

# #     insurance_balance_before = await insuranceFund.balance(asset_id_=AssetID.USDC).call()
# #     print("insurance balance before:", from64x61(
# #         insurance_balance_before.result.amount))

# #     eduard_curr_balance_before = await eduard.get_balance(AssetID.USDC).call()
# #     print("eduard usdc balance before:", from64x61(
# #         eduard_curr_balance_before.result.res))

# #     daniel_curr_balance_before = await daniel.get_balance(AssetID.USDC).call()
# #     print("Daniel usdc balance before...", from64x61(
# #         daniel_curr_balance_before.result.res))

# #     ##############################################
# #     ######## Check for liquidation ##########
# #     ##############################################
# #     liquidate_result_eduard = await liquidator_signer.send_transaction(liquidator, liquidate.contract_address, "check_liquidation", [
# #         eduard.contract_address,
# #         # 1 Position + 1 Collateral
# #         2,
# #         # Position 1 - BTC short
# #         AssetID.BTC,
# #         AssetID.USDC,
# #         to64x61(1800),
# #         to64x61(1.05),
# #         # Collateral 1 - USDC
# #         0,
# #         AssetID.USDC,
# #         0,
# #         to64x61(1.05),
# #     ])
# #     print("liquidation result of eduard...",
# #           liquidate_result_eduard.call_info.retdata[1], " ", liquidate_result_eduard.call_info.retdata[2])

# #     assert liquidate_result_eduard.call_info.retdata[1] == 1

# #     eduard_maintenance = await liquidate.return_maintenance().call()
# #     print("eduard maintenance requirement:",
# #           from64x61(eduard_maintenance.result.res))

# #     assert from64x61(eduard_maintenance.result.res) == 240.54545454545456

# #     eduard_acc_value = await liquidate.return_acc_value().call()
# #     print("eduard acc value:", from64x61(eduard_acc_value.result.res))

# #     assert from64x61(eduard_acc_value.result.res) == -1502.5185000000001

# #     eduard_amount_to_be_sold = await eduard.get_deleveragable_or_liquidatable_position().call()
# #     eduard_position = eduard_amount_to_be_sold.result.position
# #     assert eduard_position.amount_to_be_sold == 7043302282689101895
# #     assert eduard_position.market_id == BTC_USD_ID
# #     assert eduard_position.direction == 0
# #     assert eduard_position.liquidatable == 1

# #     ####### Liquidation Order #######
# #     size = 7043302282689101895
# #     marketID_1 = BTC_USD_ID

# #     order_id_1 = str_to_felt("0jfds78324sjxz")
# #     assetID_1 = AssetID.BTC
# #     collateralID_1 = AssetID.USDC
# #     price1 = to64x61(1800)
# #     stopPrice1 = 0
# #     orderType1 = 3
# #     position1 = to64x61(5 - 1.9454545454545453)
# #     direction1 = 1
# #     closeOrder1 = 1
# #     parentOrder1 = str_to_felt("343uofdsjxz")
# #     leverage1 = to64x61(3.540909090909091)
# #     liquidatorAddress1 = liquidator.contract_address

# #     order_id_2 = str_to_felt("sadfjkh2178")
# #     assetID_2 = AssetID.BTC
# #     collateralID_2 = AssetID.USDC
# #     price2 = to64x61(1800)
# #     stopPrice2 = 0
# #     orderType2 = 0
# #     position2 = to64x61(5 - 1.9454545454545453)
# #     direction2 = 0
# #     closeOrder2 = 1
# #     parentOrder2 = str_to_felt("wer4iljemn")
# #     leverage2 = to64x61(1)
# #     liquidatorAddress2 = 0

# #     execution_price1 = to64x61(1800)

# #     hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
# #                                 price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
# #     hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
# #                                 price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

# #     signed_message1 = liquidator_signer.sign(hash_computed1)
# #     signed_message2 = daniel_signer.sign(hash_computed2)

# #     diff1 = to64x61(1000) - execution_price1

# #     pnl1 = await fixed_math.Math64x61_mul(diff1, size).call()
# #     net_acc_value = pnl1.result.res + to64x61(1000)

# #     res = await liquidator_signer.send_transaction(liquidator, trading.contract_address, "execute_batch", [
# #         size,
# #         execution_price1,
# #         marketID_1,
# #         2,
# #         eduard.contract_address, signed_message1[0], signed_message1[
# #             1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 1,
# #         daniel.contract_address, signed_message2[0], signed_message2[
# #             1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 0,
# #     ])

# #     orderState1 = await eduard.get_position_data(market_id_=marketID_1, direction_=0).call()
# #     res1 = list(orderState1.result.res)
# #     print(res1)
# #     print(from64x61(res1[2]))

# #     assert res1 == [
# #         to64x61(1000),
# #         71,
# #         24000,
# #         60982,
# #         8164780473533943861
# #     ]

# #     orderState2 = await daniel.get_position_data(market_id_=marketID_1, direction_=1).call()
# #     res2 = list(orderState2.result.res)
# #     print(res2)

# #     assert res2 == [
# #         to64x61(1000),
# #         71,
# #         73310,
# #         to64x61(0),
# #         2305843009213693952
# #     ]

# #     insurance_balance = await insuranceFund.balance(asset_id_=AssetID.USDC).call()
# #     print("insurance balance after:", from64x61(
# #         insurance_balance.result.amount))

# #     eduard_curr_balance = await eduard.get_balance(AssetID.USDC).call()
# #     print("eduard balance after", from64x61(eduard_curr_balance.result.res))
