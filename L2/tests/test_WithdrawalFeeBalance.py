from copyreg import constructor
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address, L1_ZKX_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
dave_signer = Signer(123456789987654326)

maker_trading_fees = to64x61(0.0002 * 0.97)
taker_trading_fees = to64x61(0.0005 * 0.97)

BTC_ID = str_to_felt("32f0406jz7qj8")
USDC_ID = str_to_felt("fghj3am52qpzsib")
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    ### Deploy infrastructure (Part 1)
    admin1 = await starknet_service.deploy(ContractType.Account, [
        admin1_signer.public_key, 
        L1_dummy_address, 
        0, 
        1, 
        L1_ZKX_dummy_address
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        admin2_signer.public_key, 
        L1_dummy_address, 
        0, 
        1, 
        L1_ZKX_dummy_address
    ])
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    fees = await starknet_service.deploy(ContractType.TradingFees, [registry.contract_address, 1])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])

    ### Deploy user accounts
    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1,
        L1_ZKX_dummy_address
    )
    alice = await account_factory.deploy_account(alice_signer.public_key)
    bob = await account_factory.deploy_account(bob_signer.public_key)
    dave = await account_factory.deploy_account(dave_signer.public_key)

    ### Deploy infrastructure (Part 2)
    fixed_math = await starknet_service.deploy(ContractType.Math_64x61, [])
    holding = await starknet_service.deploy(ContractType.Holding, [registry.contract_address, 1])
    feeBalance = await starknet_service.deploy(ContractType.FeeBalance, [registry.contract_address, 1])
    market = await starknet_service.deploy(ContractType.Markets, [registry.contract_address, 1])
    trading = await starknet_service.deploy(ContractType.Trading, [registry.contract_address, 1])
    feeDiscount = await starknet_service.deploy(ContractType.FeeDiscount, [])
    accountRegistry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    withdrawFeeBalance = await starknet_service.deploy(ContractType.WithdrawalFeeBalance, [registry.contract_address, 1])

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Access 2 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [3, 1, feeDiscount.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [4, 1, fees.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [5, 1, trading.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [6, 1, feeBalance.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [7, 1, holding.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, accountRegistry.contract_address])

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
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [BTC_ID, 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'addAsset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'addMarket', [BTC_USD_ID, BTC_ID, USDC_ID, 0, 1, 10])

    # Fund the Holding contract
    await admin1_signer.send_transaction(admin1, holding.contract_address, 'fund', [USDC_ID, to64x61(1000000)])

    # Set the balance of admin1 and admin2
    await admin1_signer.send_transaction(admin1, admin1.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    await admin2_signer.send_transaction(admin2, admin2.contract_address, 'set_balance', [USDC_ID, to64x61(1000000)])
    return adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawFeeBalance


@pytest.mark.asyncio
async def test_registering_of_users(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawFeeBalance = adminAuth_factory

    alice_balance = to64x61(1000)
    bob_balance = to64x61(1000)

    await admin1_signer.send_transaction(admin1, alice.contract_address, 'set_balance', [USDC_ID, alice_balance])
    await admin2_signer.send_transaction(admin2, bob.contract_address, 'set_balance', [USDC_ID, bob_balance])

    ####### Opening of Orders #######
    size1 = to64x61(1)
    marketID_1 = BTC_USD_ID

    order_id_1 = str_to_felt("pqlkzc3434")
    assetID_1 = BTC_ID
    collateralID_1 = USDC_ID
    price1 = to64x61(500)
    orderType1 = 0
    position1 = to64x61(1)
    direction1 = 0
    closeOrder1 = 0
    parentOrder1 = 0
    leverage1 = to64x61(1)
    liquidatorAddress1 = 0

    order_id_2 = str_to_felt("p21pdfs12mfd")
    assetID_2 = BTC_ID
    collateralID_2 = USDC_ID
    price2 = to64x61(500)
    orderType2 = 0
    position2 = to64x61(1)
    direction2 = 1
    closeOrder2 = 0
    parentOrder2 = 0
    leverage2 = to64x61(1)
    liquidatorAddress2 = 0

    execution_price1 = to64x61(500)

    hash_computed1 = hash_order(order_id_1, assetID_1, collateralID_1,
                                price1, orderType1, position1, direction1, closeOrder1, leverage1)
    hash_computed2 = hash_order(order_id_2, assetID_2, collateralID_2,
                                price2, orderType2, position2, direction2, closeOrder2, leverage2)

    signed_message1 = alice_signer.sign(hash_computed1)
    signed_message2 = bob_signer.sign(hash_computed2)

    res = await dave_signer.send_transaction(dave, trading.contract_address, "execute_batch", [
        size1,
        execution_price1,
        marketID_1,
        2,
        alice.contract_address, signed_message1[0], signed_message1[
            1], order_id_1, assetID_1, collateralID_1, price1, orderType1, position1, direction1, closeOrder1, leverage1, liquidatorAddress1, parentOrder1, 1, 
        bob.contract_address, signed_message2[0], signed_message2[
            1], order_id_2, assetID_2, collateralID_2, price2, orderType2, position2, direction2, closeOrder2, leverage2, liquidatorAddress2, parentOrder2, 0,
    ])

    orderState1 = await alice.get_order_data(orderID_=order_id_1).call()
    res1 = list(orderState1.result.res)
    print(res1)


@pytest.mark.asyncio
async def test_update_withdrawal_fee_mapping(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawFeeBalance = adminAuth_factory

    await alice_signer.send_transaction(alice, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [alice.contract_address, USDC_ID, 10])

    execution_info = await withdrawFeeBalance.get_total_withdrawal_fee(USDC_ID).call()
    assert execution_info.result.fee == 10

    execution_info = await withdrawFeeBalance.get_user_withdrawal_fee(alice.contract_address, USDC_ID).call()
    assert execution_info.result.fee == 10


@pytest.mark.asyncio
async def test_update_withdrawal_fee_mapping_different_user(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawFeeBalance = adminAuth_factory
    await alice_signer.send_transaction(alice, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [alice.contract_address, USDC_ID, 10])

    execution_info = await withdrawFeeBalance.get_total_withdrawal_fee(USDC_ID).call()
    assert execution_info.result.fee == 20

    execution_info = await withdrawFeeBalance.get_user_withdrawal_fee(alice.contract_address, USDC_ID).call()
    assert execution_info.result.fee == 20

    await bob_signer.send_transaction(bob, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [bob.contract_address, USDC_ID, 10])

    execution_info = await withdrawFeeBalance.get_total_withdrawal_fee(USDC_ID).call()
    assert execution_info.result.fee == 30

    execution_info = await withdrawFeeBalance.get_user_withdrawal_fee(alice.contract_address, USDC_ID).call()
    assert execution_info.result.fee == 20

    execution_info = await withdrawFeeBalance.get_user_withdrawal_fee(bob.contract_address, USDC_ID).call()
    assert execution_info.result.fee == 10


@pytest.mark.asyncio
async def test_revert_Unauthorized_Tx(adminAuth_factory):
    adminAuth, fees, admin1, admin2, asset, trading, alice, bob, dave, fixed_math, holding, feeBalance, accountRegistry, withdrawFeeBalance = adminAuth_factory
    assert_revert(lambda: dave_signer.send_transaction(dave, withdrawFeeBalance.contract_address, 'update_withdrawal_fee_mapping', [alice.contract_address, USDC_ID, 10]))