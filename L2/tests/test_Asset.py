import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3


counter = 0
# Generates unique asset params (id, ticker and name) to avoid conflicts
def generate_asset_info():
    global counter
    counter += 1
    id = f"32f0406jz7qj8_${counter}"
    ticker = f"ETH_${counter}"
    name = f"Ethereum_${counter}"
    return str_to_felt(id), str_to_felt(ticker), str_to_felt(name)

def build_default_asset_properties(id, ticker, name):
    return [
        id, # id
        0, # asset_version
        ticker, # ticker
        name, # short_name
        0, # tradable
        0, # collateral
        18, # token_decimal
        0, # metadata_id
        1, # tick_size
        1, # step_size
        10, # minimum_order_size
        1, # minimum_leverage
        5, # maximum_leverage
        3, # currently_allowed_leverage
        1, # maintenance_margin_fraction
        1, # initial_margin_fraction
        1, # incremental_initial_margin_fraction
        100, # incremental_position_size
        1000, # baseline_position_size
        10000 # maximum_position_size
    ]


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
    
    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    user1 = await account_factory.deploy_account(signer3.public_key)

    # Deploy infrustructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    return adminAuth, registry, asset, admin1, admin2, user1

@pytest.fixture(scope='function')
async def fresh_asset_contract(starknet_service: StarknetService, adminAuth_factory):
    adminAuth, registry, _, admin1, _, user1 = adminAuth_factory
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    return admin1, asset


@pytest.mark.asyncio
async def test_get_admin_mapping(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 1).call()
    assert execution_info.result.allowed == 1

    execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 1).call()
    assert execution_info1.result.allowed == 0


@pytest.mark.asyncio
async def test_adding_asset_by_admin(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    execution_info = await asset.getAsset(asset_id).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == asset_ticker
    assert fetched_asset.short_name == asset_name
    assert fetched_asset.tradable == 0
    assert fetched_asset.collateral == 0
    assert fetched_asset.token_decimal == 18
    assert fetched_asset.metadata_id == 0
    assert fetched_asset.asset_version == 0
    assert fetched_asset.tick_size == 1
    assert fetched_asset.step_size == 1
    assert fetched_asset.minimum_order_size == 10
    assert fetched_asset.minimum_leverage == 1
    assert fetched_asset.maximum_leverage == 5
    assert fetched_asset.currently_allowed_leverage == 3
    assert fetched_asset.maintenance_margin_fraction == 1
    assert fetched_asset.initial_margin_fraction == 1
    assert fetched_asset.incremental_initial_margin_fraction == 1
    assert fetched_asset.incremental_position_size == 100
    assert fetched_asset.baseline_position_size == 1000
    assert fetched_asset.maximum_position_size == 10000

    assets = await asset.returnAllAssets().call()
    parsed_list = list(assets.result.array_list)[0]

    assert parsed_list.id == asset_id
    assert parsed_list.asset_version == 0
    assert parsed_list.ticker == asset_ticker
    assert parsed_list.short_name == asset_name
    assert parsed_list.tradable == 0
    assert parsed_list.collateral == 0
    assert parsed_list.token_decimal == 18
    assert parsed_list.metadata_id == 0
    assert parsed_list.tick_size == 1
    assert parsed_list.step_size == 1
    assert parsed_list.minimum_order_size == 10
    assert parsed_list.minimum_leverage == 1
    assert parsed_list.maximum_leverage == 5
    assert parsed_list.currently_allowed_leverage == 3
    assert parsed_list.maintenance_margin_fraction == 1
    assert parsed_list.initial_margin_fraction == 1
    assert parsed_list.incremental_initial_margin_fraction == 1
    assert parsed_list.incremental_position_size == 100
    assert parsed_list.baseline_position_size == 1000
    assert parsed_list.maximum_position_size == 10000


@pytest.mark.asyncio
async def test_adding_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await assert_revert(
        signer3.send_transaction(user1, asset.contract_address, 'addAsset', asset_properties)
    )


@pytest.mark.asyncio
async def test_modifying_asset_by_admin(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    new_asset_name = str_to_felt("NEW_NAME")
    new_tradable_status = 1
    new_collateral = 1
    new_token_decimal = 10
    new_metadata_id = 1

    await signer1.send_transaction(admin1, asset.contract_address, 'modify_core_settings', [
        asset_id,
        new_asset_name,
        new_tradable_status,
        new_collateral,
        new_token_decimal,
        new_metadata_id
    ])

    execution_info = await asset.getAsset(asset_id).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == asset_ticker
    assert fetched_asset.short_name == new_asset_name
    assert fetched_asset.tradable == new_tradable_status
    assert fetched_asset.collateral == new_collateral
    assert fetched_asset.token_decimal == new_token_decimal
    assert fetched_asset.metadata_id == new_metadata_id
    assert fetched_asset.asset_version == 0


@pytest.mark.asyncio
async def test_modifying_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    assert_revert(lambda: 
        signer3.send_transaction(user1, asset.contract_address, 'modify_core_settings', [
            asset_id, 
            asset_ticker, 
            asset_name, 
            0, 
            1, 
            18, 
            1
        ])
    )


@pytest.mark.asyncio
async def test_modifying_trade_settings_by_admin(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    new_tick_size = 2
    new_step_size = 2
    new_minimum_order_size = 11
    new_minimum_leverage = 2
    new_maximum_leverage = 6
    new_currently_allowed_leverage = 4
    new_maintenance_margin_fraction = 2
    new_initial_margin_fraction = 2
    new_incremental_initial_margin_fraction = 2
    new_incremental_position_size = 200
    new_baseline_position_size = 2000
    new_maximum_position_size = 20000

    await signer1.send_transaction(admin1, asset.contract_address, 'modify_trade_settings', [
        asset_id, 
        new_tick_size, 
        new_step_size, 
        new_minimum_order_size, 
        new_minimum_leverage, 
        new_maximum_leverage, 
        new_currently_allowed_leverage, 
        new_maintenance_margin_fraction, 
        new_initial_margin_fraction, 
        new_incremental_initial_margin_fraction, 
        new_incremental_position_size, 
        new_baseline_position_size, 
        new_maximum_position_size
    ])

    execution_info = await asset.getAsset(asset_id).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == asset_ticker
    assert fetched_asset.short_name == asset_name
    assert fetched_asset.tradable == 0
    assert fetched_asset.collateral == 0
    assert fetched_asset.token_decimal == 18
    assert fetched_asset.metadata_id == 0
    assert fetched_asset.tick_size == new_tick_size
    assert fetched_asset.step_size == new_step_size
    assert fetched_asset.minimum_order_size == new_minimum_order_size
    assert fetched_asset.minimum_leverage == new_minimum_leverage
    assert fetched_asset.maximum_leverage == new_maximum_leverage
    assert fetched_asset.currently_allowed_leverage == new_currently_allowed_leverage
    assert fetched_asset.maintenance_margin_fraction == new_maintenance_margin_fraction
    assert fetched_asset.initial_margin_fraction == new_initial_margin_fraction
    assert fetched_asset.incremental_initial_margin_fraction == new_incremental_initial_margin_fraction
    assert fetched_asset.incremental_position_size == new_incremental_position_size
    assert fetched_asset.baseline_position_size == new_baseline_position_size
    assert fetched_asset.maximum_position_size == new_maximum_position_size
    assert fetched_asset.asset_version == 1

    execution_info1 = await asset.get_version().call()
    version = execution_info1.result.version
    assert version == 1


@pytest.mark.asyncio
async def test_modifying_trade_settings_by_unauthorized_user(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    assert_revert(lambda: 
        signer3.send_transaction(user1, asset.contract_address, 'modify_trade_settings', [
            asset_id, 2, 2, 11, 2, 6, 4, 2, 2, 2, 200, 2000, 20000
        ])
    )


@pytest.mark.asyncio
async def test_removing_asset_by_admin(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    await signer1.send_transaction(admin1, asset.contract_address, 'removeAsset', [asset_id])

    await assert_revert(
        asset.getAsset(asset_id).call()
    )


@pytest.mark.asyncio
async def test_removing_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    assert_revert(lambda: 
        signer3.send_transaction(user1, asset.contract_address, 'removeAsset', [asset_id])
    )


@pytest.mark.asyncio
async def test_modifying_trade_settings_by_admin_twice(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    new_tick_size = 2
    new_step_size = 2
    new_minimum_order_size = 11
    new_minimum_leverage = 2
    new_maximum_leverage = 6
    new_currently_allowed_leverage = 4
    new_maintenance_margin_fraction = 2
    new_initial_margin_fraction = 2
    new_incremental_initial_margin_fraction = 2
    new_incremental_position_size = 200
    new_baseline_position_size = 2000
    new_maximum_position_size = 20000

    modify_trade_settings_payload = [
        asset_id,
        new_tick_size,
        new_step_size,
        new_minimum_order_size,
        new_minimum_leverage,
        new_maximum_leverage,
        new_currently_allowed_leverage,
        new_maintenance_margin_fraction,
        new_initial_margin_fraction,
        new_incremental_initial_margin_fraction,
        new_incremental_position_size,
        new_baseline_position_size,
        new_maximum_position_size
    ]

    await signer1.send_transaction(admin1, asset.contract_address, 'modify_trade_settings', modify_trade_settings_payload)
    await signer1.send_transaction(admin1, asset.contract_address, 'modify_trade_settings', modify_trade_settings_payload)

    execution_info = await asset.getAsset(asset_id).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == asset_ticker
    assert fetched_asset.short_name == asset_name
    assert fetched_asset.tradable == 0
    assert fetched_asset.collateral == 0
    assert fetched_asset.metadata_id == 0
    assert fetched_asset.tick_size == new_tick_size
    assert fetched_asset.step_size == new_step_size
    assert fetched_asset.minimum_order_size == new_minimum_order_size
    assert fetched_asset.minimum_leverage == new_minimum_leverage
    assert fetched_asset.maximum_leverage == new_maximum_leverage
    assert fetched_asset.currently_allowed_leverage == new_currently_allowed_leverage
    assert fetched_asset.maintenance_margin_fraction == new_maintenance_margin_fraction
    assert fetched_asset.initial_margin_fraction == new_initial_margin_fraction
    assert fetched_asset.incremental_initial_margin_fraction == new_incremental_initial_margin_fraction
    assert fetched_asset.incremental_position_size == new_incremental_position_size
    assert fetched_asset.baseline_position_size == new_baseline_position_size
    assert fetched_asset.maximum_position_size == new_maximum_position_size
    assert fetched_asset.asset_version == 2

    execution_info1 = await asset.get_version().call()
    version = execution_info1.result.version
    assert version == 3


@pytest.mark.asyncio
async def test_retrieve_assets(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    assets_before = await asset.returnAllAssets().call()
    len_before = len(list(assets_before.result.array_list))

    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)

    assets_after = await asset.returnAllAssets().call()
    len_after = len(list(assets_after.result.array_list))

    assert len_after == len_before + 1

@pytest.mark.asyncio
async def test_can_add_five_different_assets(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    # Get number of assets before
    assets_before = await asset.returnAllAssets().call()
    len_before = len(list(assets_before.result.array_list))

    # Add 1st
    asset_id_1, asset_ticker_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_ticker_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)

    # Add 2nd
    asset_id_2, asset_ticker_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_ticker_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_ticker_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_ticker_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_3)

    # Add 4th
    asset_id_4, asset_ticker_4, asset_name_4 = generate_asset_info()
    asset_properties_4 = build_default_asset_properties(asset_id_4, asset_ticker_4, asset_name_4)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_4)

    # Add 5th
    asset_id_5, asset_ticker_5, asset_name_5 = generate_asset_info()
    asset_properties_5 = build_default_asset_properties(asset_id_5, asset_ticker_5, asset_name_5)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_5)

    # Get number of assets after
    assets_after = await asset.returnAllAssets().call()
    len_after = len(list(assets_after.result.array_list))

    # Ensure 5 new assets were added
    assert len_after == len_before + 5


@pytest.mark.asyncio
async def test_not_possible_to_add_same_id(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    # Add 1st asset
    asset_id_1, asset_ticker_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_ticker_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)

    # Second asset with SAME asset ID
    _, asset_ticker_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_1, asset_ticker_2, asset_name_2)
    # Should fail because asset ID is already present
    await assert_revert(
        signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_2)
    )

@pytest.mark.asyncio
async def test_not_possible_to_add_same_ticker(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    # Add 1st asset
    asset_id_1, asset_ticker_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_ticker_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)

    # Second asset with SAME asset ticker
    asset_id_2, _, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_ticker_1, asset_name_2)
    # Should fail because asset ID is already present
    await assert_revert(
        signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_2)
    )

@pytest.mark.asyncio
async def test_not_possible_to_add_zero_asset_id(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    _, asset_ticker_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(0, asset_ticker_1, asset_name_1)

    # Should fail because asset_id is 0
    await assert_revert(
        signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)
    )

@pytest.mark.asyncio
async def test_not_possible_to_remove_zero_asset_id(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    # Should fail because zero asset_id can't be present
    await assert_revert(
        signer1.send_transaction(admin1, asset.contract_address, 'removeAsset', [0])
    )

@pytest.mark.asyncio
async def test_add_3_then_remove_FIRST_asset(fresh_asset_contract):
    admin1, asset = fresh_asset_contract

    # Add 1st asset
    asset_id_1, asset_ticker_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_ticker_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)
    
    # Add 2nd
    asset_id_2, asset_ticker_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_ticker_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_ticker_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_ticker_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_3)

    ID_TO_DELETE = asset_id_1

    # Check count is 3
    assets_after_add = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(assets_after_add) == 3

    # Remove asset
    await signer1.send_transaction(admin1, asset.contract_address, 'removeAsset', [ID_TO_DELETE])

    # Check removed asset is not present
    await assert_revert(
        asset.getAsset(ID_TO_DELETE).call()
    )

    # Check count is 2
    assets_after_remove = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(assets_after_remove) == 2

    # Check asset at 0 index, should be asset_3
    assert assets_after_remove[0].id == asset_id_3
    assert assets_after_remove[0].ticker == asset_ticker_3
    assert assets_after_remove[0].short_name == asset_name_3

    # Check asset at 1 index, should be asset_2
    assert assets_after_remove[1].id == asset_id_2
    assert assets_after_remove[1].ticker == asset_ticker_2
    assert assets_after_remove[1].short_name == asset_name_2

    # Check deleted asset can be added again
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)

    # Check re-added asset in assets list
    final_assets = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(final_assets) == 3
    assert final_assets[2].id == asset_id_1
    assert final_assets[2].ticker == asset_ticker_1
    assert final_assets[2].short_name == asset_name_1

    # Check re-added asset fetching by id
    re_added_asset = (await asset.getAsset(ID_TO_DELETE).call()).result.currAsset
    assert re_added_asset.ticker == asset_ticker_1
    assert re_added_asset.short_name == asset_name_1


@pytest.mark.asyncio
async def test_add_3_then_remove_SECOND_asset(fresh_asset_contract):
    admin1, asset = fresh_asset_contract

    # Add 1st asset
    asset_id_1, asset_ticker_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_ticker_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)
    
    # Add 2nd
    asset_id_2, asset_ticker_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_ticker_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_ticker_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_ticker_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_3)

    ID_TO_DELETE = asset_id_2

    # Check count is 3
    assets_after_add = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(assets_after_add) == 3

    # Remove asset
    await signer1.send_transaction(admin1, asset.contract_address, 'removeAsset', [ID_TO_DELETE])

    # Check removed asset is not present
    await assert_revert(
        asset.getAsset(ID_TO_DELETE).call()
    )

    # Check count is 2
    assets_after_remove = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(assets_after_remove) == 2

    # Check asset at 0 index, should be asset_1
    assert assets_after_remove[0].id == asset_id_1
    assert assets_after_remove[0].ticker == asset_ticker_1
    assert assets_after_remove[0].short_name == asset_name_1

    # Check asset at 1 index, should be asset_3
    assert assets_after_remove[1].id == asset_id_3
    assert assets_after_remove[1].ticker == asset_ticker_3
    assert assets_after_remove[1].short_name == asset_name_3

    # Check deleted asset can be added again
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_2)

    # Check re-added asset in assets list
    final_assets = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(final_assets) == 3
    assert final_assets[2].id == asset_id_2
    assert final_assets[2].ticker == asset_ticker_2
    assert final_assets[2].short_name == asset_name_2

    # Check re-added asset fetching by id
    re_added_asset = (await asset.getAsset(ID_TO_DELETE).call()).result.currAsset
    assert re_added_asset.ticker == asset_ticker_2
    assert re_added_asset.short_name == asset_name_2

@pytest.mark.asyncio
async def test_add_3_then_remove_THIRD_asset(fresh_asset_contract):
    admin1, asset = fresh_asset_contract

    # Add 1st asset
    asset_id_1, asset_ticker_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_ticker_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_1)
    
    # Add 2nd
    asset_id_2, asset_ticker_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_ticker_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_ticker_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_ticker_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_3)

    ID_TO_DELETE = asset_id_3

    # Check count is 3
    assets_after_add = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(assets_after_add) == 3

    # Remove asset
    await signer1.send_transaction(admin1, asset.contract_address, 'removeAsset', [ID_TO_DELETE])

    # Check removed asset is not present
    await assert_revert(
        asset.getAsset(ID_TO_DELETE).call()
    )

    # Check count is 2
    assets_after_remove = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(assets_after_remove) == 2

    # Check asset at 0 index, should be asset_1
    assert assets_after_remove[0].id == asset_id_1
    assert assets_after_remove[0].ticker == asset_ticker_1
    assert assets_after_remove[0].short_name == asset_name_1

    # Check asset at 1 index, should be asset_2
    assert assets_after_remove[1].id == asset_id_2
    assert assets_after_remove[1].ticker == asset_ticker_2
    assert assets_after_remove[1].short_name == asset_name_2

    # Check deleted asset can be added again
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties_3)

    # Check re-added asset in assets list
    final_assets = list((await asset.returnAllAssets().call()).result.array_list)
    assert len(final_assets) == 3
    assert final_assets[2].id == asset_id_3
    assert final_assets[2].ticker == asset_ticker_3
    assert final_assets[2].short_name == asset_name_3

    # Check re-added asset fetching by id
    re_added_asset = (await asset.getAsset(ID_TO_DELETE).call()).result.currAsset
    assert re_added_asset.ticker == asset_ticker_3
    assert re_added_asset.short_name == asset_name_3
