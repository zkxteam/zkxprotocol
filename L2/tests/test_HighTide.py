import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import DeclaredClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, PRIME, assert_event_emitted, assert_events_emitted
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3

BTC_ID = str_to_felt("32f0406jz7qj8")
USDC_ID = str_to_felt("fghj3am52qpzsib")
USDT_ID = str_to_felt("yjk45lvmasopq")
BTC_USDC_ID = str_to_felt("gecn2j0cm45sz")
BTC_USDT_ID = str_to_felt("gecn2j0c12rtzxcmsz")
class_hash=0

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

    contract_class = starknet_service.contracts_holder.get_contract_class(ContractType.LiquidityPool)
    global class_hash
    class_hash, _ = await starknet_service.starknet.state.declare(contract_class)
    direct_class_hash = compute_class_hash(contract_class)
    class_hash = int.from_bytes(class_hash,'big')
    assert direct_class_hash == class_hash

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

    await assert_revert( 
        signer3.send_transaction(user1, hightide.contract_address, 'set_multipliers', [1, 2, 3, 4]),
        reverted_with="HighTide: Unauthorized call to set multipliers"
    )

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

    await assert_revert( 
        signer3.send_transaction(user1, hightide.contract_address, 'set_constants', [1, 2, 3, 4, 5]),
        reverted_with="HighTide: Unauthorized call to set constants"
    )

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

    await assert_revert( 
        signer3.send_transaction(user1, hightide.contract_address, 'setup_trade_season', [timestamp, to64x61(30)]),
        "HighTide: Unauthorized call to setup trade season"
    )

@pytest.mark.asyncio
async def test_setup_trading_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    trade_season_setup_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        timestamp, 30])
    
    assert_event_emitted(
        trade_season_setup_tx,
        from_address=hightide.contract_address,
        name="trading_season_set_up",
        data=[
            admin1.contract_address,
            0,
            timestamp,
            30
        ]
    )

    execution_info = await hightide.get_season(1).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == timestamp
    assert fetched_trading_season.num_trading_days == 30

@pytest.mark.asyncio
async def test_start_trade_season_unauthorized_user(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    await assert_revert( 
        signer3.send_transaction(user1, hightide.contract_address, 'start_trade_season', [1]),
        reverted_with="HighTide: Unauthorized call to start trade season"  
    )

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

    await assert_revert(hightide.get_season(2).call(), reverted_with="HighTide: Trading season id existence mismatch")

@pytest.mark.asyncio
async def test_inialize_hightide_with_zero_class_hash(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory

    await assert_revert(signer1.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', 
        [BTC_USDC_ID, 1, 1, 2, USDC_ID, 1000, USDT_ID, 500]))

@pytest.mark.asyncio
async def test_inialize_hightide(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp = adminAuth_factory
    
    tx_exec_info=await signer1.send_transaction(admin1, 
                                   hightide.contract_address,
                                   'set_liquidity_pool_contract_class_hash',
                                   [class_hash])
   
    assert_event_emitted(
        tx_exec_info,
        from_address = hightide.contract_address,
        name = 'liquidity_pool_contract_class_hash_changed',
        data = [
            class_hash
        ]
    )

    tx_exec_info=await signer1.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', 
        [BTC_USDC_ID, 1, 1, 2, USDC_ID, 1000, USDT_ID, 500])

    execution_info = await hightide.get_hightide(1).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    assert_events_emitted(
        tx_exec_info,
        [
            [0, hightide.contract_address, 'liquidity_pool_contract_deployed', [1, liquidity_pool_address]],
            [1, hightide.contract_address, 'hightide_initialized', [admin1.contract_address, 1]],
        ]
    )
    
    fetched_rewards = await hightide.get_hightide_reward_tokens(1).call()
    assert fetched_rewards.result.reward_tokens_list[0].token_id == USDC_ID
    assert fetched_rewards.result.reward_tokens_list[0].no_of_tokens == 1000
    assert fetched_rewards.result.reward_tokens_list[1].token_id == USDT_ID
    assert fetched_rewards.result.reward_tokens_list[1].no_of_tokens == 500
