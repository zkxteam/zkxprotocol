import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, str_to_felt, MAX_UINT256, assert_revert, to64x61, assert_event_emitted
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)

USDC_ID = str_to_felt("fghj3am52qpzsib")
USDT_ID = str_to_felt("65ksgn23nv")

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
    collateral_prices = await starknet_service.deploy(ContractType.CollateralPrices, [registry.contract_address, 1])

    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 7, 1])

    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [13, 1, collateral_prices.contract_address])

    # Add assets
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [USDT_ID, 0, str_to_felt("USDT"), str_to_felt("USDT"), 1, 0, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', [USDC_ID, 0, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    return adminAuth, collateral_prices, admin1, admin2


@pytest.mark.asyncio
async def test_update_collateral_price_unauthorized_user(adminAuth_factory):
    adminAuth, collateral_prices, admin1, admin2 = adminAuth_factory

    await assert_revert(admin2_signer.send_transaction(admin2, collateral_prices.contract_address, 'update_collateral_price', [USDC_ID, 500]))


@pytest.mark.asyncio
async def test_update_negative_collateral_price(adminAuth_factory):
    adminAuth, collateral_prices, admin1, admin2 = adminAuth_factory

    await assert_revert(admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [USDC_ID, -500]))

@pytest.mark.asyncio
async def test_update_collateral_price(adminAuth_factory):
    adminAuth, collateral_prices, admin1, admin2 = adminAuth_factory

    tx_exec_info_1 = await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [USDC_ID, 500])

    assert_event_emitted(
        tx_exec_info_1,
        from_address = collateral_prices.contract_address,
        name = 'update_collateral_price_called',
        data=[
            USDC_ID,
            500
        ]
    )

    tx_exec_info_2 = await admin1_signer.send_transaction(admin1, collateral_prices.contract_address, 'update_collateral_price', [USDT_ID, 1000])

    assert_event_emitted(
        tx_exec_info_2,
        from_address = collateral_prices.contract_address,
        name = 'update_collateral_price_called',
        data=[
            USDT_ID,
            1000
        ]
    )

    fetched_collateral_prices1 = await collateral_prices.get_collateral_price(USDC_ID).call()
    assert fetched_collateral_prices1.result.collateral_price.price_in_usd == 500

    fetched_collateral_prices2 = await collateral_prices.get_collateral_price(USDT_ID).call()
    assert fetched_collateral_prices2.result.collateral_price.price_in_usd == 1000
