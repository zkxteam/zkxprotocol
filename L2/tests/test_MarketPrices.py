import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, str_to_felt, MAX_UINT256, assert_revert, to64x61
from utils_links import DEFAULT_LINK_1, prepare_starknet_string
from utils_asset import AssetID, build_asset_properties
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()

@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(admin1_signer.public_key)
    admin2 = await account_factory.deploy_account(admin2_signer.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    market = await starknet_service.deploy(ContractType.Markets, [registry.contract_address, 1])
    market_prices = await starknet_service.deploy(ContractType.MarketPrices, [registry.contract_address, 1])

    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])

    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [5, 1, admin1.contract_address])

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

    TESLA_properties = build_asset_properties(
        id=AssetID.TSLA,
        asset_version=0,
        short_name=str_to_felt("TESLA"),
        is_tradable=1,
        is_collateral=0,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', TESLA_properties)

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USD_ID, AssetID.BTC, AssetID.USDC, 1, 0, 10, 1, 0, 1, 0, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [ETH_USD_ID, AssetID.ETH, AssetID.USDC, 1, 0, 10, 1, 0, 1, 0, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [TSLA_USD_ID, AssetID.TSLA, AssetID.USDC, 1, 0, 10, 1, 0, 1, 0, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))

    return adminAuth, market_prices, admin1, admin2

@pytest.mark.asyncio
async def test_update_market_price(adminAuth_factory):
    adminAuth, market_prices, admin1, admin2 = adminAuth_factory

    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_market_price', [BTC_USD_ID, 500])
    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_market_price', [ETH_USD_ID, 1000])

    fetched_market_prices1 = await market_prices.get_market_price(BTC_USD_ID).call()
    assert fetched_market_prices1.result.market_price == 500

    fetched_market_prices2 = await market_prices.get_market_price(ETH_USD_ID).call()
    assert fetched_market_prices2.result.market_price == 1000

@pytest.mark.asyncio
async def test_unauthorized_add_market_price_to_market_prices(adminAuth_factory):
    adminAuth, market_prices, admin1, admin2 = adminAuth_factory

    await assert_revert(admin2_signer.send_transaction(admin2, market_prices.contract_address, 'update_market_price', [BTC_USD_ID, 500]),reverted_with="MarketPrices: Unauthorized caller for updating market price")

@pytest.mark.asyncio
async def test_update_multiple_market_prices(adminAuth_factory):
    adminAuth, market_prices, admin1, admin2 = adminAuth_factory

    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_multiple_market_prices', [2, BTC_USD_ID, 1000, ETH_USD_ID, 100])

    fetched_market_prices1 = await market_prices.get_market_price(BTC_USD_ID).call()
    assert fetched_market_prices1.result.market_price == 1000

    fetched_market_prices2 = await market_prices.get_market_price(ETH_USD_ID).call()
    assert fetched_market_prices2.result.market_price == 100

    prices = await market_prices.get_all_market_prices().call()
    assert prices.result.market_prices_list[0].price==100
    assert prices.result.market_prices_list[1].price==1000

@pytest.mark.asyncio
async def test_get_multiple_market_prices(adminAuth_factory):
    adminAuth, market_prices, admin1, admin2 = adminAuth_factory

    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_multiple_market_prices', [2, BTC_USD_ID, 1000, ETH_USD_ID, 0])

    prices = await market_prices.get_all_market_prices().call()
    assert prices.result.market_prices_list[0].price==1000

    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_multiple_market_prices', [1, TSLA_USD_ID, 10])

    prices = await market_prices.get_all_market_prices().call()
    assert prices.result.market_prices_list[0].price==10
    assert prices.result.market_prices_list[1].price==1000

    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_multiple_market_prices', [1, ETH_USD_ID, 500])
    prices = await market_prices.get_all_market_prices().call()
    assert prices.result.market_prices_list[0].price==10
    assert prices.result.market_prices_list[1].price==500
    assert prices.result.market_prices_list[2].price==1000

@pytest.mark.asyncio
async def test_unauthorized_update_multiple_market_prices(adminAuth_factory):
    adminAuth, market_prices, admin1, admin2 = adminAuth_factory

    await assert_revert(admin2_signer.send_transaction(admin2, market_prices.contract_address, 'update_market_price', [2, BTC_USD_ID, 300, ETH_USD_ID, 100]))