import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0]
    )

    user1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer3.public_key, 0]
    )


    adminAuth = await starknet.deploy(
        "contracts/AdminAuth.cairo",
        constructor_calldata=[
            admin1.contract_address,
            admin2.contract_address
        ]
    )

    asset = await starknet.deploy(
        "contracts/Asset.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
            0
        ]
    )

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    return adminAuth, asset, admin1, admin2, user1

@pytest.mark.asyncio
async def test_get_admin_mapping(adminAuth_factory): 
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory

    execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 1).call()
    assert execution_info.result.allowed == 1

    execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 1).call()
    assert execution_info1.result.allowed == 0

@pytest.mark.asyncio
async def test_adding_asset_by_admin(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    execution_info = await asset.getAsset(str_to_felt("32f0406jz7qj8")).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == str_to_felt("ETH")
    assert fetched_asset.short_name == str_to_felt("Ethereum")
    assert fetched_asset.tradable == 0 
    assert fetched_asset.collateral == 0 
    assert fetched_asset.token_decimal == 18
    assert fetched_asset.metadata_id == 0 
    assert fetched_asset.asset_version == 0


@pytest.mark.asyncio
async def test_adding_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer3.send_transaction(user1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]))


@pytest.mark.asyncio
async def test_modifying_asset_by_admin(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory
    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    await signer1.send_transaction(admin1,asset.contract_address, 'modify_core_settings', [ str_to_felt("32f0406jz7qj8"), str_to_felt("ETHEREUM"), 1, 1, 10, 1])

    execution_info = await asset.getAsset(str_to_felt("32f0406jz7qj8")).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == str_to_felt("ETH")
    assert fetched_asset.short_name == str_to_felt("ETHEREUM")
    assert fetched_asset.tradable == 1
    assert fetched_asset.collateral == 1 
    assert fetched_asset.token_decimal == 10
    assert fetched_asset.metadata_id == 1
    assert fetched_asset.asset_version == 0

@pytest.mark.asyncio
async def test_modifying_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])


    assert_revert(lambda: signer3.send_transaction(user1,asset.contract_address, 'modify_core_settings', [ str_to_felt("32f0406jz7qj8"), str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 1, 18, 1]))

@pytest.mark.asyncio
async def test_modifying_trade_settings_by_admin(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory
    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    await signer1.send_transaction(admin1,asset.contract_address, 'modify_trade_settings', [ str_to_felt("32f0406jz7qj8"), 2, 2, 11, 2, 6, 4, 2, 2, 2, 200, 2000, 20000])

    execution_info = await asset.getAsset(str_to_felt("32f0406jz7qj8")).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == str_to_felt("ETH")
    assert fetched_asset.short_name == str_to_felt("Ethereum")
    assert fetched_asset.tradable == 0
    assert fetched_asset.collateral == 0
    assert fetched_asset.token_decimal == 18
    assert fetched_asset.metadata_id == 0
    assert fetched_asset.tick_size == 2
    assert fetched_asset.step_size == 2
    assert fetched_asset.minimum_order_size == 11
    assert fetched_asset.minimum_leverage == 2
    assert fetched_asset.maximum_leverage == 6
    assert fetched_asset.currently_allowed_leverage == 4
    assert fetched_asset.maintenance_margin_fraction == 2
    assert fetched_asset.initial_margin_fraction == 2
    assert fetched_asset.incremental_initial_margin_fraction == 2
    assert fetched_asset.incremental_position_size == 200
    assert fetched_asset.baseline_position_size == 2000
    assert fetched_asset.maximum_position_size == 20000
    assert fetched_asset.asset_version == 1

    execution_info1 = await asset.get_version().call()
    version = execution_info1.result.version
    assert version == 1

@pytest.mark.asyncio
async def test_modifying_trade_settings_by_unauthorized_user(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    assert_revert(lambda: signer3.send_transaction(user1,asset.contract_address, 'modify_trade_settings', [ str_to_felt("32f0406jz7qj8"), 2, 2, 11, 2, 6, 4, 2, 2, 2, 200, 2000, 20000]))

@pytest.mark.asyncio
async def test_removing_asset_by_admin(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory
    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    await signer1.send_transaction(admin1,asset.contract_address, 'removeAsset', [ str_to_felt("32f0406jz7qj8") ])

    execution_info = await asset.getAsset(str_to_felt("32f0406jz7qj8")).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == 0
    assert fetched_asset.short_name == 0
    assert fetched_asset.tradable == 0
    assert fetched_asset.collateral == 0
    assert fetched_asset.token_decimal == 0
    assert fetched_asset.metadata_id == 0
    assert fetched_asset.tick_size == 0
    assert fetched_asset.step_size == 0
    assert fetched_asset.minimum_order_size == 0
    assert fetched_asset.minimum_leverage == 0
    assert fetched_asset.maximum_leverage == 0
    assert fetched_asset.currently_allowed_leverage == 0
    assert fetched_asset.maintenance_margin_fraction == 0
    assert fetched_asset.initial_margin_fraction == 0
    assert fetched_asset.incremental_initial_margin_fraction == 0
    assert fetched_asset.incremental_position_size == 0
    assert fetched_asset.baseline_position_size == 0
    assert fetched_asset.maximum_position_size == 0


@pytest.mark.asyncio
async def test_removing_asset_by_unauthorized_user(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory
    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    assert_revert(lambda: signer3.send_transaction(user1,asset.contract_address, 'removeAsset', [ str_to_felt("32f0406jz7qj8") ]))

@pytest.mark.asyncio
async def test_modifying_trade_settings_by_admin_twice(adminAuth_factory):
    adminAuth, asset, admin1, admin2, user1 = adminAuth_factory
    await signer1.send_transaction(admin1,asset.contract_address, 'addAsset', [ str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 0, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    await signer1.send_transaction(admin1,asset.contract_address, 'modify_trade_settings', [ str_to_felt("32f0406jz7qj8"), 2, 2, 11, 2, 6, 4, 2, 2, 2, 200, 2000, 20000])
    await signer1.send_transaction(admin1,asset.contract_address, 'modify_trade_settings', [ str_to_felt("32f0406jz7qj8"), 2, 2, 11, 2, 6, 4, 2, 2, 2, 200, 2000, 30000])

    execution_info = await asset.getAsset(str_to_felt("32f0406jz7qj8")).call()
    fetched_asset = execution_info.result.currAsset

    assert fetched_asset.ticker == str_to_felt("ETH")
    assert fetched_asset.short_name == str_to_felt("Ethereum")
    assert fetched_asset.tradable == 0
    assert fetched_asset.collateral == 0
    assert fetched_asset.metadata_id == 0
    assert fetched_asset.tick_size == 2
    assert fetched_asset.step_size == 2
    assert fetched_asset.minimum_order_size == 11
    assert fetched_asset.minimum_leverage == 2
    assert fetched_asset.maximum_leverage == 6
    assert fetched_asset.currently_allowed_leverage == 4
    assert fetched_asset.maintenance_margin_fraction == 2
    assert fetched_asset.initial_margin_fraction == 2
    assert fetched_asset.incremental_initial_margin_fraction == 2
    assert fetched_asset.incremental_position_size == 200
    assert fetched_asset.baseline_position_size == 2000
    assert fetched_asset.maximum_position_size == 30000
    assert fetched_asset.asset_version == 2

    execution_info1 = await asset.get_version().call()
    version = execution_info1.result.version
    assert version == 3