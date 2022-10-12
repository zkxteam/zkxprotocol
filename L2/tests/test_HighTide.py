import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, PRIME, assert_event_emitted
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3


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

    timestamp = int(time.time())

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 8, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [24, 1, hightide.contract_address])

    return adminAuth, hightide, admin1, admin2, user1, timestamp

@pytest.mark.asyncio
async def test_set_multipliers_unauthorized_user(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    await assert_revert( signer3.send_transaction(user1, hightide.contract_address, 'set_multipliers', [
        1, 2, 3, 4]))

@pytest.mark.asyncio
async def test_set_multipliers_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    set_multipliers_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'set_multipliers', [
        1, 2, 3, 4])
    
    assert_event_emitted(
        set_multipliers_tx,
        from_address=hightide.contract_address,
        name="multipliers_for_rewards_added",
        data=[
            admin1.contract_address,1,2,3,4
        ]
    )

    execution_info = await hightide.get_multipliers().call()
    fetched_multipliers = execution_info.result.multipliers

    assert fetched_multipliers.a1 == 1
    assert fetched_multipliers.a2 == 2
    assert fetched_multipliers.a3 == 3
    assert fetched_multipliers.a4 == 4

@pytest.mark.asyncio
async def test_set_constants_unauthorized_user(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    await assert_revert( signer3.send_transaction(user1, hightide.contract_address, 'set_constants', [
        1, 2, 3, 4, 5]))

@pytest.mark.asyncio
async def test_set_constants_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    set_constants_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'set_constants', [
        1, 2, 3, 4, 5])
    
    assert_event_emitted(
        set_constants_tx,
        from_address=hightide.contract_address,
        name="constants_for_trader_score_added",
        data=[
            admin1.contract_address,1,2,3,4,5
        ]
    )

    execution_info = await hightide.get_constants().call()
    fetched_constants = execution_info.result.constants

    assert fetched_constants.a == 1
    assert fetched_constants.b == 2
    assert fetched_constants.c == 3
    assert fetched_constants.z == 4
    assert fetched_constants.e == 5

@pytest.mark.asyncio
async def test_setup_trading_season_unauthorized_user(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    await assert_revert( signer3.send_transaction(user1, hightide.contract_address, 'setup_trade_season', [
        timestamp, to64x61(30)]))

@pytest.mark.asyncio
async def test_setup_trading_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    trade_season_setup_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        timestamp, to64x61(30)])
    
    assert_event_emitted(
        trade_season_setup_tx,
        from_address=hightide.contract_address,
        name="trading_season_set_up",
        data=[
            admin1.contract_address,
            0,
            timestamp,
            to64x61(30)
        ]
    )

    execution_info = await hightide.get_season(1).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == timestamp
    assert fetched_trading_season.num_trading_days == to64x61(30)

@pytest.mark.asyncio
async def test_start_trade_season_unauthorized_user(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    await assert_revert( signer3.send_transaction(user1, hightide.contract_address, 'start_trade_season', [
        1]))

@pytest.mark.asyncio
async def test_start_trade_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    start_trade_season_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [
        1])
    
    assert_event_emitted(
        start_trade_season_tx,
        from_address=hightide.contract_address,
        name="trading_season_started",
        data=[
            admin1.contract_address, 1
        ]
    )
    
    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 1

@pytest.mark.asyncio
async def test_get_season_with_invalid_season_id(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    await assert_revert(hightide.get_season(2).call())