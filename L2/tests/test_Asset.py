import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import ContractIndex, ManagerAction, str_to_felt, MAX_UINT256, assert_revert, assert_event_emitted
from utils_asset import build_default_asset_properties, encode_asset_id_name, DEFAULT_ASSET_ICON_LINK, DEFAULT_ASSET_METADATA_LINK
from utils_links import encode_characters
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3


counter = 0
# Generates unique asset params (id and name) to avoid conflicts
def generate_asset_info():
    global counter
    counter += 1
    id = f"ETH_${counter}"
    name = f"Ethereum_${counter}"
    return encode_asset_id_name(id, name)


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

    # Give permissions
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAssets, True])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])
    
    # Add contract to registry
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Asset, 1, asset.contract_address])

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
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    add_asset_tx = await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)
    assert_event_emitted(
        add_asset_tx,
        from_address=asset.contract_address,
        name="asset_added",
        data=[
            asset_id,
            admin1.contract_address
        ]
    )

    execution_info = await asset.get_asset(asset_id).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.id == asset_id
    assert fetched_asset.short_name == asset_name
    assert fetched_asset.is_tradable == 0
    assert fetched_asset.is_collateral == 0
    assert fetched_asset.token_decimal == 18

    assets = await asset.return_all_assets().call()
    parsed_list = list(assets.result.array_list)[0]

    assert parsed_list.id == asset_id
    assert parsed_list.asset_version == 1
    assert parsed_list.short_name == asset_name
    assert parsed_list.is_tradable == 0
    assert parsed_list.is_collateral == 0
    assert parsed_list.token_decimal == 18

    icon_call = await asset.get_icon_link(asset_id).call()
    icon_link = list(icon_call.result.link)
    assert icon_link == encode_characters(DEFAULT_ASSET_ICON_LINK)

    metadata_call = await asset.get_metadata_link(asset_id).call()
    metadata_link = list(metadata_call.result.link)
    assert metadata_link == encode_characters(DEFAULT_ASSET_METADATA_LINK)


@pytest.mark.asyncio
async def test_adding_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    await assert_revert(
        signer3.send_transaction(user1, asset.contract_address, 'add_asset', asset_properties),
        reverted_with="Asset: caller not authorized to manage assets"
    )


@pytest.mark.asyncio
async def test_modifying_asset_by_admin(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)

    new_asset_name = str_to_felt("NEW_NAME")
    new_tradable_status = 1
    new_collateral = 1

    modify_tx = await signer1.send_transaction(admin1, asset.contract_address, 'modify_core_settings', [
        asset_id,
        new_asset_name,
        new_tradable_status,
        new_collateral
    ])
    assert_event_emitted(
        modify_tx,
        from_address=asset.contract_address,
        name="asset_core_settings_update",
        data=[
            asset_id,
            admin1.contract_address
        ]
    )

    execution_info = await asset.get_asset(asset_id).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.id == asset_id
    assert fetched_asset.short_name == new_asset_name
    assert fetched_asset.is_tradable == new_tradable_status
    assert fetched_asset.is_collateral == new_collateral
    assert fetched_asset.asset_version == 2


@pytest.mark.asyncio
async def test_modifying_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)

    await assert_revert( 
        signer3.send_transaction(user1, asset.contract_address, 'modify_core_settings', [
            asset_id, 
            asset_name, 
            0, 
            1
        ])
    )


@pytest.mark.asyncio
async def test_removing_asset_by_admin(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)

    remove_tx = await signer1.send_transaction(admin1, asset.contract_address, 'remove_asset', [asset_id])
    assert_event_emitted(
        remove_tx,
        from_address=asset.contract_address,
        name="asset_removed",
        data=[
            asset_id,
            admin1.contract_address
        ]
    )

    await assert_revert(
        asset.get_asset(asset_id).call(),
        reverted_with="Asset: asset_id existence check failed"
    )


@pytest.mark.asyncio
async def test_removing_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)

    await assert_revert(
        signer3.send_transaction(user1, asset.contract_address, 'remove_asset', [asset_id]),
        reverted_with="Asset: caller not authorized to manage assets"
    )


@pytest.mark.asyncio
async def test_retrieve_assets(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    assets_before = await asset.return_all_assets().call()
    len_before = len(list(assets_before.result.array_list))

    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)

    assets_after = await asset.return_all_assets().call()
    len_after = len(list(assets_after.result.array_list))

    assert len_after == len_before + 1

@pytest.mark.asyncio
async def test_can_add_five_different_assets(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    # Get number of assets before
    assets_before = await asset.return_all_assets().call()
    len_before = len(list(assets_before.result.array_list))

    # Add 1st
    asset_id_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_1)

    # Add 2nd
    asset_id_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_3)

    # Add 4th
    asset_id_4, asset_name_4 = generate_asset_info()
    asset_properties_4 = build_default_asset_properties(asset_id_4, asset_name_4)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_4)

    # Add 5th
    asset_id_5, asset_name_5 = generate_asset_info()
    asset_properties_5 = build_default_asset_properties(asset_id_5, asset_name_5)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_5)

    # Get number of assets after
    assets_after = await asset.return_all_assets().call()
    len_after = len(list(assets_after.result.array_list))

    # Ensure 5 new assets were added
    assert len_after == len_before + 5


@pytest.mark.asyncio
async def test_not_possible_to_add_same_id(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    # Add 1st asset
    asset_id_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_1)

    # Second asset with SAME asset ID
    _, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_1, asset_name_2)
    # Should fail because asset ID is already present
    await assert_revert(
        signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_2),
        reverted_with="Asset: asset_id existence check failed"
    )

@pytest.mark.asyncio
async def test_not_possible_to_add_zero_asset_id(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory
    _, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(0, asset_name_1)

    # Should fail because asset_id is 0
    await assert_revert(
        signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_1),
        reverted_with="Asset: asset ID must be non-zero"
    )

@pytest.mark.asyncio
async def test_not_possible_to_remove_zero_asset_id(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1 = adminAuth_factory

    # Should fail because zero asset_id can't be present
    await assert_revert(
        signer1.send_transaction(admin1, asset.contract_address, 'remove_asset', [0]),
        reverted_with="Asset: asset_id existence check failed"
    )

@pytest.mark.asyncio
async def test_add_3_then_remove_FIRST_asset(fresh_asset_contract):
    admin1, asset = fresh_asset_contract

    # Add 1st asset
    asset_id_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_1)
    
    # Add 2nd
    asset_id_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_3)

    ID_TO_DELETE = asset_id_1

    # Check count is 3
    assets_after_add = list((await asset.return_all_assets().call()).result.array_list)
    assert len(assets_after_add) == 3

    # Remove asset
    await signer1.send_transaction(admin1, asset.contract_address, 'remove_asset', [ID_TO_DELETE])

    # Check removed asset is not present
    await assert_revert(
        asset.get_asset(ID_TO_DELETE).call(),
        reverted_with="Asset: asset_id existence check failed"
    )

    # Check count is 2
    assets_after_remove = list((await asset.return_all_assets().call()).result.array_list)
    assert len(assets_after_remove) == 2

    # Check asset at 0 index, should be asset_3
    assert assets_after_remove[0].id == asset_id_3
    assert assets_after_remove[0].short_name == asset_name_3

    # Check asset at 1 index, should be asset_2
    assert assets_after_remove[1].id == asset_id_2
    assert assets_after_remove[1].short_name == asset_name_2

    # Check deleted asset can be added again
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_1)

    # Check re-added asset in assets list
    final_assets = list((await asset.return_all_assets().call()).result.array_list)
    assert len(final_assets) == 3
    assert final_assets[2].id == asset_id_1
    assert final_assets[2].short_name == asset_name_1

    # Check re-added asset fetching by id
    re_added_asset = (await asset.get_asset(ID_TO_DELETE).call()).result.currAsset
    assert re_added_asset.id == asset_id_1
    assert re_added_asset.short_name == asset_name_1


@pytest.mark.asyncio
async def test_add_3_then_remove_SECOND_asset(fresh_asset_contract):
    admin1, asset = fresh_asset_contract

    # Add 1st asset
    asset_id_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_1)
    
    # Add 2nd
    asset_id_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_3)

    ID_TO_DELETE = asset_id_2

    # Check count is 3
    assets_after_add = list((await asset.return_all_assets().call()).result.array_list)
    assert len(assets_after_add) == 3

    # Remove asset
    await signer1.send_transaction(admin1, asset.contract_address, 'remove_asset', [ID_TO_DELETE])

    # Check removed asset is not present
    await assert_revert(
        asset.get_asset(ID_TO_DELETE).call(),
        reverted_with="Asset: asset_id existence check failed"
    )

    # Check count is 2
    assets_after_remove = list((await asset.return_all_assets().call()).result.array_list)
    assert len(assets_after_remove) == 2

    # Check asset at 0 index, should be asset_1
    assert assets_after_remove[0].id == asset_id_1
    assert assets_after_remove[0].short_name == asset_name_1

    # Check asset at 1 index, should be asset_3
    assert assets_after_remove[1].id == asset_id_3
    assert assets_after_remove[1].short_name == asset_name_3

    # Check deleted asset can be added again
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_2)

    # Check re-added asset in assets list
    final_assets = list((await asset.return_all_assets().call()).result.array_list)
    assert len(final_assets) == 3
    assert final_assets[2].id == asset_id_2
    assert final_assets[2].short_name == asset_name_2

    # Check re-added asset fetching by id
    re_added_asset = (await asset.get_asset(ID_TO_DELETE).call()).result.currAsset
    assert re_added_asset.id == asset_id_2
    assert re_added_asset.short_name == asset_name_2

@pytest.mark.asyncio
async def test_add_3_then_remove_THIRD_asset(fresh_asset_contract):
    admin1, asset = fresh_asset_contract

    # Add 1st asset
    asset_id_1, asset_name_1 = generate_asset_info()
    asset_properties_1 = build_default_asset_properties(asset_id_1, asset_name_1)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_1)
    
    # Add 2nd
    asset_id_2, asset_name_2 = generate_asset_info()
    asset_properties_2 = build_default_asset_properties(asset_id_2, asset_name_2)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_2)

    # Add 3rd
    asset_id_3, asset_name_3 = generate_asset_info()
    asset_properties_3 = build_default_asset_properties(asset_id_3, asset_name_3)
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_3)

    ID_TO_DELETE = asset_id_3

    # Check count is 3
    assets_after_add = list((await asset.return_all_assets().call()).result.array_list)
    assert len(assets_after_add) == 3

    # Remove asset
    await signer1.send_transaction(admin1, asset.contract_address, 'remove_asset', [ID_TO_DELETE])

    # Check removed asset is not present
    await assert_revert(
        asset.get_asset(ID_TO_DELETE).call(),
        reverted_with="Asset: asset_id existence check failed"
    )

    # Check count is 2
    assets_after_remove = list((await asset.return_all_assets().call()).result.array_list)
    assert len(assets_after_remove) == 2

    # Check asset at 0 index, should be asset_1
    assert assets_after_remove[0].id == asset_id_1
    assert assets_after_remove[0].short_name == asset_name_1

    # Check asset at 1 index, should be asset_2
    assert assets_after_remove[1].id == asset_id_2
    assert assets_after_remove[1].short_name == asset_name_2

    # Check deleted asset can be added again
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties_3)

    # Check re-added asset in assets list
    final_assets = list((await asset.return_all_assets().call()).result.array_list)
    assert len(final_assets) == 3
    assert final_assets[2].id == asset_id_3
    assert final_assets[2].short_name == asset_name_3

    # Check re-added asset fetching by id
    re_added_asset = (await asset.get_asset(ID_TO_DELETE).call()).result.currAsset
    assert re_added_asset.short_name == asset_name_3
