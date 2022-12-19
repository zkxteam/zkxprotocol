import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import DeclaredClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.public.abi import get_selector_from_name
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, PRIME, assert_event_emitted, assert_events_emitted
from utils_links import DEFAULT_LINK_1, DEFAULT_LINK_2
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3, signer4

BTC_USDC_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")

alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)

initial_timestamp = int(time.time())
timestamp1 = int(time.time()) + (60*60*24)*3 + 60
timestamp2 = int(time.time()) + (60*60*24)*6 + 60
timestamp3 = int(time.time()) + (60*60*24)*9 + 60

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

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=initial_timestamp, 
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
    trading_stats = await starknet_service.deploy(ContractType.TradingStats, [registry.contract_address, 1])
    rewardsCalculation = await starknet_service.deploy(ContractType.RewardsCalculation, [registry.contract_address, 1])
    hightideCalc = await starknet_service.deploy(ContractType.HighTideCalc, [registry.contract_address, 1])

    account_factory = AccountFactory(starknet_service, L1_dummy_address, registry.contract_address, 1)
    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)


    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 8, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [24, 1, hightide.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [25, 1, trading_stats.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, "update_contract_registry", [29, 1, rewardsCalculation.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [30, 1, hightideCalc.contract_address])

    # Add assets
    BTC_properties = build_asset_properties(
        id=AssetID.BTC,
        short_name=str_to_felt("BTC"),
        asset_version=1,
        is_tradable=True,
        is_collateral=False,
        token_decimal=8
    )
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', BTC_properties)

    USDC_properties = build_asset_properties(
        id=AssetID.USDC,
        short_name=str_to_felt("USDC"),
        asset_version=1,
        is_tradable=False,
        is_collateral=True,
        token_decimal=6
    )
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', USDC_properties)

    UST_properties = build_asset_properties(
        id=AssetID.UST,
        short_name=str_to_felt("UST"),
        asset_version=1,
        is_tradable=True,
        is_collateral=True,
        token_decimal=6
    )
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', UST_properties)

    # Add markets
    BTC_USDC_properties = MarketProperties(
        id=BTC_USDC_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.USDC,
        leverage=to64x61(10),
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=10,
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(10),
        maintenance_margin_fraction=1,
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000,
        metadata_link=DEFAULT_LINK_1
    )
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', BTC_USDC_properties.to_params_list())
    
    BTC_UST_properties = MarketProperties(
        id=BTC_UST_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.UST,
        leverage=to64x61(10),
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        step_size=1,
        minimum_order_size=10,
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(5),
        currently_allowed_leverage=to64x61(3),
        maintenance_margin_fraction=1,
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000,
        metadata_link=DEFAULT_LINK_2
    )
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', BTC_UST_properties.to_params_list())

    return adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, alice, bob

@pytest.mark.asyncio
async def test_setup_trading_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, _, _, _, _ = adminAuth_factory

    set_multipliers_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'set_multipliers', [
        1, 2, 3, 4])

    execution_info = await hightide.get_multipliers().call()
    fetched_multipliers = execution_info.result.multipliers

    assert fetched_multipliers.a_1 == 1
    assert fetched_multipliers.a_2 == 2
    assert fetched_multipliers.a_3 == 3
    assert fetched_multipliers.a_4 == 4

    set_constants_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'set_constants', [
        1, 2, 3, 4, 5])

    execution_info = await hightide.get_constants().call()
    fetched_constants = execution_info.result.constants

    assert fetched_constants.a == 1
    assert fetched_constants.b == 2
    assert fetched_constants.c == 3
    assert fetched_constants.z == 4
    assert fetched_constants.e == 5

    trade_season_setup_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, 2])

    execution_info = await hightide.get_season(1).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == initial_timestamp
    assert fetched_trading_season.num_trading_days == 2

    start_trade_season_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [1])
    
    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 1

@pytest.mark.asyncio
async def test_initialize_hightide(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1,_, _, _, _ = adminAuth_factory
    
    tx_exec_info=await signer1.send_transaction(admin1, 
                                   hightide.contract_address,
                                   'set_liquidity_pool_contract_class_hash',
                                   [class_hash])

    tx_exec_info=await signer1.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', 
        [BTC_USDC_ID, 1, admin1.contract_address, 1, 2, AssetID.USDC, 1000, 0, AssetID.UST, 500, 0])

    execution_info = await hightide.get_hightide(1).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    fetched_rewards = await hightide.get_hightide_reward_tokens(1).call()
    assert fetched_rewards.result.reward_tokens_list[0].token_id == AssetID.USDC
    assert fetched_rewards.result.reward_tokens_list[0].no_of_tokens == (1000, 0)
    assert fetched_rewards.result.reward_tokens_list[1].token_id == AssetID.UST
    assert fetched_rewards.result.reward_tokens_list[1].no_of_tokens == (500, 0)

@pytest.mark.asyncio
async def test_set_block_numbers_authorized_caller(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, _, _ = adminAuth_factory

    new_block_tx = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            123243343,
        ],
    )

    assert_event_emitted(
        new_block_tx,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            1,
            123243343
        ]
    )

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343]

@pytest.mark.asyncio
async def test_set_block_numbers_authorized_caller_2(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, _, _ = adminAuth_factory

    new_block_tx = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            123243787,
        ],
    )

    assert_event_emitted(
        new_block_tx,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            1,
            123243787
        ]
    )

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343 ,123243787]

@pytest.mark.asyncio
async def test_set_xp_values_during_season(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, alice, bob = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(
            admin1,
            rewardsCalculation.contract_address,
            "set_user_xp_values",
            [
                1,
                1,
                alice.contract_address,
                to64x61(100)
            ],
        ),
        "RewardsCalculation: Season still ongoing"
    )

    xp_value_alice = await rewardsCalculation.get_user_xp_value(1, alice.contract_address).call()
    assert xp_value_alice.result.xp_value == to64x61(0) 
    

@pytest.mark.asyncio
async def test_set_xp_values_authorized_caller_0_user_address(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, alice, bob = adminAuth_factory

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp1, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    # end trade season
    await signer1.send_transaction(admin1, hightide.contract_address, 'end_trade_season', [1])

    await assert_revert(
        signer1.send_transaction(
            admin1,
            rewardsCalculation.contract_address,
            "set_user_xp_values",
            [
                1,
                1,
                0x0,
                to64x61(100)
            ],
        ),
        "RewardsCalculation: User Address cannot be 0"
    )

    xp_value_alice = await rewardsCalculation.get_user_xp_value(1, alice.contract_address).call()
    assert xp_value_alice.result.xp_value == to64x61(0) 

@pytest.mark.asyncio
async def test_set_xp_values(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, alice, bob = adminAuth_factory

    xp_tx = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_user_xp_values",
        [
            1,
            2,
            alice.contract_address,
            to64x61(100),
            bob.contract_address,
            to64x61(50)
        ],
    )

    assert_events_emitted(
        xp_tx,
        [
            [0, rewardsCalculation.contract_address, 'xp_value_set', [1, alice.contract_address, to64x61(100)]],
            [1, rewardsCalculation.contract_address, 'xp_value_set', [1, bob.contract_address, to64x61(50)]],
        ]
    )
        

    xp_value_alice = await rewardsCalculation.get_user_xp_value(1, alice.contract_address).call()
    assert xp_value_alice.result.xp_value == to64x61(100) 

    xp_value_bob = await rewardsCalculation.get_user_xp_value(1, bob.contract_address).call()
    assert xp_value_bob.result.xp_value == to64x61(50) 

@pytest.mark.asyncio
async def test_set_xp_values_reset_xp(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, alice, bob = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(
            admin1,
            rewardsCalculation.contract_address,
            "set_user_xp_values",
            [
                1,
                1,
                alice.contract_address,
                to64x61(1),
            ],
        ),
        "RewardsCalculation: Xp value already set"
    ),

    xp_value_alice = await rewardsCalculation.get_user_xp_value(1, alice.contract_address).call()
    assert xp_value_alice.result.xp_value == to64x61(100) 

@pytest.mark.asyncio
async def test_set_block_numbers_after_season_end(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, _, _ = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(
            admin1,
            rewardsCalculation.contract_address,
            "set_block_number",
            [
                123243790,
            ],
        ),
        "RewardsCalculations: No ongoing season"
    )
    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343, 123243787]

@pytest.mark.asyncio
async def test_set_block_numbers_season_2(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, _, _ = adminAuth_factory

    # Setup and start new season

    trade_season_setup_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        timestamp1, 2])

    execution_info = await hightide.get_season(2).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == timestamp1
    assert fetched_trading_season.num_trading_days == 2

    start_trade_season_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [2])
    
    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 2

    block_numbers = await rewardsCalculation.get_block_numbers(2).call()

    assert block_numbers.result.block_numbers == []


    new_block_tx_1 = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            12328000,
        ],
    )

    assert_event_emitted(
        new_block_tx_1,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            2,
            12328000
        ]
    )

    new_block_tx_2 = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            12328025,
        ],
    )

    assert_event_emitted(
        new_block_tx_2,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            2,
            12328025
        ]
    )

    new_block_tx_3 = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            12328050,
        ],
    )

    assert_event_emitted(
        new_block_tx_3,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            2,
            12328050
        ]
    )

    block_numbers = await rewardsCalculation.get_block_numbers(2).call()

    assert block_numbers.result.block_numbers == [12328000, 12328025, 12328050]

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343, 123243787]

@pytest.mark.asyncio
async def test_set_block_numbers_season_3(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, _, _ = adminAuth_factory

    # end last season

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp2, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    await signer1.send_transaction(admin1, hightide.contract_address, 'end_trade_season', [2])

    # Setup and start new season

    trade_season_setup_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        timestamp2, 3])

    execution_info = await hightide.get_season(3).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == timestamp2
    assert fetched_trading_season.num_trading_days == 3

    start_trade_season_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [3])
    
    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 3

    block_numbers = await rewardsCalculation.get_block_numbers(3).call()

    assert block_numbers.result.block_numbers == []


    new_block_tx_1 = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            12328090,
        ],
    )

    assert_event_emitted(
        new_block_tx_1,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            3,
            12328090
        ]
    )

    new_block_tx_2 = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            12328095,
        ],
    )

    assert_event_emitted(
        new_block_tx_2,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            3,
            12328095
        ]
    )

    new_block_tx_3 = await signer1.send_transaction(
        admin1,
        rewardsCalculation.contract_address,
        "set_block_number",
        [
            12328125,
        ],
    )

    assert_event_emitted(
        new_block_tx_3,
        from_address=rewardsCalculation.contract_address,
        name="block_number_set",
        data=[
            3,
            12328125
        ]
    )

    block_numbers = await rewardsCalculation.get_block_numbers(3).call()

    assert block_numbers.result.block_numbers == [12328090, 12328095, 12328125]

    block_numbers = await rewardsCalculation.get_block_numbers(2).call()

    assert block_numbers.result.block_numbers == [12328000, 12328025, 12328050]

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343, 123243787]

