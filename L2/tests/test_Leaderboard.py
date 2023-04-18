from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, print_parsed_positions, print_parsed_collaterals, assert_event_emitted
from utils_asset import AssetID, build_asset_properties
from utils_markets import MarketProperties
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)
charlie_signer = Signer(123456789987654325)

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
class_hash = 0

initial_timestamp = int(time.time())
timestamp1 = int(time.time()) + 100
timestamp2 = int(time.time()) + 299
timestamp3 = int(time.time()) + 300
timestamp4 = int(time.time()) + 301
timestamp5 = int(time.time()) + 600

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
    ### Deploy infrastructure (Part 1)
    admin1 = await starknet_service.deploy(ContractType.Account, [
        admin1_signer.public_key
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        admin2_signer.public_key
    ])
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])

    contract_class = starknet_service.contracts_holder.get_contract_class(ContractType.LiquidityPool)
    global class_hash
    class_hash, _ = await starknet_service.starknet.state.declare(contract_class)
    direct_class_hash = compute_class_hash(contract_class)
    class_hash = int.from_bytes(class_hash,'big')
    assert direct_class_hash == class_hash

    ### Deploy user accounts
    account_factory = AccountFactory(
        starknet_service,
        L1_dummy_address,
        registry.contract_address,
        1
    )
    alice = await account_factory.deploy_ZKX_account(alice_signer.public_key)
    bob = await account_factory.deploy_ZKX_account(bob_signer.public_key)
    charlie = await account_factory.deploy_ZKX_account(charlie_signer.public_key)

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=initial_timestamp, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    ### Deploy infrastructure (Part 2)
    market = await starknet_service.deploy(ContractType.Markets, [registry.contract_address, 1])
    hightide = await starknet_service.deploy(ContractType.TestHighTide, [registry.contract_address, 1])
    leaderboard = await starknet_service.deploy(ContractType.Leaderboard, [registry.contract_address, 1])

    # Access 1 allows adding and removing assets from the system
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])

    # Access 2 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])

    # Access 3 allows adding trusted contracts to the registry
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 4, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 5, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 7, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 8, 1])
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 10, 1])

    # spoof admin1 as account_deployer so that it can update account registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [20, 1, admin1.contract_address])

    # add user accounts to account registry
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[admin1.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[admin2.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[alice.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[bob.contract_address])
    await admin1_signer.send_transaction(admin1, account_registry.contract_address, 'add_to_account_registry',[charlie.contract_address])

    # Update contract addresses in registry
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [24, 1, hightide.contract_address])

    # Add assets
    BTC_properties = build_asset_properties(
        id=AssetID.BTC,
        asset_version=1,
        short_name=str_to_felt("BTC"),
        is_tradable=True,
        is_collateral=False,
        token_decimal=8
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', BTC_properties)

    ETH_properties = build_asset_properties(
        id=AssetID.ETH,
        asset_version=1,
        short_name=str_to_felt("ETH"),
        is_tradable=True,
        is_collateral=False,
        token_decimal=18
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', ETH_properties)
    
    USDC_properties = build_asset_properties(
        id=AssetID.USDC,
        asset_version=1,
        short_name=str_to_felt("USDC"),
        is_tradable=False,
        is_collateral=True,
        token_decimal=6
    )
    await admin1_signer.send_transaction(admin1, asset.contract_address, 'add_asset', USDC_properties)

    # Add markets
    BTC_USD_properties = MarketProperties(
        id=BTC_USD_ID,
        asset=AssetID.BTC,
        asset_collateral=AssetID.USDC,
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        tick_precision=0,
        step_size=1,
        step_precision=0,
        minimum_order_size=10,
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(10),
        currently_allowed_leverage=to64x61(10),
        maintenance_margin_fraction=1,
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', BTC_USD_properties.to_params_list())

    ETH_USD_properties = MarketProperties(
        id=ETH_USD_ID,
        asset=AssetID.ETH,
        asset_collateral=AssetID.USDC,
        is_tradable=True,
        is_archived=False,
        ttl=60,
        tick_size=1,
        tick_precision=0,
        step_size=1,
        step_precision=0,
        minimum_order_size=10,
        minimum_leverage=to64x61(1),
        maximum_leverage=to64x61(5),
        currently_allowed_leverage=to64x61(3),
        maintenance_margin_fraction=1,
        initial_margin_fraction=1,
        incremental_initial_margin_fraction=1,
        incremental_position_size=100,
        baseline_position_size=1000,
        maximum_position_size=10000
    )
    await admin1_signer.send_transaction(admin1, market.contract_address, 'add_market', ETH_USD_properties.to_params_list())

    season_id = 1
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        initial_timestamp, 4])
    
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [1])

    await admin1_signer.send_transaction(admin1, hightide.contract_address,'set_liquidity_pool_contract_class_hash',[class_hash])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', [ETH_USD_ID, 1, admin1.contract_address, 1, 2, AssetID.USDC, 1000, 0, AssetID.UST, 500, 0])
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', [BTC_USD_ID, 1, admin1.contract_address, 1, 2, AssetID.USDC, 1000, 0, AssetID.UST, 500, 0])

    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'activate_high_tide', [1])
    await admin1_signer.send_transaction(admin1, hightide.contract_address, 'activate_high_tide', [2])

    return starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard

@pytest.mark.asyncio
async def test_setting_time_between_calls_unauthorized(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

    await assert_revert(
        admin2_signer.send_transaction(admin2, leaderboard.contract_address, "set_time_between_calls", [300]),
        "Leaderboard: Unauthorized call"
    )

    time_between_calls = await leaderboard.get_time_between_calls().call()
    assert time_between_calls.result.time_between_calls == 0

@pytest.mark.asyncio
async def test_setting_time_between_calls_invalid(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

    await assert_revert(
        admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_time_between_calls", [0]),
        "Leaderboard: Invalid time_between_calls provided"
    )

    time_between_calls = await leaderboard.get_time_between_calls().call()
    assert time_between_calls.result.time_between_calls == 0

@pytest.mark.asyncio
async def test_setting_set_number_of_top_traders_unauthorized(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

    await assert_revert(
        admin2_signer.send_transaction(admin2, leaderboard.contract_address, "set_number_of_top_traders", [10]),
        "Leaderboard: Unauthorized call"
    )

    number_of_top_traders = await leaderboard.get_number_of_top_traders().call()
    assert number_of_top_traders.result.number_of_top_traders == 0

@pytest.mark.asyncio
async def test_setting_time_between_calls_invalid(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

    await assert_revert(
        admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_number_of_top_traders", [0]),
        "Leaderboard: Invalid number_of_traders provided"
    )

    number_of_top_traders = await leaderboard.get_number_of_top_traders().call()
    assert number_of_top_traders.result.number_of_top_traders == 0

@pytest.mark.asyncio
async def test_setting_params_admin(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
    # Admin setting params
    traders_tx = await admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_number_of_top_traders", [2])
    time_between_tx = await admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_time_between_calls", [300])

    assert_event_emitted(
        traders_tx,
        from_address=leaderboard.contract_address,
        name="number_of_top_traders_update",
        data=[
            0,
            2
        ]
    )

    assert_event_emitted(
        time_between_tx,
        from_address=leaderboard.contract_address,
        name="time_between_calls_update",
        data=[
            0,
            300
        ]
    )

    number_of_top_traders = await leaderboard.get_number_of_top_traders().call()
    assert number_of_top_traders.result.number_of_top_traders == 2

    time_between_calls = await leaderboard.get_time_between_calls().call()
    assert time_between_calls.result.time_between_calls == 300

@pytest.mark.asyncio
async def test_setting_leaderboard_wrong_number_of_traders(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

    await assert_revert(
        admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_leaderboard", 
            [
                BTC_USD_ID,
                3,
                alice.contract_address,
                to64x61(10),
                bob.contract_address,
                to64x61(21),
                charlie.contract_address,
                to64x61(32)

            ]
        ),
        "Leaderboard: Invalid number of entries"
    )

# @pytest.mark.asyncio
# async def test_setting_leaderboard_invalid_reward(adminAuth_factory):
#     starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

#     await assert_revert(
#         admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_leaderboard", 
#             [
#                 BTC_USD_ID,
#                 2,
#                 alice.contract_address,
#                 -1,
#                 bob.contract_address,
#                 to64x61(21),
#             ]
#         ),
#         "Leaderboard: Invalid number of entries"
#     )


@pytest.mark.asyncio
async def test_setting_leaderboard_btc(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

    set_leaderboard = await admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_leaderboard", 
        [
            BTC_USD_ID,
            2,
            alice.contract_address,
            to64x61(10),
            bob.contract_address,
            to64x61(21)

        ]
    )

    assert_event_emitted(
        set_leaderboard,
        from_address=leaderboard.contract_address,
        name="leaderboard_update",
        data=[
            1,
            BTC_USD_ID,
            0,
            initial_timestamp
        ]
    )

    leaderboard_positions = await leaderboard.get_leaderboard_epoch(1, BTC_USD_ID, 0).call()
    parsed_leaderboard_positions = list(leaderboard_positions.result.leaderboard_array)
    print(parsed_leaderboard_positions)

    assert parsed_leaderboard_positions[0].user_address == alice.contract_address
    assert parsed_leaderboard_positions[0].reward == to64x61(10)

    assert parsed_leaderboard_positions[1].user_address == bob.contract_address
    assert parsed_leaderboard_positions[1].reward == to64x61(21)

    set_timestamp = await leaderboard.get_epoch_to_timestamp(1, BTC_USD_ID, 0).call()
    assert set_timestamp.result.timestamp == initial_timestamp

@pytest.mark.asyncio
async def test_get_status_1(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
  
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp1, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    time_remaining = await leaderboard.get_next_call(BTC_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 200

    status = await leaderboard.get_call_status(BTC_USD_ID).call()
    assert status.result.status == 0

    time_remaining = await leaderboard.get_next_call(ETH_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 0

    status = await leaderboard.get_call_status(ETH_USD_ID).call()
    assert status.result.status == 1



@pytest.mark.asyncio
async def test_setting_leaderboard_eth(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory

    set_leaderboard = await admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_leaderboard", 
        [
            ETH_USD_ID,
            2,
            alice.contract_address,
            to64x61(120),
            bob.contract_address,
            to64x61(241)

        ]
    )

    assert_event_emitted(
        set_leaderboard,
        from_address=leaderboard.contract_address,
        name="leaderboard_update",
        data=[
            1,
            ETH_USD_ID,
            0,
            timestamp1
        ]
    )

    leaderboard_positions = await leaderboard.get_leaderboard_epoch(1, ETH_USD_ID, 0).call()
    parsed_leaderboard_positions = list(leaderboard_positions.result.leaderboard_array)
    print(parsed_leaderboard_positions)

    assert parsed_leaderboard_positions[0].user_address == alice.contract_address
    assert parsed_leaderboard_positions[0].reward == to64x61(120)

    assert parsed_leaderboard_positions[1].user_address == bob.contract_address
    assert parsed_leaderboard_positions[1].reward == to64x61(241)

    set_timestamp = await leaderboard.get_epoch_to_timestamp(1, ETH_USD_ID, 0).call()
    assert set_timestamp.result.timestamp == timestamp1



@pytest.mark.asyncio
async def test_get_status_2(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
  
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp2, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    time_remaining = await leaderboard.get_next_call(BTC_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 1

    status = await leaderboard.get_call_status(BTC_USD_ID).call()
    assert status.result.status == 0

    time_remaining = await leaderboard.get_next_call(ETH_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 101

    status = await leaderboard.get_call_status(ETH_USD_ID).call()
    assert status.result.status == 0

@pytest.mark.asyncio
async def test_setting_leaderboard_before_time(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
    
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, leaderboard.contract_address, "set_leaderboard", 
            [
                BTC_USD_ID,
                2,
                alice.contract_address,
                to64x61(13),
                bob.contract_address,
                to64x61(26)

            ]
        ),
        "Leaderboard: Cool down period"
    )
  

@pytest.mark.asyncio
async def test_get_status_3(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
  
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp3, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    time_remaining = await leaderboard.get_next_call(BTC_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 0

    status = await leaderboard.get_call_status(BTC_USD_ID).call()
    assert status.result.status == 1

    time_remaining = await leaderboard.get_next_call(ETH_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 100

    status = await leaderboard.get_call_status(ETH_USD_ID).call()
    assert status.result.status == 0

@pytest.mark.asyncio
async def test_get_status_4(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
  
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp4, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    time_remaining = await leaderboard.get_next_call(BTC_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 0

    status = await leaderboard.get_call_status(BTC_USD_ID).call()
    assert status.result.status == 1

    time_remaining = await leaderboard.get_next_call(ETH_USD_ID).call()
    assert time_remaining.result.remaining_seconds == 99

    status = await leaderboard.get_call_status(ETH_USD_ID).call()
    assert status.result.status == 0

@pytest.mark.asyncio
async def test_setting_leaderboard_btc_2(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
  
    set_leaderboard = await admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_leaderboard", 
        [
            BTC_USD_ID,
            2,
            bob.contract_address,
            to64x61(71),
            alice.contract_address,
            to64x61(17),
        ]
    )

    assert_event_emitted(
        set_leaderboard,
        from_address=leaderboard.contract_address,
        name="leaderboard_update",
        data=[
            1,
            BTC_USD_ID,
            1,
            timestamp4
        ]
    )

    leaderboard_positions = await leaderboard.get_leaderboard_epoch(1, BTC_USD_ID, 1).call()
    parsed_leaderboard_positions = list(leaderboard_positions.result.leaderboard_array)
    print(parsed_leaderboard_positions)

    assert parsed_leaderboard_positions[0].user_address == bob.contract_address
    assert parsed_leaderboard_positions[0].reward == to64x61(71)

    assert parsed_leaderboard_positions[1].user_address == alice.contract_address
    assert parsed_leaderboard_positions[1].reward == to64x61(17)

    set_timestamp = await leaderboard.get_epoch_to_timestamp(1, BTC_USD_ID, 1).call()
    assert set_timestamp.result.timestamp == timestamp4

@pytest.mark.asyncio
async def test_setting_eth_leaderboard_before_time(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
    
    await assert_revert(
        admin1_signer.send_transaction(
            admin1, leaderboard.contract_address, "set_leaderboard", 
            [
                ETH_USD_ID,
                2,
                alice.contract_address,
                to64x61(423),
                bob.contract_address,
                to64x61(926)

            ]
        ),
        "Leaderboard: Cool down period"
    )

@pytest.mark.asyncio
async def test_setting_leaderboard_eth_2(adminAuth_factory):
    starknet_service, adminAuth, admin1, admin2, alice, bob, charlie, leaderboard = adminAuth_factory
    
    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp5, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    set_leaderboard = await admin1_signer.send_transaction(admin1, leaderboard.contract_address, "set_leaderboard", 
        [
            ETH_USD_ID,
            2,
            bob.contract_address,
            to64x61(926),
            alice.contract_address,
            to64x61(423),
        ]
    )

    assert_event_emitted(
        set_leaderboard,
        from_address=leaderboard.contract_address,
        name="leaderboard_update",
        data=[
            1,
            ETH_USD_ID,
            1,
            timestamp5
        ]
    )

    leaderboard_positions = await leaderboard.get_leaderboard_epoch(1, ETH_USD_ID, 1).call()
    parsed_leaderboard_positions = list(leaderboard_positions.result.leaderboard_array)
    print(parsed_leaderboard_positions)

    assert parsed_leaderboard_positions[0].user_address == bob.contract_address
    assert parsed_leaderboard_positions[0].reward == to64x61(926)

    assert parsed_leaderboard_positions[1].user_address == alice.contract_address
    assert parsed_leaderboard_positions[1].reward == to64x61(423)

    set_timestamp = await leaderboard.get_epoch_to_timestamp(1, ETH_USD_ID, 1).call()
    assert set_timestamp.result.timestamp == timestamp5
  