from copyreg import constructor
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, assert_event_emitted, assert_revert
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from utils_links import prepare_starknet_string, encode_characters, DEFAULT_LINK_1, DEFAULT_LINK_2


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
admin3_signer = Signer(123456789987654323)
alice_signer = Signer(123456789987654324)

MANAGE_SETTINGS_ACTION = 9
SETTINGS_REGISTRY_INDEX = 28

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def shared_factory(starknet_service: StarknetService):

    ### Deploy accounts
    admin1 = await starknet_service.deploy(ContractType.Account, [admin1_signer.public_key])
    admin2 = await starknet_service.deploy(ContractType.Account, [admin2_signer.public_key])
    admin3 = await starknet_service.deploy(ContractType.Account, [admin3_signer.public_key])
    alice = await starknet_service.deploy(ContractType.Account, [alice_signer.public_key])

    ### Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])

    ### Give admin3 rights to add trusted contracts to AuthRegistry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [
      admin1.contract_address, 
      3,
      True
    ])

    ### Give settings manager rights to admin3
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [
      admin3.contract_address, 
      MANAGE_SETTINGS_ACTION, 
      True
    ])

    return admin1, admin2, admin3, alice, registry


@pytest.fixture(scope='function')
async def settings_factory(starknet_service: StarknetService, shared_factory):

    admin1, admin2, admin3, alice, registry = shared_factory

    # Deploy Settings contract
    settings = await starknet_service.deploy(ContractType.Settings, [registry.contract_address, 1])

    # Add Settings contract to AuthRegistry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [
      SETTINGS_REGISTRY_INDEX, 
      1,
      settings.contract_address
    ])

    return settings


@pytest.mark.asyncio
async def test_initially_settings_are_empty(shared_factory, settings_factory):
    admin1, admin2, admin3, alice, registry = shared_factory
    settings = settings_factory

    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters("")


@pytest.mark.asyncio
async def test_update_settings_link_by_master_admin(shared_factory, settings_factory):
    admin1, admin2, admin3, alice, registry = shared_factory
    settings = settings_factory

    # 1. Check settings address from AuthRegistry
    settings_from_registry_call = await registry.get_contract_address(SETTINGS_REGISTRY_INDEX, 1).call()
    assert settings_from_registry_call.result.address == settings.contract_address

    # 2. Check stored link is initially empty
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters("")

    # 3. Update link to DEFAULT_LINK_1 by Master Admin
    update_tx = await admin1_signer.send_transaction(
        admin1, 
        settings.contract_address, 
        'update_settings_link',
        prepare_starknet_string(DEFAULT_LINK_1)
    )
    assert_event_emitted(
      update_tx,
      from_address=settings.contract_address,
      name="settings_link_updated"
    )

    # 4. Check stored link is DEFAULT_LINK_1
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters(DEFAULT_LINK_1)

    # 5. Update link to DEFAULT_LINK_2 by Master Admin
    update_tx = await admin1_signer.send_transaction(
        admin1, 
        settings.contract_address, 
        'update_settings_link',
        prepare_starknet_string(DEFAULT_LINK_2)
    )
    assert_event_emitted(
      update_tx,
      from_address=settings.contract_address,
      name="settings_link_updated"
    )

    # 6. Check stored link is DEFAULT_LINK_2
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters(DEFAULT_LINK_2)


@pytest.mark.asyncio
async def test_update_settings_link_by_settings_admin(shared_factory, settings_factory):
    admin1, admin2, admin3, alice, registry = shared_factory
    settings = settings_factory

    # 1. Check settings address from AuthRegistry
    settings_from_registry_call = await registry.get_contract_address(SETTINGS_REGISTRY_INDEX, 1).call()
    assert settings_from_registry_call.result.address == settings.contract_address

    # 2. Check stored link is initially empty
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters("")

    # 3. Update link to DEFAULT_LINK_1 by Settings Admin
    await admin3_signer.send_transaction(
        admin3, 
        settings.contract_address, 
        'update_settings_link',
        prepare_starknet_string(DEFAULT_LINK_1)
    )

    # 4. Check stored link is DEFAULT_LINK_1
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters(DEFAULT_LINK_1)

    # 5. Update link to DEFAULT_LINK_2 by Settings Admin
    await admin3_signer.send_transaction(
        admin3, 
        settings.contract_address, 
        'update_settings_link',
        prepare_starknet_string(DEFAULT_LINK_2)
    )

    # 6. Check stored link is DEFAULT_LINK_2
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters(DEFAULT_LINK_2)


@pytest.mark.asyncio
async def test_remove_settings_link_by_settings_admin(shared_factory, settings_factory):
    admin1, admin2, admin3, alice, registry = shared_factory
    settings = settings_factory

    # 1. Check settings address from AuthRegistry
    settings_from_registry_call = await registry.get_contract_address(SETTINGS_REGISTRY_INDEX, 1).call()
    assert settings_from_registry_call.result.address == settings.contract_address

    # 2. Ensure stored link is initially empty
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters("")

    # 3. Update link to DEFAULT_LINK_1 by Settings Admin
    update_tx = await admin3_signer.send_transaction(
        admin3, 
        settings.contract_address, 
        'update_settings_link',
        prepare_starknet_string(DEFAULT_LINK_1)
    )
    assert_event_emitted(
      update_tx,
      from_address=settings.contract_address,
      name="settings_link_updated"
    )

    # 4. Validate stored link is DEFAULT_LINK_1
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters(DEFAULT_LINK_1)

    # 5. Remove link by Settings Admin
    remove_tx = await admin3_signer.send_transaction(
        admin3, 
        settings.contract_address, 
        'update_settings_link',
        prepare_starknet_string("")
    )
    assert_event_emitted(
      remove_tx,
      from_address=settings.contract_address,
      name="settings_link_updated"
    )

    # 6. Validate stored link is empty
    settings_link_call = await settings.get_settings_link().call()
    settings_link = list(settings_link_call.result.link)
    assert settings_link == encode_characters("")
    

@pytest.mark.asyncio
async def test_update_settings_link_by_unauthorized_user(shared_factory, settings_factory):
    admin1, admin2, admin3, alice, registry = shared_factory
    settings = settings_factory

    await assert_revert(
      alice_signer.send_transaction(
        alice, 
        settings.contract_address, 
        'update_settings_link',
        prepare_starknet_string(DEFAULT_LINK_1)
      ),
      reverted_with="Settings: caller not authorized to manage settings"
    )

@pytest.mark.asyncio
async def test_settings_contract_is_present_in_auth_registry(shared_factory, settings_factory):
    admin1, admin2, admin3, alice, registry = shared_factory
    settings = settings_factory

    settings_from_registry_call = await registry.get_contract_address(SETTINGS_REGISTRY_INDEX, 1).call()
    assert settings_from_registry_call.result.address == settings.contract_address
