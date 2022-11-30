import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, str_to_felt, MAX_UINT256, assert_revert, to64x61
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)

BTC_ID = str_to_felt("32f0406jz7qj8")
ETH_ID = str_to_felt("65ksgn23nv")
USDC_ID = str_to_felt("fghj3am52qpzsib")
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")


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
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [BTC_ID, 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [ETH_ID, 0, str_to_felt("ETH"), str_to_felt("Etherum"), 1, 0, 18, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USD_ID, BTC_ID, USDC_ID, to64x61(10), 1, 0, 10, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', [ETH_USD_ID, ETH_ID, USDC_ID, to64x61(10), 1, 0, 10, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])

    return adminAuth, market_prices, admin1, admin2

@pytest.mark.asyncio
async def test_update_market_price(adminAuth_factory):
    adminAuth, market_prices, admin1, admin2 = adminAuth_factory

    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_market_price', [BTC_USD_ID, 500])
    await admin1_signer.send_transaction(admin1, market_prices.contract_address, 'update_market_price', [ETH_USD_ID, 1000])

    fetched_market_prices1 = await market_prices.get_market_price(BTC_USD_ID).call()
    assert fetched_market_prices1.result.market_price.asset_id == BTC_ID
    assert fetched_market_prices1.result.market_price.collateral_id == USDC_ID
    assert fetched_market_prices1.result.market_price.price == 500

    fetched_market_prices2 = await market_prices.get_market_price(ETH_USD_ID).call()
    assert fetched_market_prices2.result.market_price.asset_id == ETH_ID
    assert fetched_market_prices2.result.market_price.collateral_id == USDC_ID
    assert fetched_market_prices2.result.market_price.price == 1000

@pytest.mark.asyncio
async def test_unauthorized_add_market_price_to_market_prices(adminAuth_factory):
    adminAuth, market_prices, admin1, admin2 = adminAuth_factory

    await assert_revert(admin2_signer.send_transaction(admin2, market_prices.contract_address, 'update_market_price', [BTC_USD_ID, 500]),reverted_with="MarketPrices: Unauthorized caller for updating market price")