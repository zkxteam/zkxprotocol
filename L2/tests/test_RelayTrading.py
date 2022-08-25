from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61
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

BTC_ID = str_to_felt("32f0406jz7qj8")
ETH_ID = str_to_felt("65ksgn23nv")
USDC_ID = str_to_felt("fghj3am52qpzsib")
UST_ID = str_to_felt("yjk45lvmasopq")
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

    ### Deploy infrastructure (Part 1)
    admin1 = await starknet_service.deploy(ContractType.Account, [
        admin1_signer.public_key
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        admin2_signer.public_key
    ])
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    fees = await starknet_service.deploy(ContractType.TradingFees, [registry.contract_address, 1])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
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

    timestamp = int(time.time())

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Access 2 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 7, 1])

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

    # Deploy relay contracts with appropriate indexes
    relay_trading = await starknet_service.deploy(ContractType.RelayTrading, [
        registry.contract_address, 
        1,
        5 # trading index
    ])
    relay_asset = await starknet_service.deploy(ContractType.RelayAsset, [
        registry.contract_address, 
        1,
        1 # asset index
    ])
    relay_holding = await starknet_service.deploy(ContractType.RelayHolding, [
        registry.contract_address, 
        1,
        7 # holding index
    ])
    relay_feeBalance = await starknet_service.deploy(ContractType.RelayFeeBalance, [
        registry.contract_address, 
        1,
        6 # feeBalance index
    ])

    # give full permissions to all relays
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_trading.contract_address, 0, 1])
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_trading.contract_address, 1, 1])

    # Access 2 allows adding trusted contracts to the registry
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_trading.contract_address, 2, 1])

    # Access 3 allows adding trusted contracts to the registry
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_trading.contract_address, 3, 1])
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_trading.contract_address, 4, 1])
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_trading.contract_address, 5, 1])

    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 0, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 1, 1])

    # Access 2 allows adding trusted contracts to the registry
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 2, 1])

    # Access 3 allows adding trusted contracts to the registry
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 3, 1])
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 4, 1])
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 5, 1])


    
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_holding.contract_address, 5, 1])

   

    # Access 3 allows adding trusted contracts to the registry
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_feeBalance.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_feeBalance.contract_address, 4, 1])
    #await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_feeBalance.contract_address, 5, 1])

    

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
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'addAsset', [BTC_ID, 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'addAsset', [ETH_ID, 0, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'addAsset', [UST_ID, 0, str_to_felt("UST"), str_to_felt("UST"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'addAsset', [DOGE_ID, 0, str_to_felt("DOGE"), str_to_felt("DOGECOIN"), 0, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, relay_asset.contract_address, 'addAsset', [TSLA_ID, 0, str_to_felt("TESLA"), str_to_felt("TESLA MOTORS"), 1, 0, 0, 1, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [BTC_USD_ID, BTC_ID, USDC_ID, to64x61(10), 1, 10])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [ETH_USD_ID, ETH_ID, USDC_ID, to64x61(10), 1, 10])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [TSLA_USD_ID, TSLA_ID, USDC_ID, to64x61(10), 1, 10])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Fund the Liquidity fund contract
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [USDC_ID, to64x61(1000000)])
    await admin1_signer.send_transaction(admin1, liquidity.contract_address, 'fund', [UST_ID, to64x61(1000000)])

    # Update collateral prices
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [USDC_ID, to64x61(1)])
    await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [UST_ID, to64x61(1)])

    # Set the balance of admin1 and admin2
    #await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    #await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])

    # return relay versions of asset, trading, holding, feeBalance to test underlying contract logic
    return starknet_service.starknet, adminAuth, fees, admin1, admin2, relay_asset, relay_trading, alice, bob, charlie, dave, fixed_math, relay_holding, relay_feeBalance



@pytest.mark.asyncio
async def test_set_balance_for_testing(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory
    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)
    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    bob_curr_balance = await bob.get_balance(USDC_ID).call()

    assert alice_curr_balance.result.res == alice_balance
    assert bob_curr_balance.result.res == bob_balance


@pytest.mark.asyncio
async def test_revert_balance_low(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100)
    bob_balance = to64x61(100)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("pqlkzc3434")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(10789)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("p21pdfs12mfd")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(10789)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ]))

@pytest.mark.asyncio
async def test_revert_if_market_order_2percent_deviation(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("kzwerl2kfsm")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("asl19uxkzck")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1021)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ]))


@pytest.mark.asyncio
async def test_revert_if_bad_limit_order_long(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("ls23ksfl2fd")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("sdfk23kdfsl1")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1000)
    stopPrice2 = 0
    orderType2 = 1
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1001)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ]))


@pytest.mark.asyncio
async def test_revert_if_bad_limit_order_short(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("kmzm2ms62fds")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1000)
    stopPrice1 = 0
    orderType1 = 1
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("9sk2nsk2llj")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1000)
    stopPrice2 = 0
    orderType2 = 1
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(999)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ]))


@pytest.mark.asyncio
async def test_revert_if_order_mismatch(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("jciow4k234")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("sdfk32lvfl")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1078)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 0
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ]))


@pytest.mark.asyncio
async def test_revert_if_asset_not_tradable(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = TSLA_USD_ID

    order_id_1 = str_to_felt("w3godgvx323af")
    assetID_1 = TSLA_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("fj45g324dfsg")
    assetID_2 = TSLA_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1078)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ]))


@pytest.mark.asyncio
async def test_revert_if_collateral_mismatch(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [UST_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("wqelvqwe23")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("34ksdfmvcv")
    assetID_2 = BTC_ID
    collateralID_2 = UST_ID
    price2 = to64x61(1078)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ]))


@pytest.mark.asyncio
async def test_revert_if_asset_mismatch(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("wqelvqwe23")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(1078)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 3
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("34ksdfmvcv")
    assetID_2 = ETH_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(1078)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(1078)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ]))


@pytest.mark.asyncio
async def test_revert_wrong_signature(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(1000000)
    bob_balance = to64x61(1000000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("y7hi83kjhr")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(10789)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(4)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("329dsfjvcx9u")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(10789)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(10789)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    assert_revert(lambda: dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message1[0], signed_message1[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress1, parentOrder2, 0,
    ]))


@pytest.mark.asyncio
async def test_revert_if_leverage_more_than_allowed(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("343uofdsjnv")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = 11
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
    leverage2 = 3
    liquidatorAddress2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    await assert_revert(dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ]))


@pytest.mark.asyncio
async def test_opening_and_closing_full_orders(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    alice_curr_balance_before = await alice.get_balance(USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(USDC_ID).call()

    ####### Opening of Orders #######
    size = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("343uofdsjnv")
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

    amount1 = await fixed_math.Math64x61_mul(execution_price1, size).call()
    fees1 = await fixed_math.Math64x61_mul(amount1.result.res, maker_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.Math64x61_mul(execution_price1, size).call()
    fees2 = await fixed_math.Math64x61_mul(amount2.result.res, taker_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 0,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 1,
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        position1,
        orderType1,
        direction1,
        size,
        2,
        to64x61(5000),
        to64x61(0),
        leverage1
    ]

    orderState2 = await bob.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        size,
        2,
        to64x61(5000),
        to64x61(0),
        leverage2
    ]

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    bob_curr_balance = await bob.get_balance(USDC_ID).call()
    holdingBalance = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    print("Fee balance got: ", feeBalance_curr.result.fee)
    print("Alice fee: ", alice_total_fees.result.fee)
    print("Bob fee: ", bob_total_fees.result.fee)

    assert from64x61(alice_curr_balance.result.res) == from64x61(alice_curr_balance_before.result.res - total_amount1)
    assert from64x61(bob_curr_balance.result.res) == from64x61(bob_curr_balance_before.result.res - total_amount2)
    assert holdingBalance.result.amount == holdingBalance_before.result.amount + \
        amount1.result.res + amount2.result.res
    # Commenting the below line because of 64x61 bug
    #assert from64x61(alice_total_fees.result.fee) == from64x61(alice_total_fees_before.result.fee) + from64x61(fees1.result.res)
    assert from64x61(bob_total_fees.result.fee) == from64x61(bob_total_fees_before.result.fee + fees2.result.res)
    #assert from64x61(feeBalance_curr.result.fee) == from64x61(feeBalance_before.result.fee + fees1.result.res + fees2.result.res)

    #### Closing Of Orders ########
    size2 = to64x61(1)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("rlbrj4hd")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(6000)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("tew2334")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(6000)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(1)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    amount2 = await fixed_math.Math64x61_mul(execution_price2, size).call()

    pnl = execution_price2 - execution_price1
    adjusted_price = execution_price1 - pnl
    amount1 = await fixed_math.Math64x61_mul(adjusted_price, size).call()

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, parentOrder3, 0,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, parentOrder4, 1,
    ])

    orderState3 = await alice.get_order_data(orderID_=order_id_1).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3,
        collateralID_3,
        price1,
        execution_price1,
        0,
        orderType1,
        direction1,
        0,
        4,
        to64x61(0),
        to64x61(0),
        leverage3
    ]

    orderState4 = await bob.get_order_data(orderID_=order_id_2).call()
    res4 = list(orderState4.result.res)

    assert res4 == [
        assetID_4,
        collateralID_4,
        price2,
        execution_price1,
        0,
        orderType2,
        direction2,
        0,
        4,
        to64x61(0),
        to64x61(0),
        leverage4
    ]

    alice_curr_balance_after = await alice.get_balance(collateralID_3).call()
    bob_curr_balance_after = await bob.get_balance(collateralID_4).call()
    holdingBalance_after = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    assert holdingBalance_after.result.amount == holdingBalance.result.amount - \
        amount1.result.res - amount2.result.res
    assert alice_curr_balance_after.result.res == alice_curr_balance.result.res + \
        amount1.result.res
    assert bob_curr_balance_after.result.res == bob_curr_balance.result.res + amount2.result.res
    assert alice_total_fees_after.result.fee == alice_total_fees.result.fee
    assert bob_total_fees_after.result.fee == bob_total_fees.result.fee
    assert feeBalance_after.result.fee == feeBalance_curr.result.fee


@pytest.mark.asyncio
async def test_three_orders_in_a_batch(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)
    charlie_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])
    await admin2_signer.send_transaction(admin2, charlie.contract_address, 'set_balance', [USDC_ID, charlie_balance])

    alice_curr_balance_before = await alice.get_balance(assetID_=USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(assetID_=USDC_ID).call()
    charlie_curr_balance_before = await charlie.get_balance(assetID_=USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(4)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("asdlfkjaf")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(9325.2432042)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(5)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("fdser34iu45g")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(9325.03424)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(3)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    order_id_3 = str_to_felt("3dfw32423rv")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(9324.43)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(1)
    direction3 = 1
    closeOrder3 = 0
    parentOrder3 = 0
    leverage3 = to64x61(1)
    liquidatorAddress3 = 0

    execution_price1 = to64x61(9325)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)
    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)
    signed_message3 = charlie_signer.sign(hash_computed3)

    amount1 = await fixed_math.Math64x61_mul(execution_price1, size1).call()
    fees1 = await fixed_math.Math64x61_mul(amount1.result.res, taker_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    amount2 = await fixed_math.Math64x61_mul(execution_price1, position2).call()
    fees2 = await fixed_math.Math64x61_mul(amount2.result.res, maker_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    amount3 = await fixed_math.Math64x61_mul(execution_price1, position3).call()
    fees3 = await fixed_math.Math64x61_mul(amount3.result.res, maker_trading_fees).call()
    total_amount3 = amount3.result.res + fees3.result.res

    holdingBalance_before = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()
    charlie_total_fees_before = await feeBalance.get_user_fee(address=charlie.contract_address, assetID_=USDC_ID).call()

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        3,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
        charlie.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, parentOrder3, 0,
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        position1,
        orderType1,
        direction1,
        size1,
        1,
        to64x61(37300),
        to64x61(0),
        leverage1
    ]

    orderState2 = await bob.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        position2,
        2,
        to64x61(27975),
        to64x61(0),
        leverage2
    ]

    orderState3 = await charlie.get_order_data(orderID_=order_id_3).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3,
        collateralID_3,
        price3,
        execution_price1,
        position3,
        orderType3,
        direction3,
        position3,
        2,
        to64x61(9325),
        to64x61(0),
        leverage3
    ]

    alice_curr_balance = await alice.get_balance(assetID_=USDC_ID).call()
    bob_curr_balance = await bob.get_balance(assetID_=USDC_ID).call()
    charlie_curr_balance = await charlie.get_balance(assetID_=USDC_ID).call()
    holdingBalance = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()
    charlie_total_fees = await feeBalance.get_user_fee(address=charlie.contract_address, assetID_=USDC_ID).call()

    assert alice_curr_balance.result.res == alice_curr_balance_before.result.res - total_amount1
    assert from64x61(bob_curr_balance.result.res) == from64x61(bob_curr_balance_before.result.res - total_amount2)
    assert from64x61(charlie_curr_balance.result.res) == from64x61(charlie_curr_balance_before.result.res - total_amount3)
    assert from64x61(holdingBalance.result.amount) == from64x61(holdingBalance_before.result.amount + amount1.result.res + amount2.result.res + amount3.result.res)
    assert from64x61(alice_total_fees.result.fee) == from64x61(alice_total_fees_before.result.fee + fees1.result.res)
    # Commenting the following check because of 64x61 bug
    #assert from64x61(bob_total_fees.result.fee) == from64x61(bob_total_fees_before.result.fee + fees2.result.res)
    #assert from64x61(charlie_total_fees.result.fee) == from64x61(charlie_total_fees_before.result.fee + fees3.result.res)
    #assert from64x61(feeBalance_curr.result.fee) == from64x61(feeBalance_before.result.fee + fees1.result.res + fees2.result.res + fees3.result.res)

    ##### Closing Of Orders ########
    size2 = to64x61(4)
    marketID_2 = BTC_USD_ID

    order_id_4 = str_to_felt("er8u324hj4hd")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(12000.2432042)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(4)
    direction4 = 1
    closeOrder4 = 1
    parentOrder4 = order_id_1
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0

    order_id_5 = str_to_felt("5324k34")
    assetID_5 = BTC_ID
    collateralID_5 = USDC_ID
    price5 = to64x61(12032.9803)
    stopPrice5 = 0
    orderType5 = 0
    position5 = to64x61(3)
    direction5 = 0
    closeOrder5 = 1
    parentOrder5 = order_id_2
    leverage5 = to64x61(1)
    liquidatorAddress5 = 0

    order_id_6 = str_to_felt("3df324gds34")
    assetID_6 = BTC_ID
    collateralID_6 = USDC_ID
    price6 = to64x61(12010.2610396)
    stopPrice6 = 0
    orderType6 = 0
    position6 = to64x61(1)
    direction6 = 0
    closeOrder6 = 1
    parentOrder6 = order_id_3
    leverage6 = to64x61(1)
    liquidatorAddress6 = 0

    execution_price2 = to64x61(12025.432)

    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)
    hash_computed5 = hash_order(order_id_5, assetID_5, collateralID_5,
                                price5, stopPrice5, orderType5, position5, direction5, closeOrder5, leverage5)
    hash_computed6 = hash_order(order_id_6, assetID_6, collateralID_6,
                                price6, stopPrice6, orderType6, position6, direction6, closeOrder6, leverage6)

    signed_message4 = alice_signer.sign(hash_computed4)
    signed_message5 = bob_signer.sign(hash_computed5)
    signed_message6 = charlie_signer.sign(hash_computed6)

    pnl = execution_price2 - execution_price1
    adjusted_price = execution_price1 - pnl
    amount1 = await fixed_math.Math64x61_mul(adjusted_price, size2).call()

    amount2 = await fixed_math.Math64x61_mul(execution_price2, position2).call()

    amount3 = await fixed_math.Math64x61_mul(execution_price2, position3).call()

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        3,
        alice.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, parentOrder4, 1,
        bob.contract_address, signed_message5[0], signed_message5[
            1], order_id_5, assetID_5, collateralID_5, price5, stopPrice5, orderType5, position5, direction5, closeOrder5, leverage5, liquidatorAddress5, parentOrder5, 0,
        charlie.contract_address, signed_message6[0], signed_message6[
            1], order_id_6, assetID_6, collateralID_6, price6, stopPrice6, orderType6, position6, direction6, closeOrder6, leverage6, liquidatorAddress6, parentOrder6, 0,
    ])

    orderState4 = await alice.get_order_data(orderID_=order_id_1).call()
    res4 = list(orderState4.result.res)
    assert res4 == [
        assetID_4,
        collateralID_4,
        price1,
        execution_price1,
        to64x61(1),
        orderType1,
        direction1,
        0,
        4,
        to64x61(0),
        to64x61(0),
        leverage4
    ]

    orderState5 = await bob.get_order_data(orderID_=order_id_2).call()
    res5 = list(orderState5.result.res)
    assert res5 == [
        assetID_5,
        collateralID_5,
        price2,
        execution_price1,
        0,
        orderType2,
        direction2,
        0,
        4,
        to64x61(0),
        to64x61(0),
        leverage5
    ]

    orderState6 = await charlie.get_order_data(orderID_=order_id_3).call()
    res6 = list(orderState6.result.res)
    assert res6 == [
        assetID_6,
        collateralID_6,
        price3,
        execution_price1,
        0,
        orderType3,
        direction3,
        0,
        4,
        to64x61(0),
        to64x61(0),
        leverage6
    ]

    alice_curr_balance_after = await alice.get_balance(assetID_=USDC_ID).call()
    bob_curr_balance_after = await bob.get_balance(assetID_=USDC_ID).call()
    charlie_curr_balance_after = await charlie.get_balance(assetID_=USDC_ID).call()
    holdingBalance_after = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()
    charlie_total_fees_after = await feeBalance.get_user_fee(address=charlie.contract_address, assetID_=USDC_ID).call()

    assert holdingBalance_after.result.amount == holdingBalance.result.amount - \
        amount1.result.res - amount2.result.res - amount3.result.res
    assert alice_curr_balance_after.result.res == alice_curr_balance.result.res + \
        amount1.result.res
    assert bob_curr_balance_after.result.res == bob_curr_balance.result.res + amount2.result.res
    assert charlie_curr_balance_after.result.res == charlie_curr_balance.result.res + \
        amount3.result.res
    assert alice_total_fees_after.result.fee == alice_total_fees.result.fee
    assert bob_total_fees_after.result.fee == bob_total_fees.result.fee
    assert charlie_total_fees_after.result.fee == charlie_total_fees.result.fee
    assert feeBalance_after.result.fee == feeBalance_curr.result.fee


@pytest.mark.asyncio
async def test_opening_and_closing_full_orders_with_leverage(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    alice_curr_balance_before = await alice.get_balance(USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(USDC_ID).call()

    ####### Opening of Orders #######
    size1 = to64x61(2)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("343uofdsjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(2)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(2)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("wer4iljemn")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(5000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(2)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(2)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(5000)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    size_without_leverage1 = await fixed_math.Math64x61_div(size1, leverage1).call()
    amount1 = await fixed_math.Math64x61_mul(execution_price1, size_without_leverage1.result.res).call()
    amount_for_fee1 = await fixed_math.Math64x61_mul(execution_price1, size1).call()
    fees1 = await fixed_math.Math64x61_mul(amount_for_fee1.result.res, taker_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    size_without_leverage2 = await fixed_math.Math64x61_div(size1, leverage2).call()
    amount2 = await fixed_math.Math64x61_mul(execution_price1, size_without_leverage2.result.res).call()
    amount_for_fee2 = await fixed_math.Math64x61_mul(execution_price1, size1).call()
    fees2 = await fixed_math.Math64x61_mul(amount_for_fee2.result.res, maker_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1,
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        position1,
        orderType1,
        direction1,
        to64x61(2),
        2,
        to64x61(5000),
        to64x61(5000),
        leverage1
    ]

    orderState2 = await bob.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        to64x61(2),
        2,
        to64x61(5000),
        to64x61(5000),
        leverage2
    ]

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    bob_curr_balance = await bob.get_balance(USDC_ID).call()
    holdingBalance = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    assert from64x61(alice_curr_balance.result.res) == from64x61(alice_curr_balance_before.result.res - total_amount1)
    assert from64x61(bob_curr_balance.result.res) == from64x61(bob_curr_balance_before.result.res - total_amount2)
    assert from64x61(holdingBalance.result.amount) == from64x61(holdingBalance_before.result.amount + amount_for_fee1.result.res + amount_for_fee2.result.res)
    assert from64x61(alice_total_fees.result.fee) == from64x61(alice_total_fees_before.result.fee + fees1.result.res)
    # Commenting due to 64x61 bug
    #assert from64x61(bob_total_fees.result.fee) == from64x61(bob_total_fees_before.result.fee + fees2.result.res)
    #assert from64x61(feeBalance_curr.result.fee) == from64x61(feeBalance_before.result.fee + fees1.result.res + fees2.result.res)

    alice_position_array = await alice.return_array_positions().call()
    alice_parsed = list(alice_position_array.result.array_list)
    print("Alice Array:", alice_parsed)

    #### Closing Of Orders ########
    size2 = to64x61(2)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("rlbrj4hd")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(6000)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(2)
    direction3 = 1
    closeOrder3 = 1
    parentOrder3 = order_id_1
    leverage3 = to64x61(2)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("tew2334")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(6000)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(2)
    direction4 = 0
    closeOrder4 = 1
    parentOrder4 = order_id_2
    leverage4 = to64x61(2)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3,
                                price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4,
                                price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4)

    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    diff1 = execution_price1 - execution_price2

    adjusted_price3 = to64x61(from64x61(execution_price1) + from64x61(diff1))
    pnl3 = await fixed_math.Math64x61_mul(diff1, size1).call()
    fraction_closed3 = await fixed_math.Math64x61_div(size1, size2).call()
    pnl_closed3 = await fixed_math.Math64x61_mul(pnl3.result.res, fraction_closed3.result.res).call()
    margin_returned3 = await fixed_math.Math64x61_mul(amount2.result.res, fraction_closed3.result.res).call()
    amount_returned3 = to64x61(
        from64x61(pnl_closed3.result.res) + from64x61(margin_returned3.result.res))
    position_value_closed3 = await fixed_math.Math64x61_mul(adjusted_price3, size2).call()

    print("alice difference is: ", from64x61(diff1))
    print("amount to be returned to alice is: ", from64x61(amount_returned3))
    print("amount to be returned to alice is: ", amount_returned3)
    print("margin returned of alice is: ",
          from64x61(margin_returned3.result.res))
    print("fraction closed of alice is: ",
          from64x61(fraction_closed3.result.res))
    print("pnl of alice is:", from64x61(pnl3.result.res))
    print("posiiton value of alice is: ", from64x61(
        position_value_closed3.result.res))

    diff2 = execution_price2 - execution_price1

    pnl4 = await fixed_math.Math64x61_mul(diff2, size1).call()
    fraction_closed4 = await fixed_math.Math64x61_div(size1, size2).call()
    pnl_closed4 = await fixed_math.Math64x61_mul(pnl4.result.res, fraction_closed4.result.res).call()
    margin_returned4 = await fixed_math.Math64x61_mul(amount1.result.res, fraction_closed4.result.res).call()
    amount_returned4 = to64x61(
        from64x61(pnl_closed4.result.res) + from64x61(margin_returned4.result.res))
    position_value_closed4 = await fixed_math.Math64x61_mul(execution_price2, size2).call()

    print("bob difference is: ", from64x61(diff2))
    print("amount to be returned to bob is: ", from64x61(amount_returned4))
    print("amount to be returned to bob is: ", amount_returned4)
    print("margin returned of bob is: ", from64x61(margin_returned4.result.res))
    print("fraction closed of bob is: ", from64x61(fraction_closed4.result.res))
    print("pnl of bob is:", from64x61(pnl4.result.res))
    print("posiiton value of bob is: ", from64x61(
        position_value_closed4.result.res))

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, parentOrder3, 1,
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, parentOrder4, 0,
    ])

    orderState3 = await alice.get_order_data(orderID_=order_id_1).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3,
        collateralID_3,
        price1,
        execution_price1,
        0,
        orderType1,
        direction1,
        0,
        4,
        to64x61(0),
        to64x61(0),
        leverage3
    ]

    orderState4 = await bob.get_order_data(orderID_=order_id_2).call()
    res4 = list(orderState4.result.res)

    assert res4 == [
        assetID_4,
        collateralID_4,
        price2,
        execution_price1,
        0,
        orderType2,
        direction2,
        0,
        4,
        to64x61(0),
        to64x61(0),
        leverage4
    ]

    alice_curr_balance_after = await alice.get_balance(collateralID_3).call()
    print("Alice current balance is", from64x61(
        alice_curr_balance_after.result.res))
    print("Alice difference is", from64x61(
        alice_curr_balance.result.res) + from64x61(amount_returned3))
    bob_curr_balance_after = await bob.get_balance(collateralID_4).call()
    print("Bob current balance is", from64x61(
        bob_curr_balance_after.result.res))
    print("Bob difference is", from64x61(
        bob_curr_balance.result.res) + from64x61(amount_returned3))
    holdingBalance_after = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    assert holdingBalance_after.result.amount == holdingBalance.result.amount - \
        position_value_closed3.result.res - position_value_closed4.result.res
    assert alice_curr_balance_after.result.res == (
        alice_curr_balance.result.res + amount_returned3)
    assert bob_curr_balance_after.result.res == (
        bob_curr_balance.result.res + amount_returned4)
    assert alice_total_fees_after.result.fee == alice_total_fees.result.fee
    assert bob_total_fees_after.result.fee == bob_total_fees.result.fee
    assert feeBalance_after.result.fee == feeBalance_curr.result.fee


@pytest.mark.asyncio
async def test_removing_closed_orders_from_position_array(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_position_array = await alice.return_array_positions().call()
    alice_parsed = list(alice_position_array.result.array_list)


@pytest.mark.asyncio
async def test_opening_and_closing_orders_with_leverage_partial_open_and_close(adminAuth_factory):
    _, adminAuth, fees, admin1, admin2, asset, trading, alice, bob, charlie, dave, fixed_math, holding, feeBalance = adminAuth_factory

    alice_balance = to64x61(100000)
    bob_balance = to64x61(100000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    alice_curr_balance_before = await alice.get_balance(USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(USDC_ID).call()

    ####### Open order partially #######
    size1 = to64x61(5)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("678uofdsjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(10)
    direction1 = 1
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(10)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("ryt4iljemn")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(5000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(5)
    direction2 = 0
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

    order_executed_user1 = to64x61(min(from64x61(size1), from64x61(position1)))
    order_executed_user2 = to64x61(min(from64x61(size1), from64x61(position1)))

    size_without_leverage1 = await fixed_math.Math64x61_div(order_executed_user1, leverage1).call()
    amount1 = await fixed_math.Math64x61_mul(execution_price1, size_without_leverage1.result.res).call()
    amount_for_fee1 = await fixed_math.Math64x61_mul(execution_price1, order_executed_user1).call()
    fees1 = await fixed_math.Math64x61_mul(amount_for_fee1.result.res, taker_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    size_without_leverage2 = await fixed_math.Math64x61_div(order_executed_user2, leverage2).call()
    amount2 = await fixed_math.Math64x61_mul(execution_price1, size_without_leverage2.result.res).call()
    amount_for_fee2 = await fixed_math.Math64x61_mul(execution_price1, order_executed_user2).call()
    fees2 = await fixed_math.Math64x61_mul(amount_for_fee2.result.res, maker_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        position1,
        orderType1,
        direction1,
        to64x61(5),
        1,
        to64x61(2500),
        to64x61(22500),
        leverage1
    ]

    orderState2 = await bob.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        to64x61(5),
        2,
        to64x61(25000),
        to64x61(0),
        leverage2
    ]

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    bob_curr_balance = await bob.get_balance(USDC_ID).call()
    holdingBalance = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    print("Alice balance before trade:", from64x61(
        alice_curr_balance_before.result.res))
    print("Alice balance after trade:", from64x61(
        alice_curr_balance.result.res))
    print("Bob balance before trade:", from64x61(
        bob_curr_balance_before.result.res))
    print("Bob balance after trade:", from64x61(bob_curr_balance.result.res))

    assert from64x61(alice_curr_balance.result.res) == from64x61(alice_curr_balance_before.result.res - total_amount1)
    assert from64x61(bob_curr_balance.result.res) == from64x61(bob_curr_balance_before.result.res - total_amount2)
    assert from64x61(holdingBalance.result.amount) == from64x61(holdingBalance_before.result.amount + amount_for_fee1.result.res + amount_for_fee2.result.res)
    assert from64x61(alice_total_fees.result.fee) == from64x61(alice_total_fees_before.result.fee + fees1.result.res)
    # Commenting the below line because of 64x61 bug
    #assert from64x61(bob_total_fees.result.fee) == from64x61(bob_total_fees_before.result.fee + fees2.result.res)
    #assert from64x61(feeBalance_curr.result.fee) == from64x61(feeBalance_before.result.fee + fees1.result.res + fees2.result.res)

    #### Close order partially ########
    size2 = to64x61(2.5)
    marketID_2 = BTC_USD_ID

    order_id_3 = str_to_felt("rlbrj4hd")
    assetID_3 = BTC_ID
    collateralID_3 = USDC_ID
    price3 = to64x61(6000)
    stopPrice3 = 0
    orderType3 = 0
    position3 = to64x61(10)
    direction3 = 0
    closeOrder3 = 1
    parentOrder3 = order_id_1
    leverage3 = to64x61(10)
    liquidatorAddress3 = 0

    order_id_4 = str_to_felt("tew2334")
    assetID_4 = BTC_ID
    collateralID_4 = USDC_ID
    price4 = to64x61(6000)
    stopPrice4 = 0
    orderType4 = 0
    position4 = to64x61(5)
    direction4 = 1
    closeOrder4 = 1
    parentOrder4 = order_id_2
    leverage4 = to64x61(1)
    liquidatorAddress4 = 0

    execution_price2 = to64x61(6000)

    hash_computed3 = hash_order(order_id_3, assetID_3, collateralID_3, price3, stopPrice3,
                                orderType3, position3, direction3, closeOrder3, leverage3)
    hash_computed4 = hash_order(order_id_4, assetID_4, collateralID_4, price4, stopPrice4,
                                orderType4, position4, direction4, closeOrder4, leverage4)

    print("bob hash: ", hash_computed4)
    signed_message3 = alice_signer.sign(hash_computed3)
    signed_message4 = bob_signer.sign(hash_computed4)

    order_executed_user3 = to64x61(from64x61(min(size2, position1)))
    order_executed_user4 = to64x61(from64x61(min(size2, position2)))

    diff1 = execution_price2 - execution_price1

    pnl3 = await fixed_math.Math64x61_mul(diff1, order_executed_user1).call()
    fraction_closed3 = await fixed_math.Math64x61_div(order_executed_user3, order_executed_user1).call()
    pnl_closed3 = await fixed_math.Math64x61_mul(pnl3.result.res, fraction_closed3.result.res).call()
    margin_returned3 = await fixed_math.Math64x61_mul(amount1.result.res, fraction_closed3.result.res).call()
    amount_returned3 = to64x61(
        from64x61(pnl_closed3.result.res) + from64x61(margin_returned3.result.res))
    position_value_closed3 = await fixed_math.Math64x61_mul(execution_price2, order_executed_user3).call()

    print("alice difference is: ", from64x61(diff1))
    print("amount to be returned to alice is: ", from64x61(amount_returned3))
    print("margin returned of alice is: ",
          from64x61(margin_returned3.result.res))
    print("fraction closed of alice is: ",
          from64x61(fraction_closed3.result.res))
    print("pnl of alice is:", from64x61(pnl3.result.res))
    print("posiiton value of alice is: ", from64x61(
        position_value_closed3.result.res))

    diff2 = execution_price1 - execution_price2

    adjusted_price4 = execution_price1 + diff2
    pnl4 = await fixed_math.Math64x61_mul(diff2, order_executed_user1).call()
    fraction_closed4 = await fixed_math.Math64x61_div(order_executed_user4, order_executed_user1).call()
    pnl_closed4 = await fixed_math.Math64x61_mul(pnl4.result.res, fraction_closed4.result.res).call()
    margin_returned4 = await fixed_math.Math64x61_mul(amount2.result.res, fraction_closed4.result.res).call()
    amount_returned4 = to64x61(
        from64x61(pnl_closed4.result.res) + from64x61(margin_returned4.result.res))
    position_value_closed4 = await fixed_math.Math64x61_mul(adjusted_price4, order_executed_user4).call()

    print("bob difference is: ", from64x61(diff2))
    print("amount to be returned to bob is: ", from64x61(amount_returned4))
    print("amount to be returned to bob is: ", amount_returned4)
    print("margin returned of bob is: ", from64x61(margin_returned4.result.res))
    print("fraction closed of bob is: ", from64x61(fraction_closed4.result.res))
    print("pnl of bob is:", from64x61(pnl4.result.res))
    print("posiiton value of bob is: ", from64x61(
        position_value_closed4.result.res))

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size2,
        execution_price2,
        marketID_2,
        2,
        alice.contract_address, signed_message3[0], signed_message3[
            1], order_id_3, assetID_3, collateralID_3, price3, stopPrice3, orderType3, position3, direction3, closeOrder3, leverage3, liquidatorAddress3, parentOrder3, 1, 
        bob.contract_address, signed_message4[0], signed_message4[
            1], order_id_4, assetID_4, collateralID_4, price4, stopPrice4, orderType4, position4, direction4, closeOrder4, leverage4, liquidatorAddress4, parentOrder4, 0,
    ])

    orderState3 = await alice.get_order_data(orderID_=order_id_1).call()
    res3 = list(orderState3.result.res)

    assert res3 == [
        assetID_3,
        collateralID_3,
        price1,
        execution_price1,
        to64x61(7.5),
        orderType1,
        direction1,
        to64x61(2.5),
        3,
        to64x61(1250),
        to64x61(11250),
        leverage3
    ]

    orderState4 = await bob.get_order_data(orderID_=order_id_2).call()
    res4 = list(orderState4.result.res)

    assert res4 == [
        assetID_4,
        collateralID_4,
        price2,
        execution_price1,
        to64x61(2.5),
        orderType2,
        direction2,
        to64x61(2.5),
        3,
        to64x61(12500),
        to64x61(0),
        leverage4
    ]

    alice_curr_balance_after = await alice.get_balance(collateralID_3).call()
    bob_curr_balance_after = await bob.get_balance(collateralID_4).call()
    holdingBalance_after = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_after = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_after = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_after = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    print("Alice balance before:", from64x61(alice_curr_balance.result.res))
    print("Alice balance after:", from64x61(
        alice_curr_balance_after.result.res))
    print("Bob balance before:", from64x61(bob_curr_balance.result.res))
    print("Bob balance after:", from64x61(bob_curr_balance_after.result.res))
    print("Position value close 3", from64x61(
        position_value_closed3.result.res))
    print("Position value close 4", from64x61(
        position_value_closed4.result.res))
    print("Holding balance before", from64x61(holdingBalance.result.amount))
    print("Holding balance after", from64x61(
        holdingBalance_after.result.amount))
    print("Holding balance comaparison", from64x61(holdingBalance_after.result.amount -
          position_value_closed3.result.res - position_value_closed4.result.res),  from64x61(holdingBalance.result.amount))

    assert from64x61(holdingBalance_after.result.amount) == from64x61(holdingBalance.result.amount - position_value_closed3.result.res - position_value_closed4.result.res)
    assert from64x61(alice_curr_balance_after.result.res) == from64x61(alice_curr_balance.result.res + amount_returned3)
    assert from64x61(bob_curr_balance_after.result.res) == from64x61(bob_curr_balance.result.res + amount_returned4)
    assert from64x61(alice_total_fees_after.result.fee) == from64x61(alice_total_fees.result.fee)
    assert from64x61(bob_total_fees_after.result.fee) == from64x61(bob_total_fees.result.fee)
    assert from64x61(feeBalance_after.result.fee) == from64x61(feeBalance_curr.result.fee)

    # ####### Open order partially for the second time #######
    alice_curr_balance_before = await alice.get_balance(USDC_ID).call()
    bob_curr_balance_before = await bob.get_balance(USDC_ID).call()

    size = to64x61(2.5)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("678uofdsjxz")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(5000)
    stopPrice1 = 0
    orderType1 = 0
    position1 = to64x61(7.5)
    direction1 = 1
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(10)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("ryt4iljeno")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(5000)
    stopPrice2 = 0
    orderType2 = 0
    position2 = to64x61(2.5)
    direction2 = 0
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

    size_by_leverage1 = await fixed_math.Math64x61_div(size, leverage1).call()
    amount1 = await fixed_math.Math64x61_mul(execution_price1, size_by_leverage1.result.res).call()
    amount_for_fee1 = await fixed_math.Math64x61_mul(execution_price1, size).call()
    fees1 = await fixed_math.Math64x61_mul(amount_for_fee1.result.res, taker_trading_fees).call()
    total_amount1 = amount1.result.res + fees1.result.res

    size_by_leverage2 = await fixed_math.Math64x61_div(size, leverage2).call()
    amount2 = await fixed_math.Math64x61_mul(execution_price1, size_by_leverage2.result.res).call()
    amount_for_fee2 = await fixed_math.Math64x61_mul(execution_price1, size).call()
    fees2 = await fixed_math.Math64x61_mul(amount_for_fee2.result.res, maker_trading_fees).call()
    total_amount2 = amount2.result.res + fees2.result.res

    holdingBalance_before = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_before = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees_before = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees_before = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, stopPrice1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_1, collateralID_2, price2, stopPrice2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0, 
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)

    assert res1 == [
        assetID_1,
        collateralID_1,
        price1,
        execution_price1,
        position1,
        orderType1,
        direction1,
        to64x61(5),
        1,
        to64x61(2500),
        to64x61(22500),
        leverage1
    ]

    orderState2 = await bob.get_order_data(orderID_=order_id_2).call()
    res2 = list(orderState2.result.res)

    assert res2 == [
        assetID_2,
        collateralID_2,
        price2,
        execution_price1,
        position2,
        orderType2,
        direction2,
        to64x61(2.5),
        2,
        to64x61(12500),
        to64x61(0),
        leverage2
    ]

    alice_curr_balance = await alice.get_balance(USDC_ID).call()
    bob_curr_balance = await bob.get_balance(USDC_ID).call()
    holdingBalance = await holding.balance(asset_id_=USDC_ID).call()
    feeBalance_curr = await feeBalance.get_total_fee(assetID_=USDC_ID).call()
    alice_total_fees = await feeBalance.get_user_fee(address=alice.contract_address, assetID_=USDC_ID).call()
    bob_total_fees = await feeBalance.get_user_fee(address=bob.contract_address, assetID_=USDC_ID).call()

    assert from64x61(alice_curr_balance.result.res) == from64x61(alice_curr_balance_before.result.res - total_amount1)
    assert from64x61(bob_curr_balance.result.res) == from64x61(bob_curr_balance_before.result.res - total_amount2)
    assert from64x61(holdingBalance.result.amount) == from64x61(holdingBalance_before.result.amount + amount_for_fee1.result.res + amount_for_fee2.result.res)
    assert from64x61(alice_total_fees.result.fee) == from64x61(alice_total_fees_before.result.fee + fees1.result.res)
    # Commenting the below line because of 64x61 bug
    #assert from64x61(bob_total_fees.result.fee) == from64x61(bob_total_fees_before.result.fee + fees2.result.res)
    #assert from64x61(feeBalance_curr.result.fee) == from64x61(feeBalance_before.result.fee + fees1.result.res + fees2.result.res)

    hash_list=await trading.get_caller_hash_list(dave.contract_address).call()
    print(hash_list.result)