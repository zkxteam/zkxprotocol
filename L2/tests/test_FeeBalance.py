import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, str_to_felt

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)
signer4 = Signer(123456789987654324)

asset_ID = str_to_felt("c83jv93i4hksdk")

L1_dummy_address = 0x01234567899876543210
L1_ZKX_dummy_address = 0x98765432100123456789


@pytest.fixture
def global_var():
    pytest.user1 = None
    pytest.user2 = None


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def feeBalance_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, L1_dummy_address, 0, 1, L1_ZKX_dummy_address]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, L1_dummy_address, 0, 1, L1_ZKX_dummy_address]
    )

    pytest.user1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer3.public_key, L1_dummy_address, 0, 1, L1_ZKX_dummy_address]
    )

    pytest.user2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer4.public_key, L1_dummy_address, 0, 1, L1_ZKX_dummy_address]
    )

    adminAuth = await starknet.deploy(
        "contracts/AdminAuth.cairo",
        constructor_calldata=[
            admin1.contract_address,
            admin2.contract_address
        ]
    )

    registry = await starknet.deploy(
        "contracts/AuthorizedRegistry.cairo",
        constructor_calldata=[
            adminAuth.contract_address
        ]
    )

    feeBalance = await starknet.deploy(
        "contracts/FeeBalance.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    callFeeBalance = await starknet.deploy(
        "contracts/CallFeeBalance.cairo",
        constructor_calldata=[feeBalance.contract_address]
    )

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [5, 1, callFeeBalance.contract_address])

    return feeBalance, callFeeBalance, admin1, admin2


@pytest.mark.asyncio
async def test_update_fee_mapping_invalid(feeBalance_factory):
    feeBalance, callFeeBalance, admin1, _ = feeBalance_factory

    assert_revert(lambda: signer3.send_transaction(admin1, feeBalance.contract_address,
                  'update_fee_mapping', [pytest.user1.contract_address, 10]))


@pytest.mark.asyncio
async def test_update_fee_mapping(feeBalance_factory):
    feeBalance, callFeeBalance, admin1, _ = feeBalance_factory

    await signer1.send_transaction(admin1, callFeeBalance.contract_address, 'update', [pytest.user1.contract_address, asset_ID, 10])

    execution_info = await feeBalance.get_total_fee(asset_ID).call()
    assert execution_info.result.fee == 10

    execution_info = await feeBalance.get_user_fee(pytest.user1.contract_address, asset_ID).call()
    assert execution_info.result.fee == 10


@pytest.mark.asyncio
async def test_update_fee_mapping_different_user(feeBalance_factory):
    feeBalance, callFeeBalance, admin1, _ = feeBalance_factory
    await signer1.send_transaction(admin1, callFeeBalance.contract_address, 'update', [pytest.user1.contract_address, asset_ID, 10])

    execution_info = await feeBalance.get_total_fee(asset_ID).call()
    assert execution_info.result.fee == 20

    execution_info = await feeBalance.get_user_fee(pytest.user1.contract_address, asset_ID).call()
    assert execution_info.result.fee == 20

    await signer1.send_transaction(admin1, callFeeBalance.contract_address, 'update', [pytest.user2.contract_address, asset_ID, 10])

    execution_info = await feeBalance.get_total_fee(asset_ID).call()
    assert execution_info.result.fee == 30

    execution_info = await feeBalance.get_user_fee(pytest.user1.contract_address, asset_ID).call()
    assert execution_info.result.fee == 20

    execution_info = await feeBalance.get_user_fee(pytest.user2.contract_address, asset_ID).call()
    assert execution_info.result.fee == 10
