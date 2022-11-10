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
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, PRIME, assert_event_emitted, assert_events_emitted
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3

BTC_ID = str_to_felt("32f0406jz7qj8")
USDC_ID = str_to_felt("fghj3am52qpzsib") 
UST_ID = str_to_felt("yjk45lvmasopq") 
BTC_USDC_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
class_hash=0
USDC_L1_address=123
UST_L1_address=456
whitelisted_usdc=None
whitelisted_ust=None

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
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    market = await starknet_service.deploy(ContractType.Markets, [registry.contract_address, 1])
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])
    starkway = await starknet_service.deploy(ContractType.Starkway, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 8, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [24, 1, hightide.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [27, 1, starkway.contract_address])

    # Add assets
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [BTC_ID, 1, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [USDC_ID, 1, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [UST_ID, 1, str_to_felt("UST"), str_to_felt("UST"), 1, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USDC_ID, BTC_ID, USDC_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [BTC_UST_ID, BTC_ID, UST_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Deploy ERC20 contracts
    native_erc20_usdc = await starknet_service.deploy(ContractType.ERC20, [str_to_felt("USDC"), str_to_felt("USDC"), 6, 100, 0, starkway.contract_address, admin1.contract_address])
    native_erc20_ust = await starknet_service.deploy(ContractType.ERC20, [str_to_felt("UST"), str_to_felt("UST"), 18, 100, 0, starkway.contract_address, admin1.contract_address])
  
    # add native token l2 address
    await signer1.send_transaction(admin1, starkway.contract_address, 'add_native_token_l2_address',[USDC_L1_address, native_erc20_usdc.contract_address])
    await signer1.send_transaction(admin1, starkway.contract_address, 'add_native_token_l2_address',[UST_L1_address, native_erc20_ust.contract_address])

    return adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, starknet_service

# @pytest.mark.asyncio
# async def test_set_multipliers_unauthorized_user(adminAuth_factory):
#     adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

#     await assert_revert( 
#         signer3.send_transaction(user1, hightide.contract_address, 'set_multipliers', [1, 2, 3, 4]),
#         reverted_with="HighTide: Unauthorized call to set multipliers"
#     )

# @pytest.mark.asyncio
# async def test_set_multipliers_authorized_admin(adminAuth_factory):
#     adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

#     set_multipliers_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'set_multipliers', [
#         1, 2, 3, 4])
    
#     assert_event_emitted(
#         set_multipliers_tx,
#         from_address=hightide.contract_address,
#         name="multipliers_for_rewards_added",
#         data=[
#             admin1.contract_address,1,2,3,4
#         ]
#     )

#     execution_info = await hightide.get_multipliers().call()
#     fetched_multipliers = execution_info.result.multipliers

#     assert fetched_multipliers.a1 == 1
#     assert fetched_multipliers.a2 == 2
#     assert fetched_multipliers.a3 == 3
#     assert fetched_multipliers.a4 == 4

# @pytest.mark.asyncio
# async def test_set_constants_unauthorized_user(adminAuth_factory):
#     adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

#     await assert_revert( 
#         signer3.send_transaction(user1, hightide.contract_address, 'set_constants', [1, 2, 3, 4, 5]),
#         reverted_with="HighTide: Unauthorized call to set constants"
#     )

# @pytest.mark.asyncio
# async def test_set_constants_authorized_admin(adminAuth_factory):
#     adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

#     set_constants_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'set_constants', [
#         1, 2, 3, 4, 5])
    
#     assert_event_emitted(
#         set_constants_tx,
#         from_address=hightide.contract_address,
#         name="constants_for_trader_score_added",
#         data=[
#             admin1.contract_address,1,2,3,4,5
#         ]
#     )

#     execution_info = await hightide.get_constants().call()
#     fetched_constants = execution_info.result.constants

#     assert fetched_constants.a == 1
#     assert fetched_constants.b == 2
#     assert fetched_constants.c == 3
#     assert fetched_constants.z == 4
#     assert fetched_constants.e == 5

# @pytest.mark.asyncio
# async def test_setup_trading_season_unauthorized_user(adminAuth_factory):
#     adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

#     await assert_revert( 
#         signer3.send_transaction(user1, hightide.contract_address, 'setup_trade_season', [timestamp, to64x61(30)]),
#         "HighTide: Unauthorized call to setup trade season"
#     )

@pytest.mark.asyncio
async def test_setup_trading_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

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
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

    await assert_revert( 
        signer3.send_transaction(user1, hightide.contract_address, 'start_trade_season', [1]),
        reverted_with="HighTide: Unauthorized call to start trade season"  
    )

@pytest.mark.asyncio
async def test_start_trade_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

    start_trade_season_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [1])
    
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

# end trade season before it gets expired
@pytest.mark.asyncio
async def test_end_trade_season_before_expiry(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory
    
    await assert_revert(
        signer1.send_transaction(
            admin1,
            hightide.contract_address,
            "end_trade_season",
            [1],
        ),
        "HighTide: Trading season is still active"
    )

# end trade season after it gets expired
@pytest.mark.asyncio
async def test_end_trade_season_after_expiry(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, starknet_service = adminAuth_factory
    
    execution_info = await hightide.get_season(1).call()
    fetched_trading_season = execution_info.result.trading_season

    num_trading_days = fetched_trading_season.num_trading_days

    timestamp = fetched_trading_season.start_timestamp + (num_trading_days*24*60*60) + 1

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    execution_info = await signer1.send_transaction(admin1, hightide.contract_address,
                            "end_trade_season",[1])

    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 0

@pytest.mark.asyncio
async def test_get_season_with_invalid_season_id(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

    await assert_revert(hightide.get_season(2).call(), reverted_with="HighTide: Trading season id existence mismatch")

@pytest.mark.asyncio
async def test_initialize_hightide_for_expired_trading_season(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

    await assert_revert(signer1.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', 
        [BTC_USDC_ID, 1, admin1.contract_address, 1, 2, USDC_L1_address, 1000, 0, UST_L1_address, 500, 0]),
        "HighTide: Trading season already ended")

@pytest.mark.asyncio
async def test_initialize_hightide_with_zero_class_hash(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

    await assert_revert(signer1.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', 
        [BTC_USDC_ID, 1, admin1.contract_address, 1, 2, USDC_L1_address, 1000, 0, UST_L1_address, 500, 0]))

@pytest.mark.asyncio
async def test_initialize_hightide(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory
    
    await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        timestamp, 40])
    season_id = 2
    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == timestamp
    assert fetched_trading_season.num_trading_days == 40

    await signer1.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [season_id])
    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id
    assert season_id == 2

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
        [BTC_USDC_ID, season_id, admin1.contract_address, 1, 2, USDC_L1_address, 1000, 0, UST_L1_address, 500, 0])
    hightide_id = 1
    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    assert_events_emitted(
        tx_exec_info,
        [
            [0, hightide.contract_address, 'liquidity_pool_contract_deployed', [hightide_id, liquidity_pool_address]],
            [1, hightide.contract_address, 'hightide_initialized', [admin1.contract_address, hightide_id]],
        ]
    )
    
    fetched_rewards = await hightide.get_hightide_reward_tokens(hightide_id).call()
    assert fetched_rewards.result.reward_tokens_list[0].token_id == USDC_L1_address
    assert fetched_rewards.result.reward_tokens_list[0].no_of_tokens == (1000, 0)
    assert fetched_rewards.result.reward_tokens_list[1].token_id == UST_L1_address
    assert fetched_rewards.result.reward_tokens_list[1].no_of_tokens == (500, 0)

# activating hightide will fail as there are no funds in liquidity pool contract
@pytest.mark.asyncio
async def test_activate_hightide_with_zero_fund_transfer(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

    hightide_id = 1
    await assert_revert(
        signer1.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Liquidity pool should be fully funded"
    )

# activating hightide by funding only native tokens
@pytest.mark.asyncio
async def test_activate_hightide_with_native_token_funds(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory

    execution_info = await hightide.get_current_season_id().call()
    season_id = execution_info.result.season_id
    hightide_id = 1

    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    await signer1.send_transaction(admin1, native_erc20_usdc.contract_address,
                                    'mint',[liquidity_pool_address, 1000, 0],)

    await signer1.send_transaction(admin1, native_erc20_ust.contract_address,
                                    'mint',[liquidity_pool_address, 500, 0],)

    tx_exec_info = await signer1.send_transaction(admin1, hightide.contract_address,
        "activate_high_tide",[hightide_id])

    assert_events_emitted(
        tx_exec_info,
        [
            [0, hightide.contract_address, 'hightide_activated', [admin1.contract_address, hightide_id]],
            [1, hightide.contract_address, 'assigned_hightide_to_season', [hightide_id, season_id]],
        ]
    )

# activating hightide will fail as hightide is already activated
@pytest.mark.asyncio
async def test_activate_hightide_which_is_already_activated(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, _ = adminAuth_factory
    hightide_id = 1
    await assert_revert(
        signer1.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Hightide is already activated"
    )

# activating hightide will fail as trading season already expired
@pytest.mark.asyncio
async def test_activate_hightide_for_expired_trading_season(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, starknet_service = adminAuth_factory

    season_id = 2
    tx_exec_info=await signer1.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', 
        [BTC_USDC_ID, season_id, admin1.contract_address, 1, 2, USDC_L1_address, 2000, 0, UST_L1_address, 2000, 0])
    hightide_id = 2
    execution_info = await hightide.get_hightide(hightide_id).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    await signer1.send_transaction(admin1, native_erc20_usdc.contract_address,
                                    'mint',[liquidity_pool_address, 2000, 0],)

    await signer1.send_transaction(admin1, native_erc20_ust.contract_address,
                                    'mint',[liquidity_pool_address, 2000, 0],)

    execution_info = await hightide.get_season(season_id).call()
    fetched_trading_season = execution_info.result.trading_season
    num_trading_days = fetched_trading_season.num_trading_days
    timestamp = fetched_trading_season.start_timestamp + (num_trading_days*24*60*60) + 1

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )
    await signer1.send_transaction(admin1, hightide.contract_address,
                            "end_trade_season",[season_id])

    await assert_revert(
        signer1.send_transaction(
            admin1,
            hightide.contract_address,
            "activate_high_tide",
            [hightide_id],
        ),
        "HighTide: Trading season already ended"
    )

# # activating hightide by funding both native and non native tokens
# @pytest.mark.asyncio
# async def test_activate_hightide_with_native_and_non_native_token_funds(adminAuth_factory):
#     adminAuth, hightide, admin1, admin2, user1, timestamp, native_erc20_usdc, native_erc20_ust, starkway, starknet_service = adminAuth_factory

#     execution_info = await hightide.get_current_season_id().call()
#     season_id = execution_info.result.season_id
#     hightide_id = 1

#     execution_info = await hightide.get_hightide(hightide_id).call()
#     liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

#     global whitelisted_usdc
#     global whitelisted_ust
#     whitelisted_usdc = await starknet_service.deploy(ContractType.ERC20,
#                         [str_to_felt("USDC"), str_to_felt("USDC"),6,100,0,starkway.contract_address, admin1.contract_address])
#     whitelisted_ust = await starknet_service.deploy(ContractType.ERC20,
#                         [str_to_felt("UST"), str_to_felt("UST"),18,200,0,starkway.contract_address, admin1.contract_address])
    
#     await signer1.send_transaction(admin1, whitelisted_usdc.contract_address,
#                                     'mint',[liquidity_pool_address, 0, 150],)
    
#     await signer1.send_transaction(admin1, whitelisted_ust.contract_address,
#                                     'mint',[liquidity_pool_address, 0, 200],)

#     await signer1.send_transaction(admin1, starkway.contract_address,
#                                     'whitelist_token_address',[USDC_L1_address, whitelisted_usdc.contract_address],)

#     await signer1.send_transaction(admin1, starkway.contract_address,
#                                     'whitelist_token_address',[UST_L1_address, whitelisted_ust.contract_address],)

#     await signer1.send_transaction(admin1, native_erc20_usdc.contract_address,
#                                     'mint',[liquidity_pool_address, 1000, 0],)

#     await signer1.send_transaction(admin1, native_erc20_ust.contract_address,
#                                     'mint',[liquidity_pool_address, 500, 0],)

#     tx_exec_info = await signer1.send_transaction(admin1, hightide.contract_address,
#         "activate_high_tide",[hightide_id])

#     assert_events_emitted(
#         tx_exec_info,
#         [
#             [0, hightide.contract_address, 'hightide_activated', [admin1.contract_address, hightide_id]],
#             [1, hightide.contract_address, 'assigned_hightide_to_season', [hightide_id, season_id]],
#         ]
#     )
