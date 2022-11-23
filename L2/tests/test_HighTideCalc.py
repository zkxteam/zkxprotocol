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
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, print_parsed_positions, print_parsed_collaterals, assert_events_emitted
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
timestamp2 = int(time.time()) + (60*60*24) + 60
timestamp3 = int(time.time()) + (60*60*24)*2 + 60
timestamp4 = int(time.time()) + (60*60*24)*3 + 60
timestamp5 = int(time.time()) + (60*60*24)*4 + 60
timestamp5 = int(time.time()) + (60*60*24)*5 + 60

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
    ### Deploy infrastructure (Part 1)
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

    contract_class = starknet_service.contracts_holder.get_contract_class(ContractType.LiquidityPool)
    global class_hash
    class_hash, _ = await starknet_service.starknet.state.declare(contract_class)
    direct_class_hash = compute_class_hash(contract_class)
    class_hash = int.from_bytes(class_hash,'big')
    assert direct_class_hash == class_hash

    ### Deploy user accounts
    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )
    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)
    dave = await account_factory.deploy_account(dave_signer.public_key)
    eduard = await account_factory.deploy_account(eduard_signer.public_key)
    gary = await account_factory.deploy_account(gary_signer.public_key)

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=initial_timestamp, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    ### Deploy infrastructure (Part 2)
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

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # add user accounts to account registry
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[admin1.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[admin2.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[alice.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[bob.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[charlie.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[dave.contract_address])

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
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    # Fund the Liquidity fund contract
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [AssetID.USDC, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [AssetID.UST, to64x61(1000000)])

    season_id = 1
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, 5])
    
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [1])

    await admin1_signer.send_transaction(admin1, hightide.contract_address,'set_liquidity_pool_contract_class_hash',[class_hash])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', [ETH_USD_ID, 1, admin1.contract_address, 1, 2, USDC_ID, 1000, 0, UST_ID, 500, 0])
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', [TSLA_USD_ID, 1, admin1.contract_address, 1, 2, USDC_ID, 1000, 0, UST_ID, 500, 0])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'set_constants', [
        to64x61(0.8), 
        to64x61(0.15), 
        to64x61(0.05), 
        to64x61(3), 
        to64x61(0.3)
    ])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'activate_high_tide', [1])
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'activate_high_tide', [2])

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [AssetID.USDC, to64x61(100000)])
    await admin1_signer.send_transaction(admin1, bob.contract_address, 'set_balance', [AssetID.USDC, to64x61(100000)])

    markets = await market.get_all_markets_by_state(1,0).call()
    print(markets.result)

    return starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, marketPrices, liquidate, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation
 
@pytest.mark.asyncio
async def test_placing_orders_day_0(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation = adminAuth_factory

    ####### Opening of BTC_USD Orders #######
    size1 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("hhsadklhfk")
    assetID_1 = AssetID.BTC
    collateralID_1 = AssetID.USDC
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("kdfjlk32lk4j")
    assetID_2 = AssetID.BTC
    collateralID_2 = AssetID.USDC
    price2 = to64x61(5000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ])

    season_id = 1
    pair_id = marketID_1

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 1

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 0).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    print(order_volume)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size1)*from64x61(execution_price1)

    trader1_fee = await user_stats.get_trader_fee(season_id, pair_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, pair_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, pair_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, pair_id, closeOrder1)).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == from64x61(size1)*from64x61(execution_price1)

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, pair_id, closeOrder2)).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == from64x61(size1)*from64x61(execution_price1)

    trader1_pnl = await user_stats.get_trader_pnl(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 0
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 0

    trader2_pnl = await user_stats.get_trader_pnl(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0

    ####### Opening of ETH_USD Orders #######
    size2 = to64x61(2)
    marketID_2 = ETH_USD_ID

    order_id_3 = str_to_felt("fasdkjlkw45")
    assetID_3 = AssetID.ETH
    collateralID_3 = AssetID.USDC
    price3 = to64x61(500)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(2)
    direction3 = 0
    closeOrder3 = 0
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("weriljerw")
    assetID_4 = AssetID.ETH
    collateralID_4 = AssetID.USDC
    price4 = to64x61(500)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(2)
    direction4 = 1
    closeOrder4 = 0
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(500)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, 0,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, 1,
    ])

    season_id = 1
    pair_id = marketID_2

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 1

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 0).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    print(order_volume)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size2)*from64x61(execution_price2)

    trader1_fee = await user_stats.get_trader_fee(season_id, pair_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees)*from64x61(size2)*from64x61(execution_price2)), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, pair_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees)*from64x61(size2)*from64x61(execution_price2)), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, pair_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, pair_id, closeOrder3)).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, pair_id, closeOrder4)).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader1_pnl = await user_stats.get_trader_pnl(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 0
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 0

    trader2_pnl = await user_stats.get_trader_pnl(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0

    ####### Opening of TESLA_USD Orders #######
    size3 = to64x61(4)
    marketID_3 = TSLA_USD_ID

    order_id_5 = str_to_felt("pqiejh23987f")
    assetID_5 = AssetID.TSLA
    collateralID_5 = AssetID.USDC
    price5 = to64x61(50)
    stopPrice5 = 0
    orderType5 = 0
    position5 = to64x61(4)
    direction5 = 1
    closeOrder5 = 0
    parentOrder5 = 0
    leverage5 = to64x61(1)
    liquidatorAddress5 = 0

    order_id_6 = str_to_felt("sj38udhjkajnkd")
    assetID_6 = AssetID.TSLA
    collateralID_6 = AssetID.USDC
    price6 = to64x61(50)
    stopPrice6 = 0
    orderType6 = 0
    position6 = to64x61(4)
    direction6 = 0
    closeOrder6 = 0
    parentOrder6 = 0
    leverage6 = to64x61(1)
    liquidatorAddress6 = 0

    execution_price3 = to64x61(50)

    hash_computed5 = hash_order(order_id_5, assetID_5, collateralID_5,
                                price5, stopPrice5, orderType5, position5, direction5, closeOrder5, leverage5)
    hash_computed6 = hash_order(order_id_6, assetID_6, collateralID_6,
                                price6, stopPrice6, orderType6, position6, direction6, closeOrder6, leverage6)

    signed_message5 = alice_signer.sign(hash_computed5)
    signed_message6 = bob_signer.sign(hash_computed6)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size3,
        execution_price3,
        marketID_3,
        2,
        alice.contract_address, signed_message5[0], signed_message5[
            1], order_id_5, assetID_5, collateralID_5, price5, stopPrice5, orderType5, position5, direction5, closeOrder5, leverage5, liquidatorAddress5, 0,
        bob.contract_address, signed_message6[0], signed_message6[
            1], order_id_6, assetID_6, collateralID_6, price6, stopPrice6, orderType6, position6, direction6, closeOrder6, leverage6, liquidatorAddress6, 1,
    ])

    season_id = 1
    pair_id = marketID_3

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 1

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 0).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    print(order_volume)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size3)*from64x61(execution_price3)

    trader1_fee = await user_stats.get_trader_fee(season_id, pair_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees)*from64x61(size3)*from64x61(execution_price3)), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, pair_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees)*from64x61(size3)*from64x61(execution_price3)), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, pair_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, pair_id, closeOrder5)).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == from64x61(size3)*from64x61(execution_price3)

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, pair_id, closeOrder6)).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == from64x61(size3)*from64x61(execution_price3)

    trader1_pnl = await user_stats.get_trader_pnl(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 0
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 0

    trader2_pnl = await user_stats.get_trader_pnl(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0

    await assert_revert(admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_w", [
        season_id,
        pair_id,
        2,
        alice.contract_address,
        bob.contract_address
    ]), "HighTideCalc: Season still ongoing")

    await assert_revert(admin1_signer.send_transaction(admin1, hightideCalc.contract_address, "calculate_trader_score", [
        season_id,
        pair_id,
        2,
        alice.contract_address,
        bob.contract_address
    ]), "HighTideCalc: Season still ongoing")

@pytest.mark.asyncio
async def test_closing_orders_day_1(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation = adminAuth_factory
    
    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp2, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    #### Open orders ##############
    size1 = to64x61(1)
    execution_price1 = to64x61(5000)

    #### Closing Of Orders ########
    size2 = to64x61(1)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("rlbrj32414hd")
    assetID_3 = AssetID.BTC
    collateralID_3 = AssetID.USDC
    price3 = to64x61(6000)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 1
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("tew243sdf2334")
    assetID_4 = AssetID.BTC
    collateralID_4 = AssetID.USDC
    price4 = to64x61(6000)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(1)
    direction4 = 0
    closeOrder4 = 1
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, 0,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, 1,
    ])

    season_id = 1
    pair_id = marketID_2

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 2

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 1).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size1)*from64x61(execution_price1)

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 1)).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size2)*from64x61(execution_price2)

    trader1_fee = await user_stats.get_trader_fee(season_id, pair_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, pair_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, pair_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, pair_id, closeOrder3)).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, pair_id, closeOrder4)).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader1_pnl = await user_stats.get_trader_pnl(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 1000
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 5000

    trader2_pnl = await user_stats.get_trader_pnl(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 1000
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 5000

    #### Open orders ##############
    size1 = to64x61(2)
    execution_price1 = to64x61(500)

    #### Closing Of Orders ########
    size2 = to64x61(2)
    marketID_2 = ETH_USD_ID

    order_id_3 = str_to_felt("kjddlsjlk")
    assetID_3 = AssetID.ETH
    collateralID_3 = AssetID.USDC
    price3 = to64x61(400)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(2)
    direction3 = 1
    closeOrder3 = 1
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("asdkfnjkllasd")
    assetID_4 = AssetID.ETH
    collateralID_4 = AssetID.USDC
    price4 = to64x61(400)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(2)
    direction4 = 0
    closeOrder4 = 1
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(400)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, 0,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, 1,
    ])

    season_id = 1
    pair_id = marketID_2

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 2

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 1).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size1)*from64x61(execution_price1)
    print("final short volume ETH", from64x61(order_volume.result[1]))

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 1)).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size1)*from64x61(execution_price2)
    print("final long volume ETH", from64x61(order_volume.result[1]))

    trader1_fee = await user_stats.get_trader_fee(season_id, pair_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, pair_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, pair_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, pair_id, closeOrder3)).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, pair_id, closeOrder4)).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader1_pnl = await user_stats.get_trader_pnl(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 200
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 1000

    trader2_pnl = await user_stats.get_trader_pnl(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 200
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 1000

    #### Open orders ##############
    size1 = to64x61(4)
    execution_price1 = to64x61(50)

    ####### Closing of TESLA_USD Orders #######
    size2 = to64x61(3)
    marketID_2 = TSLA_USD_ID

    order_id_1 = str_to_felt("opqoijljdlfs")
    assetID_1 = AssetID.TSLA
    collateralID_1 = AssetID.USDC
    price1 = to64x61(40)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(3)
    direction1 = 0
    closeOrder1 = 1
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("poq123lijos")
    assetID_2 = AssetID.TSLA
    collateralID_2 = AssetID.USDC
    price2 = to64x61(40)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 1
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price2 = to64x61(40)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ])

    season_id = 1
    pair_id = marketID_2

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 2

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 1).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size1)*from64x61(execution_price1)
    print("final short volume TSLA", from64x61(order_volume.result[1]))

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 1)).call()
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1]) == 2*from64x61(size2)*from64x61(execution_price2)
    print("final long volume TSLA", from64x61(order_volume.result[1]))

    trader1_fee = await user_stats.get_trader_fee(season_id, pair_id, alice.contract_address).call()
    fee = pytest.approx((from64x61(maker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader1_fee.result.fee_64x61) == fee

    trader2_fee = await user_stats.get_trader_fee(season_id, pair_id, bob.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, pair_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == from64x61(trader1_fee.result.fee_64x61) + from64x61(trader2_fee.result.fee_64x61)

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, pair_id, closeOrder1)).call()
    assert trader1_order_volume.result.number_of_orders == 1
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader2_order_volume = await user_stats.get_trader_order_volume(bob.contract_address, (season_id, pair_id, closeOrder2)).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == from64x61(size2)*from64x61(execution_price2)

    trader1_pnl = await user_stats.get_trader_pnl(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 30
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 150

    trader2_pnl = await user_stats.get_trader_pnl(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 30
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, bob.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 150

@pytest.mark.asyncio
async def test_opening_orders_day_2(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation = adminAuth_factory

    # here we check the scenario that there are multiple calls to record_trade_batch_stats in a single day
    # we also check that recording is handled properly when orders are executed partially
    # increment to next day
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp3, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    #### Open orders ##############
    size1 = to64x61(1)
    execution_price1 = to64x61(5000)

    size2 = to64x61(1)
    execution_price2 = to64x61(6000)
    ####### Opening of Orders #######
    size3 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("sdj343234df")
    assetID_1 = AssetID.BTC
    collateralID_1 = AssetID.USDC
    price1 = to64x61(6500)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(2)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("432342dfd23dff")
    assetID_2 = AssetID.BTC
    collateralID_2 = AssetID.USDC
    price2 = to64x61(6500)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price3 = to64x61(6500)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size3,
        execution_price3,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ])

    season_id = 1
    pair_id = marketID_1

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    print(days_traded.result.res)
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 2).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    print(active_traders.result.res)
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    print(trade_frequency.result.frequency)
    assert trade_frequency.result.frequency == [2, 2, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    print(order_volume.result)   
    assert order_volume.result[0] == 4
    assert from64x61(order_volume.result[1]) == 2*from64x61(size1)*from64x61(execution_price1) + 2*from64x61(size3)*from64x61(execution_price3)

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 1)).call()
    print("real", order_volume.result)
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1])== 2*from64x61(size2)*from64x61(execution_price2)

    order_id_2 = str_to_felt("432342dfd23dfe")
    assetID_2 = AssetID.BTC
    collateralID_2 = AssetID.USDC
    price2 = to64x61(6500)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size3,
        execution_price3,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ])


    season_id = 1
    pair_id = marketID_1

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    print(days_traded.result.res)
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 2).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 4

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    print(active_traders.result.res)
    assert active_traders.result.res == 2

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    print(trade_frequency.result.frequency)
    assert trade_frequency.result.frequency == [2, 2, 4]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 4

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    print(order_volume.result)   
    assert order_volume.result[0] == 6
    assert from64x61(order_volume.result[1]) == 2*from64x61(size1)*from64x61(execution_price1) + 4*from64x61(size3)*from64x61(execution_price3)

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 1)).call()
    print("real", order_volume.result)
    #print("expected", [2, 2*to64x61(size2*execution_price2)])
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1])== 2*from64x61(size2)*from64x61(execution_price2)

@pytest.mark.asyncio
async def test_opening_closing_orders_day_3(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation = adminAuth_factory

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
        starknet_version = STARKNET_VERSION
    )

    #### Open orders ##############
    size1 = to64x61(1)
    execution_price1 = to64x61(5000)

    size2 = to64x61(1)
    execution_price2 = to64x61(6000)

    size3 = to64x61(1)
    execution_price3 = to64x61(6500)
    ####### Opening of Orders #######
    size4 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("y7whd873i2jkfd")
    assetID_1 = AssetID.BTC
    collateralID_1 = AssetID.USDC
    price1 = to64x61(7000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(4)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("287fj1hjksaskjh")
    assetID_2 = AssetID.BTC
    collateralID_2 = AssetID.USDC
    price2 = to64x61(7000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    liquidatorAddress2 = 0

    execution_price4 = to64x61(7000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = charlie_signer.sign(hash_computed2)


    order_id_3 = str_to_felt("rlbrj32414hd1")
    assetID_3 = AssetID.BTC
    collateralID_3 = AssetID.USDC
    price3 = to64x61(7000)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(2)
    direction3 = 1
    closeOrder3 = 1
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("tew243sdf23341")
    assetID_4 = AssetID.BTC
    collateralID_4 = AssetID.USDC
    price4 = to64x61(7000)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(2)
    direction4 = 0
    closeOrder4 = 1
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0


    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)


    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size4,
        execution_price4,
        marketID_1,
        4,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        charlie.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, 0,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, 1,
    ])

    season_id = 1
    pair_id = marketID_1

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 4

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 3).call()
    print(num_trades_in_a_day.result.res)
    assert num_trades_in_a_day.result.res == 4

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 3

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2, 2, 4, 4]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 4


    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    print(order_volume.result)   
    assert order_volume.result[0] == 8
    assert from64x61(order_volume.result[1]) == (2*from64x61(size1)*from64x61(execution_price1) + 4*from64x61(size3)*from64x61(execution_price3) \
                                                + 2*from64x61(size4)*from64x61(execution_price4))
    print("final short volume BTC", from64x61(order_volume.result[1]))
    
    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 1)).call()
    print(order_volume.result)   
    assert order_volume.result[0] == 4
    assert from64x61(order_volume.result[1]) == (2*from64x61(size2)*from64x61(execution_price2) \
                                                + 2*from64x61(size4)*from64x61(execution_price4))
    print("final long volume BTC", from64x61(order_volume.result[1]))


@pytest.mark.asyncio
async def test_opening_closing_orders_day_4(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation = adminAuth_factory

    # increment to a later date 
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp5, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    ####### opening and closing of TESLA_USD Orders #######
    size1 = to64x61(1)
    marketID_1 = TSLA_USD_ID

    order_id_1 = str_to_felt("opqoijfitlfs")
    assetID_1 = AssetID.TSLA
    collateralID_1 = AssetID.USDC
    price1 = to64x61(30)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 1
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("poq1deajos")
    assetID_2 = AssetID.TSLA
    collateralID_2 = AssetID.USDC
    price2 = to64x61(30)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(30)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = charlie_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        charlie.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ])

    season_id = 1
    pair_id = marketID_1

    days_traded = await trading_stats.get_total_days_traded(season_id, pair_id).call()
    assert days_traded.result.res == 3

    num_trades_in_a_day = await trading_stats.get_num_trades_in_day(season_id, pair_id, 4).call()
    assert num_trades_in_a_day.result.res == 2

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 3

    trade_frequency = await trading_stats.get_season_trade_frequency(season_id, pair_id).call()
    assert trade_frequency.result.frequency == [2, 2, 0, 0, 2]

    max_trades = await trading_stats.get_max_trades_in_day(season_id, pair_id).call()
    assert max_trades.result.res == 2

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    assert order_volume.result[0] == 3
    assert from64x61(order_volume.result[1]) == ((2*4*50) + (1*1*30))
    print("final short volume TSLA", from64x61(order_volume.result[1]))

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 1)).call()
    assert order_volume.result[0] == 3
    assert from64x61(order_volume.result[1]) == ((2*3*40) + (1*1*30))
    print("final long volume TSLA", from64x61(order_volume.result[1]))

    trader1_fee = await user_stats.get_trader_fee(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_fee.result.fee_64x61) == 0.03879999999999986

    trader2_fee = await user_stats.get_trader_fee(season_id, pair_id, charlie.contract_address).call()
    fee = pytest.approx((from64x61(taker_trading_fees)*from64x61(size1)*from64x61(execution_price1)), abs=1e-6)
    assert from64x61(trader2_fee.result.fee_64x61) == fee

    total_fee = await user_stats.get_total_fee(season_id, pair_id).call()
    assert from64x61(total_fee.result.total_fee_64x61) == 0.1503499999999998

    trader1_order_volume = await user_stats.get_trader_order_volume(alice.contract_address, (season_id, pair_id, closeOrder1)).call()
    assert trader1_order_volume.result.number_of_orders == 2
    assert from64x61(trader1_order_volume.result.total_volume_64x61) == ((3*40) + from64x61(size1)*from64x61(execution_price1))

    trader2_order_volume = await user_stats.get_trader_order_volume(charlie.contract_address, (season_id, pair_id, closeOrder2)).call()
    assert trader2_order_volume.result.number_of_orders == 1
    assert from64x61(trader2_order_volume.result.total_volume_64x61) == from64x61(size1)*from64x61(execution_price1)

    trader1_pnl = await user_stats.get_trader_pnl(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_pnl.result.pnl_64x61) == 50
    trader1_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, alice.contract_address).call()
    assert from64x61(trader1_margin.result.margin_amount_64x61) == 200

    trader2_pnl = await user_stats.get_trader_pnl(season_id, pair_id, charlie.contract_address).call()
    assert from64x61(trader2_pnl.result.pnl_64x61) == 0
    trader2_margin = await user_stats.get_trader_margin_amount(season_id, pair_id, charlie.contract_address).call()
    assert from64x61(trader2_margin.result.margin_amount_64x61) == 0


@pytest.mark.asyncio
async def test_calculating_factors(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc, user_stats, rewardsCalculation = adminAuth_factory

    # increment to a later date 
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp6, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    markets = await hightide.get_hightides_by_season_id(1).call()
    print(markets.result)

    top_stats = await hightideCalc.find_top_stats(1).call()
    print(top_stats.result)

    set_factors_tx = await dave_signer.send_transaction(dave, hightideCalc.contract_address, "calculate_high_tide_factors", [
        1,
    ])

    ETH_factors = await hightideCalc.get_hightide_factors(1, ETH_USD_ID).call()
    ETH_parsed = list(ETH_factors.result.res)
    print(ETH_parsed)

    assert from64x61(ETH_parsed[0]) == pytest.approx(((3600/4)/(76000/12)), abs=1e-6)
    assert from64x61(ETH_parsed[1]) == (2/4)
    assert from64x61(ETH_parsed[2]) == (2/5)
    assert from64x61(ETH_parsed[3]) == (2/3)

    TSLA_factors = await hightideCalc.get_hightide_factors(1, TSLA_USD_ID).call()
    TSLA_parsed = list(TSLA_factors.result.res)
    print(TSLA_parsed)

    assert from64x61(TSLA_parsed[0]) == pytest.approx(((700/6)/(76000/12)), abs=1e-6)
    assert from64x61(TSLA_parsed[1]) == (2/4)
    assert from64x61(TSLA_parsed[2]) == (3/5)
    assert from64x61(TSLA_parsed[3]) == (3/3)

    assert_events_emitted(
        set_factors_tx,
        [
            [0, hightideCalc.contract_address, "high_tide_factors_set", [1, ETH_USD_ID] + ETH_parsed],
            [1, hightideCalc.contract_address, "high_tide_factors_set", [1, TSLA_USD_ID] + TSLA_parsed]
        ]
    )

    season_id = 1
    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    num_trading_days = fetched_trading_season.num_trading_days

    timestamp = fetched_trading_season.start_timestamp + (num_trading_days*24*60*60) + 1

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    await admin1_signer.send_transaction(admin1, hightide.contract_address,"end_trade_season",[season_id])
    await admin1_signer.send_transaction(admin1, rewardsCalculation.contract_address,"set_user_xp_values",
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
    assert from64x61(alice_w_ETH_USD_ID.result.trader_score) == 0.4479042456318879
    bob_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, bob.contract_address).call()
    assert from64x61(bob_w_ETH_USD_ID.result.trader_score) == 0.5520957543681121
    charlie_w_ETH_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, ETH_USD_ID, charlie.contract_address).call()
    assert from64x61(charlie_w_ETH_USD_ID.result.trader_score) == 0
    
    # Get the trader score for all traders
    alice_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, alice.contract_address).call()
    assert from64x61(alice_w_TSLA_USD_ID.result.trader_score) == 0.3060977266932676
    bob_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, bob.contract_address).call()
    assert from64x61(bob_w_TSLA_USD_ID.result.trader_score) == 0.37100273218642876
    charlie_w_TSLA_USD_ID = await hightideCalc.get_trader_score_per_market(season_id, TSLA_USD_ID, charlie.contract_address).call()
    assert from64x61(charlie_w_TSLA_USD_ID.result.trader_score) == 0.3228995411203036

    # funds flow per market comparision
    funds_flow_BTC_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, BTC_USD_ID).call()
    assert from64x61(funds_flow_BTC_USD_ID.result.funds_flow) == 0
    funds_flow_ETH_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, ETH_USD_ID).call()
    assert from64x61(funds_flow_ETH_USD_ID.result.funds_flow) == 0.42719298245614035
    funds_flow_TSLA_USD_ID = await hightideCalc.get_funds_flow_per_market(season_id, TSLA_USD_ID).call()
    assert from64x61(funds_flow_TSLA_USD_ID.result.funds_flow) == 0.5296052631578947
