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

BTC_ID = str_to_felt("32f0406jz7qj8")
ETH_ID = str_to_felt("65ksgn23nv")
USDC_ID = str_to_felt("fghj3am52qpzsib")
UST_ID = str_to_felt("yjk45lvmasopq")
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")
DOGE_ID = str_to_felt("jdi2i8621hzmnc7324o")
TSLA_ID = str_to_felt("i39sk1nxlqlzcee")

initial_timestamp = int(time.time())
timestamp2 = int(time.time()) + (60*60*24) + 60
timestamp3 = int(time.time()) + (60*60*24)*2 + 60
timestamp4 = int(time.time()) + (60*60*24)*3 + 60
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
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    hightideCalc = await starknet_service.deploy(ContractType.HighTideCalc, [registry.contract_address, 1])
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])

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
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [26, 1, trading_stats.contract_address])

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
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [BTC_ID, 1, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [ETH_ID, 1, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [USDC_ID, 1, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [UST_ID, 1, str_to_felt("UST"), str_to_felt("UST"), 1, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [DOGE_ID, 1, str_to_felt("DOGE"), str_to_felt("DOGECOIN"), 0, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [TSLA_ID, 1, str_to_felt("TESLA"), str_to_felt("TESLA MOTORS"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USD_ID, BTC_ID, USDC_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_UST_ID, BTC_ID, UST_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [ETH_USD_ID, ETH_ID, USDC_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [TSLA_USD_ID, TSLA_ID, USDC_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [UST_USDC_ID, UST_ID, USDC_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Update collateral prices
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [USDC_ID, to64x61(1)])
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [UST_ID, to64x61(1)])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Fund the Liquidity fund contract
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    season_id = 1
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, 4])

    return starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, marketPrices, liquidate, trading_stats, hightide, hightideCalc

@pytest.mark.asyncio
async def test_unauthorized_call(adminAuth_factory):
    
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, factors = adminAuth_factory

    alice_balance = to64x61(50000)
    bob_balance = to64x61(50000)
    
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    size1 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("sdj324hka8kaedf")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("wer4iljerw")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
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

    await assert_revert(dave_signer.send_transaction(dave, trading_stats.contract_address, "record_trade_batch_stats", [
        marketID_1,
        size1,
        execution_price1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, 1,
    ]), "Trade can be recorded only by Trading contract")


@pytest.mark.asyncio
async def test_invalid_season_id_call(adminAuth_factory):
    
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc = adminAuth_factory
     ####### Opening of Orders #######
    size1 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("12345")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("67899")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
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
    
    season_id=0
    pair_id=marketID_1

    await assert_revert(trading_stats.get_total_days_traded(season_id, pair_id).call(),"Invalid season id")

    active_traders = await trading_stats.get_num_active_traders(season_id, pair_id).call()
    assert active_traders.result.res == 0

    await assert_revert(trading_stats.get_max_trades_in_day(season_id, pair_id).call(),"Invalid season id")

    order_volume = await trading_stats.get_order_volume((season_id, pair_id, 0)).call()
    assert order_volume.result[0] == 0
    assert from64x61(order_volume.result[1]) == 0

@pytest.mark.asyncio
async def test_placing_orders_day_0(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc = adminAuth_factory

    # start season to test recording of trade stats
    season_id=1
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [
        season_id])

    ####### Opening of BTC_USD Orders #######
    size1 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("hhsadklhfk")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
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
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
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

    ####### Opening of ETH_USD Orders #######
    size2 = to64x61(2)
    marketID_2 = ETH_USD_ID

    order_id_3 = str_to_felt("fasdkjlkw45")
    assetID_3 = ETH_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(500)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(2)
    direction3 = 0
    closeOrder3 = 0
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("weriljerw")
    assetID_4 = ETH_ID
    collateralID_4 = USDC_ID
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

    ####### Opening of TESLA_USD Orders #######
    size3 = to64x61(4)
    marketID_3 = TSLA_USD_ID

    order_id_5 = str_to_felt("pqiejh23987f")
    assetID_5 = TSLA_ID
    collateralID_5 = USDC_ID
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
    assetID_6 = TSLA_ID
    collateralID_6 = USDC_ID
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

@pytest.mark.asyncio
async def test_closing_orders_day_1(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc = adminAuth_factory
    
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
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(6000)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 1
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("tew243sdf2334")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
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

    #### Open orders ##############
    size1 = to64x61(2)
    execution_price1 = to64x61(500)

    #### Closing Of Orders ########
    size2 = to64x61(2)
    marketID_2 = ETH_USD_ID

    order_id_3 = str_to_felt("kjddlsjlk")
    assetID_3 = ETH_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(400)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(2)
    direction3 = 1
    closeOrder3 = 1
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("asdkfnjkllasd")
    assetID_4 = ETH_ID
    collateralID_4 = USDC_ID
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

    #### Open orders ##############
    size1 = to64x61(4)
    execution_price1 = to64x61(50)

    ####### Closing of TESLA_USD Orders #######
    size2 = to64x61(3)
    marketID_2 = TSLA_USD_ID

    order_id_1 = str_to_felt("opqoijljdlfs")
    assetID_1 = TSLA_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(40)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(3)
    direction1 = 0
    closeOrder1 = 1
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("poq123lijos")
    assetID_2 = TSLA_ID
    collateralID_2 = USDC_ID
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


@pytest.mark.asyncio
async def test_opening_orders_day_2(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc = adminAuth_factory

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
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
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
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
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
    #print("expected", [2, 2*to64x61(size2*execution_price2)])
    assert order_volume.result[0] == 2
    assert from64x61(order_volume.result[1])== 2*from64x61(size2)*from64x61(execution_price2)

    order_id_2 = str_to_felt("432342dfd23dfe")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
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
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc = adminAuth_factory

    # here we test with new traders in request_list
    # we also test a batch of trades with open as well as close type orders
    charlie_balance = to64x61(50000)
    
    await admin1_signer.send_transaction(admin1, charlie.contract_address, 'set_balance', [USDC_ID, charlie_balance])
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
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
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
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
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
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(7000)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(2)
    direction3 = 1
    closeOrder3 = 1
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("tew243sdf23341")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
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
async def test_calculating_factors(adminAuth_factory):
    starknet_service, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance, _, _, trading_stats, hightide, hightideCalc = adminAuth_factory

    # increment to a later date 
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp5, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    await dave_signer.send_transaction(dave, hightideCalc.contract_address, "calculate_high_tide_factors", [
        2,
        ETH_USD_ID,
        TSLA_USD_ID,
        1, 
        BTC_USD_ID
    ])

    ETH_factors = await hightideCalc.get_hightide_factors(1, ETH_USD_ID).call()
    ETH_parsed = list(ETH_factors.result.res)

    assert from64x61(ETH_parsed[0]) == pytest.approx(((3600/4)/(76000/12)), abs=1e-6)
    assert from64x61(ETH_parsed[1]) == (2/4)
    assert from64x61(ETH_parsed[2]) == (2/4)
    assert from64x61(ETH_parsed[3]) == (2/3)

    TSLA_factors = await hightideCalc.get_hightide_factors(1, TSLA_USD_ID).call()
    TSLA_parsed = list(TSLA_factors.result.res)

    assert from64x61(TSLA_parsed[0]) == pytest.approx(((640/4)/(76000/12)), abs=1e-6)
    assert from64x61(TSLA_parsed[1]) == (2/4)
    assert from64x61(TSLA_parsed[2]) == (2/4)
    assert from64x61(TSLA_parsed[3]) == (2/3)
    

    
   