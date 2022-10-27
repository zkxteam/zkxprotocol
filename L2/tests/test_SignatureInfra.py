import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import DeclaredClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from starkware.starknet.public.abi import get_selector_from_name
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.testing.contract import StarknetContract
from starkware.cairo.common.hash_state import compute_hash_on_elements
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address


signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(12345)
signer4 = Signer(56789)


@pytest.fixture(scope="module")
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope="module")
async def adminAuth_factory(starknet_service: StarknetService):

    admin1 = await starknet_service.deploy(ContractType.Account, [
        signer1.public_key
    ])
    admin2 = await starknet_service.deploy(ContractType.Account, [
        signer2.public_key
    ])

    user3 = await starknet_service.deploy(ContractType.Account, [
        signer3.public_key
    ])

    user4 = await starknet_service.deploy(ContractType.Account, [
        signer4.public_key
    ])

    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])

    test_asset = await starknet_service.deploy(
        ContractType.TestAsset, []
    )

    validator_router = await starknet_service.deploy(
        ContractType.ValidatorRouter,
        [registry.contract_address, 1],
    )

    sig_req_manager = await starknet_service.deploy(
        ContractType.SigRequirementsManager,
        [registry.contract_address, 1],
    )

    pubkey_whitelister = await starknet_service.deploy(
        ContractType.PubkeyWhitelister,
        [registry.contract_address, 1],
    )

    await signer1.send_transaction(
        admin1,
        adminAuth.contract_address,
        "update_admin_mapping",
        [admin1.contract_address, 3, 1],
    )
    await signer1.send_transaction(
        admin1,
        registry.contract_address,
        "update_contract_registry",
        [22, 1, pubkey_whitelister.contract_address],
    )
    await signer1.send_transaction(
        admin1,
        registry.contract_address,
        "update_contract_registry",
        [23, 1, sig_req_manager.contract_address],
    )

    await signer1.send_transaction(
        admin1,
        registry.contract_address,
        "update_contract_registry",
        [1, 1, test_asset.contract_address],
    )

    return (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    )


@pytest.mark.asyncio
async def test_unauthorised_whitelist(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await assert_revert(
        signer3.send_transaction(
            user3,
            pubkey_whitelister.contract_address,
            "whitelist_pubkey",
            [signer1.public_key],
        ),
        reverted_with="Caller Check: Unauthorized caller"
    )


@pytest.mark.asyncio
async def test_unauthorised_set_sig_req(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await assert_revert(
        signer3.send_transaction(
            user3,
            sig_req_manager.contract_address,
            "set_sig_requirement",
            [1, 1, get_selector_from_name("set_asset_value"), 2],
        ),
        reverted_with="Caller Check: Unauthorized caller"
    )


@pytest.mark.asyncio
async def test_unauthorised_deregister(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await assert_revert(
        signer3.send_transaction(
            user3,
            sig_req_manager.contract_address,
            "deregister_func",
            [1, 1, get_selector_from_name("set_asset_value")],
        ),
        reverted_with="Caller Check: Unauthorized caller"
    )


@pytest.mark.asyncio
async def test_unauthorised_delist(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await assert_revert(
        signer3.send_transaction(
            user3,
            pubkey_whitelister.contract_address,
            "delist_pubkey",
            [signer3.public_key],
        )
    ),
    reverted_with="Caller Check: Unauthorized caller"


@pytest.mark.asyncio
async def test_simple_call_flow(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 2],
    )

    current_sig_req = await sig_req_manager.get_sig_requirement(
        (1, 1, get_selector_from_name("set_asset_value"))
    ).call()

    current_sig_req = current_sig_req.result.num_req

    assert current_sig_req == 2

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

    # get current nonce from ValidatorRouter
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    current_asset_value = await test_asset.get_asset_value().call()

    current_asset_value = current_asset_value.result.res

    assert current_asset_value == 0

    # calculate hash of core function call, this will be signed by the users / nodes
    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([10]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)

    # call core function with required parameters, ref ValidatorRouter.cairo for exact param list and meanings
    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            1,
            10,
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

    current_asset_value = await test_asset.get_asset_value().call()
    current_asset_value = current_asset_value.result.res

    assert current_asset_value == 10


@pytest.mark.asyncio
async def test_call_with_incorrect_nonce(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 1],
    )

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    current_asset_value = await test_asset.get_asset_value().call()

    current_asset_value = current_asset_value.result.res

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            0,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([20]),
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
                1,
                1,
                0,
                get_selector_from_name("set_asset_value"),
                1,
                20,
                1,
                user3_sig[0],
                user3_sig[1],
                1,
                signer3.public_key,
            ],
        ),
        reverted_with="SigRequirementsManager: Nonce mismatch"
    )


@pytest.mark.asyncio
async def test_call_with_incorrect_signature(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([200]),
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
                1,
                1,
                current_nonce,
                get_selector_from_name("set_asset_value"),
                1,
                200,
                1,
                # here we are deliberately sending user4 signatures but user3 pubkey
                user4_sig[0],
                user4_sig[1],
                1,
                signer3.public_key,
            ],
        )
    )
    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                1,
                1,
                current_nonce,
                get_selector_from_name("set_asset_value"),
                1,
                30,  # signed data was 200 - data tampering should revert call due to signature mismatch
                1,
                user3_sig[0],
                user3_sig[1],
                1,
                signer3.public_key,
            ],
        )
    )


@pytest.mark.asyncio
async def test_call_with_insufficient_sig(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 2],
    )

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    current_sig_req = await sig_req_manager.get_sig_requirement(
        (1, 1, get_selector_from_name("set_asset_value"))
    ).call()

    current_sig_req = current_sig_req.result.num_req

    assert current_sig_req == 2

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([20]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)
    # calling with 1 signature for a requirement of 2 signatures
    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                1,
                1,
                current_nonce,
                get_selector_from_name("set_asset_value"),
                1,
                20,
                1,
                user3_sig[0],
                user3_sig[1],
                1,
                signer3.public_key,
            ],
        ),
        reverted_with="SigRequirementsManager: No. of signatures sent is less than number required"
    )


@pytest.mark.asyncio
async def test_call_with_more_than_req_sig(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 1],
    )

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([20]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)

    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            1,
            20,
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

    current_asset_value = await test_asset.get_asset_value().call()
    current_asset_value = current_asset_value.result.res
    assert current_asset_value == 20


@pytest.mark.asyncio
async def test_call_with_0_sig(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 0],
    )

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([30]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)

    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            1,
            30,
            1,
            user3_sig[0],
            user3_sig[1],
            1,
            signer3.public_key,
        ],
    )

    current_asset_value = await test_asset.get_asset_value().call()
    current_asset_value = current_asset_value.result.res
    assert current_asset_value == 30

    # when there is 0 sig requirement then sig check is not performed and hence even an incorrect sig works
    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([40]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)

    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            1,
            40,
            1,
            # sig and pubkey mismatch will also work since there is 0 sig requirement
            user4_sig[0],
            user4_sig[1],
            1,
            signer3.public_key,
        ],
    )

    current_asset_value = await test_asset.get_asset_value().call()
    current_asset_value = current_asset_value.result.res
    assert current_asset_value == 40


@pytest.mark.asyncio
async def test_call_with_sig_check_turned_off(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 2],
    )

    should_check_sig = await validator_router.get_check_sig().call()
    should_check_sig = should_check_sig.result.res

    assert should_check_sig == 1

    await signer1.send_transaction(
        admin1, validator_router.contract_address, "toggle_check_sig", []
    )

    should_check_sig = await validator_router.get_check_sig().call()
    should_check_sig = should_check_sig.result.res

    assert should_check_sig == 0

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([50]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)

    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            1,
            50,
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

    current_asset_value = await test_asset.get_asset_value().call()
    current_asset_value = current_asset_value.result.res
    assert current_asset_value == 50


@pytest.mark.asyncio
async def test_call_with_delisted_pubkey(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 1],
    )

    await signer1.send_transaction(
        admin1,
        pubkey_whitelister.contract_address,
        "delist_pubkey",
        [signer3.public_key],
    )

    await signer1.send_transaction(
        admin1,
        pubkey_whitelister.contract_address,
        "whitelist_pubkey",
        [signer4.public_key],
    )

    await signer1.send_transaction(
        admin1, validator_router.contract_address, "toggle_check_sig", []
    )

    should_check_sig = await validator_router.get_check_sig().call()
    should_check_sig = should_check_sig.result.res

    assert should_check_sig == 1

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([70]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)

    await signer1.send_transaction(
        admin1,
        validator_router.contract_address,
        "call_core_function",
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            1,
            70,
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

    current_asset_value = await test_asset.get_asset_value().call()
    current_asset_value = current_asset_value.result.res

    assert current_asset_value == 70

    # call should revert if there are no valid pubkeys signing the call

    is_whitelisted = await pubkey_whitelister.is_whitelisted(signer4.public_key).call()
    is_whitelisted = is_whitelisted.result.res

    assert is_whitelisted == 1

    await signer1.send_transaction(
        admin1,
        pubkey_whitelister.contract_address,
        "delist_pubkey",
        [signer4.public_key],
    )

    is_whitelisted = await pubkey_whitelister.is_whitelisted(signer4.public_key).call()
    is_whitelisted = is_whitelisted.result.res

    assert is_whitelisted == 0

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([80]),
        ]
    )

    user3_sig = signer3.sign(core_function_call_hash)
    user4_sig = signer4.sign(core_function_call_hash)
    admin1_sig = signer1.sign(core_function_call_hash)

    await assert_revert(
        signer1.send_transaction(
            admin1,
            validator_router.contract_address,
            "call_core_function",
            [
                1,
                1,
                current_nonce,
                get_selector_from_name("set_asset_value"),
                1,
                80,
                2,
                user3_sig[0],
                user3_sig[1],
                admin1_sig[0],
                admin1_sig[1],
                2,
                signer3.public_key,
                signer1.public_key,
            ],
        ),
        reverted_with="SigRequirementsManager: Insufficient no. of valid signatures"
    )


@pytest.mark.asyncio
async def test_with_deregistered_func(adminAuth_factory):

    (
        admin1,
        admin2,
        user3,
        user4,
        registry,
        test_asset,
        validator_router,
        sig_req_manager,
        pubkey_whitelister,
    ) = adminAuth_factory

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "set_sig_requirement",
        [1, 1, get_selector_from_name("set_asset_value"), 2],
    )

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

    await signer1.send_transaction(
        admin1,
        sig_req_manager.contract_address,
        "deregister_func",
        [1, 1, get_selector_from_name("set_asset_value")],
    )

    current_nonce = await validator_router.get_nonce().call()
    current_nonce = current_nonce.result.current_nonce

    core_function_call_hash = compute_hash_on_elements(
        [
            1,
            1,
            current_nonce,
            get_selector_from_name("set_asset_value"),
            compute_hash_on_elements([80]),
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
                1,
                1,
                current_nonce,
                get_selector_from_name("set_asset_value"),
                1,
                80,
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
        reverted_with="SigRequirementsManager: Function not registered"
    )
