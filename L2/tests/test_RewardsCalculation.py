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
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3, signer4

BTC_ID = str_to_felt("32f0406jz7qj8")
USDC_ID = str_to_felt("fghj3am52qpzsib")
UST_ID = str_to_felt("yjk45lvmasopq")
BTC_USDC_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")

alice_signer = Signer(123456789987654323)
bob_signer = Signer(123456789987654324)

initial_timestamp = int(time.time())
timestamp2 = int(time.time()) + (60*60*24) + 60
timestamp3 = int(time.time()) + (60*60*24)*2 + 60
timestamp4 = int(time.time()) + (60*60*24)*3 + 60
timestamp5 = int(time.time()) + (60*60*24)*31 + 60

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
    rewardsCalculation = await starknet_service.deploy(ContractType.RewardsCalculation, [registry.contract_address, 1])
    validator_router = await starknet_service.deploy(ContractType.ValidatorRouter, [registry.contract_address, 1])
    sig_req_manager = await starknet_service.deploy(ContractType.SigRequirementsManager,[registry.contract_address, 1])
    pubkey_whitelister = await starknet_service.deploy(ContractType.PubkeyWhitelister, [registry.contract_address, 1])

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
    await signer1.send_transaction(admin1, registry.contract_address, "update_contract_registry", [22, 1, pubkey_whitelister.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, "update_contract_registry", [23, 1, sig_req_manager.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, "update_contract_registry", [28, 1, validator_router.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, "update_contract_registry", [29, 1, rewardsCalculation.contract_address])

    # Add assets
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [BTC_ID, 1, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 8, 0, 1, 1, 10, to64x61(1), to64x61(10), to64x61(10), 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [USDC_ID, 1, str_to_felt("USDC"), str_to_felt("USDC"), 0, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [UST_ID, 1, str_to_felt("UST"), str_to_felt("UST"), 1, 1, 6, 0, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add markets
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [BTC_USDC_ID, BTC_ID, USDC_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [BTC_UST_ID, BTC_ID, UST_ID, to64x61(10), 1, 0, 60, 1, 1, 10, to64x61(1), to64x61(5), to64x61(3), 1, 1, 1, 100, 1000, 10000])

    # Add set_block_number to signature infra
    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [29, 1, get_selector_from_name("set_block_number"), 2],
    )

    # Add set_user_xp_values to signature infra 
    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [29, 1, get_selector_from_name("set_user_xp_values"), 2],
    )

    # Whitelist pubkeys
    await signer1.send_transaction(
        admin1,
        pubkey_whitelister.contract_address,
        "whitelist_pubkey",
        [signer3.public_key],
    )

    await signer1.send_transaction(
        admin1,
        pubkey_whitelister.contract_address,
        "whitelist_pubkey",
        [signer4.public_key],
    )

    # turn on signature check master switch in the ValidatorRouter
    await signer1.send_transaction(
        admin1, validator_router.contract_address, "toggle_check_sig", []
    )

    return adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, alice, bob

@pytest.mark.asyncio
async def test_setup_trading_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, _, _, _, _, _, _, _ = adminAuth_factory

    set_multipliers_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'set_multipliers', [
        1, 2, 3, 4])

    execution_info = await hightide.get_multipliers().call()
    fetched_multipliers = execution_info.result.multipliers

    assert fetched_multipliers.a1 == 1
    assert fetched_multipliers.a2 == 2
    assert fetched_multipliers.a3 == 3
    assert fetched_multipliers.a4 == 4

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
    adminAuth, hightide, admin1, admin2, user1, _, _, _, _, _, _, _ = adminAuth_factory
    
    tx_exec_info=await signer1.send_transaction(admin1, 
                                   hightide.contract_address,
                                   'set_liquidity_pool_contract_class_hash',
                                   [class_hash])

    tx_exec_info=await signer1.send_transaction(admin1, hightide.contract_address, 'initialize_high_tide', 
        [BTC_USDC_ID, 1, admin1.contract_address, 1, 2, USDC_ID, 1000, 0, UST_ID, 500, 0])

    execution_info = await hightide.get_hightide(1).call()
    liquidity_pool_address = execution_info.result.hightide_metadata.liquidity_pool_address

    fetched_rewards = await hightide.get_hightide_reward_tokens(1).call()
    assert fetched_rewards.result.reward_tokens_list[0].token_id == USDC_ID
    assert fetched_rewards.result.reward_tokens_list[0].no_of_tokens == (1000, 0)
    assert fetched_rewards.result.reward_tokens_list[1].token_id == UST_ID
    assert fetched_rewards.result.reward_tokens_list[1].no_of_tokens == (500, 0)

@pytest.mark.asyncio
async def test_set_block_number_direct_wo_sigs(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, _, _ = adminAuth_factory

    await assert_revert( 
        signer1.send_transaction(
            admin1, 
            rewardsCalculation.contract_address, 
            'set_block_number', 
            [7247809324]
        ),
        "RewardsCalculation: Unauthorized call"
    )

@pytest.mark.asyncio
async def test_set_block_numbers_unauthorized_caller(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, _, _ = adminAuth_factory

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            compute_hash_on_elements([123243343]),
        ]
    )

    user1_sig = signer1.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                29,
                1,
                current_nonce,
                get_selector_from_name("set_block_number"),
                1,
                123243343,
                2,
                user1_sig[0],
                user1_sig[1],
                user4_sig[0],
                user4_sig[1],
                2,
                signer1.public_key,
                signer4.public_key,
            ],
        ),
        "SigRequirementsManager: Insufficient no. of valid signatures"
    )

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == []

@pytest.mark.asyncio
async def test_set_block_numbers_authorized_caller(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, _, _ = adminAuth_factory

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            compute_hash_on_elements([123243343]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            1,
            123243343,
            2,
            user3_sig[0],
            user3_sig[1],
            user4_sig[0],
            user4_sig[1],
            2,
            signer3.public_key,
            signer4.public_key,
        ],
    )

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343]

@pytest.mark.asyncio
async def test_set_block_numbers_authorized_caller_2(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, _, _ = adminAuth_factory

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            compute_hash_on_elements([123243787]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            1,
            123243787,
            2,
            user3_sig[0],
            user3_sig[1],
            user4_sig[0],
            user4_sig[1],
            2,
            signer3.public_key,
            signer4.public_key,
        ],
    )

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343 ,123243787]

@pytest.mark.asyncio
async def test_set_xp_values_unauthorized_caller(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, alice, bob = adminAuth_factory

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_user_xp_values"),
            compute_hash_on_elements([1, alice.contract_address, to64x61(100)]),
        ]
    )

    user1_sig = signer1.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                29,
                1,
                current_nonce,
                get_selector_from_name("set_user_xp_values"),
                3,
                1,
                alice.contract_address,
                to64x61(100),
                2,
                user1_sig[0],
                user1_sig[1],
                user4_sig[0],
                user4_sig[1],
                2,
                signer1.public_key,
                signer4.public_key,
            ],
        ),
        "SigRequirementsManager: Insufficient no. of valid signatures"
    )

@pytest.mark.asyncio
async def test_set_xp_values_authorized_caller_0_user_address(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, alice, bob = adminAuth_factory

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_user_xp_values"),
            compute_hash_on_elements([1, 1, 0x0, to64x61(100)]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                29,
                1,
                current_nonce,
                get_selector_from_name("set_user_xp_values"),
                # calldata len
                4,
                # calldata
                1,
                1,
                0x0,
                to64x61(100),
                # sig len
                2,
                # sigs
                user3_sig[0],
                user3_sig[1],
                user4_sig[0],
                user4_sig[1],
                # pub key lens
                2,
                # pub key
                signer3.public_key,
                signer4.public_key,
            ],
        ), 
        "RewardsCalculation: User Address cannot be 0"
    )

    xp_value_alice = await rewardsCalculation.get_user_xp_value(1, alice.contract_address).call()
    assert xp_value_alice.result.xp_value == to64x61(0) 

@pytest.mark.asyncio
async def test_set_xp_values_authorized_caller(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, alice, bob = adminAuth_factory

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_user_xp_values"),
            compute_hash_on_elements([1, 2, alice.contract_address, to64x61(100), bob.contract_address, to64x61(50)]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_user_xp_values"),
            # calldata len
            6,
            # calldata
            1,
            2,
            alice.contract_address,
            to64x61(100),
            bob.contract_address,
            to64x61(50),
            # sig len
            2,
            # sigs
            user3_sig[0],
            user3_sig[1],
            user4_sig[0],
            user4_sig[1],
            # pub key lens
            2,
            # pub key
            signer3.public_key,
            signer4.public_key,
        ],
    )

    xp_value_alice = await rewardsCalculation.get_user_xp_value(1, alice.contract_address).call()
    assert xp_value_alice.result.xp_value == to64x61(100) 

    xp_value_bob = await rewardsCalculation.get_user_xp_value(1, bob.contract_address).call()
    assert xp_value_bob.result.xp_value == to64x61(50) 

@pytest.mark.asyncio
async def test_set_xp_values_authorized_caller_reset_xp(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, alice, bob = adminAuth_factory

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_user_xp_values"),
            compute_hash_on_elements([1, 1, alice.contract_address, to64x61(100)]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                29,
                1,
                current_nonce,
                get_selector_from_name("set_user_xp_values"),
                # calldata len
                4,
                # calldata
                1,
                1,
                alice.contract_address,
                to64x61(100),
                # sig len
                2,
                # sigs
                user3_sig[0],
                user3_sig[1],
                user4_sig[0],
                user4_sig[1],
                # pub key lens
                2,
                # pub key
                signer3.public_key,
                signer4.public_key,
            ],
        )
    )

    xp_value_alice = await rewardsCalculation.get_user_xp_value(1, alice.contract_address).call()
    assert xp_value_alice.result.xp_value == to64x61(100) 

@pytest.mark.asyncio
async def test_set_xp_values_authorized_caller_wo_sigs(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, alice, _ = adminAuth_factory

    await assert_revert( 
        signer1.send_transaction(
            admin1, 
            rewardsCalculation.contract_address, 
            'set_user_xp_values', 
            [
                1, 
                1,
                alice.contract_address,
                to64x61(100)
            ]
        ),
        "RewardsCalculation: Unauthorized call"
    )

@pytest.mark.asyncio
async def test_set_block_numbers_after_season_end(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, _, _ = adminAuth_factory

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp5, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address,
        starknet_version = STARKNET_VERSION
    )

    # end trade season
    await signer1.send_transaction(admin1, hightide.contract_address, 'end_trade_season', [1])
    
    
    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            compute_hash_on_elements([123243787]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                29,
                1,
                current_nonce,
                get_selector_from_name("set_block_number"),
                1,
                123243787,
                2,
                user3_sig[0],
                user3_sig[1],
                user4_sig[0],
                user4_sig[1],
                2,
                signer3.public_key,
                signer4.public_key,
            ],
        ),
        "RewardsCalculations: No ongoing season"
    )
    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343, 123243787]

@pytest.mark.asyncio
async def test_set_block_numbers_new_season(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1, rewardsCalculation, starknet_service, validator_router, sig_req_manager, pubkey_whitelister, _, _ = adminAuth_factory

    # Setup and start new season

    trade_season_setup_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        timestamp5, 2])

    execution_info = await hightide.get_season(2).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == timestamp5
    assert fetched_trading_season.num_trading_days == 2

    start_trade_season_tx = await signer1.send_transaction(admin1, hightide.contract_address, 'start_trade_season', [2])
    
    execution_info = await hightide.get_current_season_id().call()
    fetched_season_id = execution_info.result.season_id

    assert fetched_season_id == 2

    block_numbers = await rewardsCalculation.get_block_numbers(2).call()

    assert block_numbers.result.block_numbers == []


    # Set block number

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            compute_hash_on_elements([12328000]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)


    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            29,
            1,
            current_nonce,
            get_selector_from_name("set_block_number"),
            1,
            12328000,
            2,
            user3_sig[0],
            user3_sig[1],
            user4_sig[0],
            user4_sig[1],
            2,
            signer3.public_key,
            signer4.public_key,
        ],
    )

    block_numbers = await rewardsCalculation.get_block_numbers(2).call()

    assert block_numbers.result.block_numbers == [12328000]

    block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    assert block_numbers.result.block_numbers == [123243343, 123243787]




    # await signer1.send_transaction(admin1, rewardsCalculation.contract_address, 'set_block_number', [343123432])

    # block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    # print(block_numbers.result.block_numbers)

    # await signer1.send_transaction(admin1, rewardsCalculation.contract_address, 'set_block_number', [4768712769])

    # block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    # print(block_numbers.result.block_numbers)

    # await signer1.send_transaction(admin1, rewardsCalculation.contract_address, 'set_block_number', [7247809324])

    # block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    # print(block_numbers.result.block_numbers)

   
    # await signer1.send_transaction(admin1, hightide.contract_address, 'end_trade_season', [1])

    # await assert_revert(signer1.send_transaction(admin1, rewardsCalculation.contract_address, 'set_block_number', [7247809324]))


    # block_numbers = await rewardsCalculation.get_block_numbers(1).call()

    # print(block_numbers.result.block_numbers)









