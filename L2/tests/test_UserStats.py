from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, print_parsed_positions, print_parsed_collaterals
from utils_links import DEFAULT_LINK_1, prepare_starknet_string
from utils_asset import AssetID, build_asset_properties
from utils_trading import User, order_direction, order_types, side, OrderExecutor, fund_mapping, set_balance, execute_and_compare, compare_fund_balances, compare_user_balances, compare_user_positions, check_batch_status
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

    # Add assets
    # await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [AssetID.BTC, 1, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1) + prepare_starknet_string(DEFAULT_LINK_2))
    # await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [AssetID.ETH, 1, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1) + prepare_starknet_string(DEFAULT_LINK_2))
    # await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [AssetID.USDC, 1, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1) + prepare_starknet_string(DEFAULT_LINK_2))
    # await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [AssetID.UST, 1, str_to_felt("UST"), str_to_felt("UST"), 1, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1) + prepare_starknet_string(DEFAULT_LINK_2))
    # await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [AssetID.DOGE, 1, str_to_felt("DOGE"), str_to_felt("DOGECOIN"), 0, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1) + prepare_starknet_string(DEFAULT_LINK_2))
    # await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [AssetID.TSLA, 1, str_to_felt("TESLA"), str_to_felt("TESLA MOTORS"), 1, 0, 1, 1, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1) + prepare_starknet_string(DEFAULT_LINK_2))

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USD_ID, AssetID.BTC, AssetID.USDC, 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_UST_ID, AssetID.BTC, AssetID.UST, 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [ETH_USD_ID, AssetID.ETH, AssetID.USDC, 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [TSLA_USD_ID, AssetID.TSLA, AssetID.USDC, 2, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [UST_USDC_ID, AssetID.UST, AssetID.USDC, 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))

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

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, to64x61(30)])

    return starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, marketPrices, liquidate, user_stats, hightide, alice_test, bob_test, python_executor


@pytest.mark.asyncio
async def test_unauthorized_call(adminAuth_factory):

    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, user_stats, hightide, alice_test, bob_test, python_executor = adminAuth_factory

    marketID = BTC_USD_ID
    fee_64x61 = to64x61(0.5)
    season_id = 1
    order_volume_64x61 = to64x61(1000)
    order_type = 1
    pnl_64x61 = to64x61(100)
    margin_amount_64x61 = to64x61(500)

    await assert_revert(dave_signer.send_transaction(dave, user_stats.contract_address, "record_trader_stats", [
        season_id,
        marketID,
        1,
        alice.contract_address,
        fee_64x61, order_volume_64x61, order_type, pnl_64x61, margin_amount_64x61]), "UserStats: Stats can be recorded only by TradingStats contract")


@pytest.mark.asyncio
async def test_record_trader_stats_with_two_open_orders(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, user_stats, hightide, alice_test, bob_test, python_executor = adminAuth_factory
    # start season to test recording of user stats
    season_id = 1
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [
        season_id])

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

    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_fee.result.fee_64x61) == 0.9699999999999964

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_fee.result.fee_64x61) == 2.424999999999999

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == 3.394999999999995

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_1*oracle_price_1

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_1*oracle_price_1

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 0
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 0

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0


@pytest.mark.asyncio
async def test_record_trader_stats_with_two_close_orders(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, user_stats, hightide, alice_test, bob_test, python_executor = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users_test = [alice_test, bob_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 0.5
    market_id_1 = BTC_USD_ID
    oracle_price_1 = 6000

    # Create orders
    orders_1 = [{
        "quantity": 0.5,
        "price": 6000,
        "order_type": order_types["limit"],
        "direction": order_direction["short"],
        "side": side["sell"]
    }, {
        "quantity": 0.5,
        "price": 6000,
        "side": side["sell"]
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_1

    # Recorded fee is not changed as we placed close orders
    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_fee.result.fee_64x61) == 0.9699999999999964

    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_fee.result.fee_64x61) == 2.424999999999999

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == 3.394999999999995

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader1_order_volume.result.total_volume_64x61) == quantity_locked_1*oracle_price_1

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(
        trader2_order_volume.result.total_volume_64x61) == quantity_locked_1*oracle_price_1

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 500
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 2500

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 500
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 2500


@pytest.mark.asyncio
async def test_record_trader_stats_with_one_open_order_and_one_close_order(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, user_stats, hightide, alice_test, bob_test, python_executor = adminAuth_factory

    ###################
    ### Open orders ##
    ###################
    # List of users
    users_test = [bob_test, alice_test]

    # Batch params for OPEN orders
    quantity_locked_1 = 0.5
    market_id_1 = BTC_USD_ID
    oracle_price_1 = 6000

    # Create orders
    orders_1 = [{
        "quantity": 1,
        "price": 6000,
        "order_type": order_types["limit"],
        "side": side["sell"]
    }, {
        "quantity": 1,
        "price": 6000,
    }]

    # execute order
    await execute_and_compare(zkx_node_signer=admin1_signer, zkx_node=admin1, executor=python_executor, orders=orders_1, users_test=users_test, quantity_locked=quantity_locked_1, market_id=market_id_1, oracle_price=oracle_price_1, trading=trading, is_reverted=0, error_code=0)

    season_id = 1
    market_id = market_id_1

    # Recorded fee is changed for Alice as it is a open order
    trader1_fee = await user_stats.get_trader_fee(season_id, market_id, alice.contract_address).call()
    print("alice fee",  from64x61(trader1_fee.result.fee_64x61))
    assert from64x61(trader1_fee.result.fee_64x61) == 2.424999999999996

    # Recorded fee is not changed for bob as it is a close order
    trader2_fee = await user_stats.get_trader_fee(season_id, market_id, bob.contract_address).call()
    print("bob fee",  from64x61(trader2_fee.result.fee_64x61))
    assert from64x61(trader2_fee.result.fee_64x61) == 2.424999999999999

    total_fee = await user_stats.get_total_fee(season_id, market_id).call()
    print("total fee", from64x61(total_fee.result.total_fee_64x61))
    assert from64x61(total_fee.result.total_fee_64x61) == 4.849999999999994

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, market_id, side["buy"])).call()
    assert trader1_order_volume.result.number_of_orders == 2
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == 8000

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, market_id, side["sell"])).call()
    assert trader2_order_volume.result.number_of_orders == 2
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == 6000

    trader1_pnl = await user_stats.get_trader_pnl(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 500
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, market_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 2500

    trader2_pnl = await user_stats.get_trader_pnl(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 1000
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, market_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 5000
