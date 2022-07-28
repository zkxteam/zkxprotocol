import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, L1_address_dummy

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)
signer4 = Signer(123456789987654323)
signer5 = Signer(123456789987654324)


@pytest.fixture
def global_var():
    pytest.user1 = None
    pytest.user2 = None
    pytest.user3 = None


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, L1_address_dummy, 0, 1, 1]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, L1_address_dummy, 0, 1, 1]
    )

    pytest.user1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer3.public_key, L1_address_dummy, 0, 1, 1]
    )

    pytest.user2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer4.public_key, L1_address_dummy, 0, 1, 1]
    )

    pytest.user3 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer5.public_key, L1_address_dummy, 0, 1, 1]
    )

    adminAuth = await starknet.deploy(
        "contracts/AdminAuth.cairo",
        constructor_calldata=[
            admin1.contract_address,
            admin2.contract_address
        ]
    )

    return adminAuth, admin1, admin2


@pytest.mark.asyncio
async def test_get_admin_mapping(adminAuth_factory):
    adminAuth, admin1, admin2 = adminAuth_factory

    execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 0).call()
    assert execution_info.result.allowed == 1

    execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 0).call()
    assert execution_info1.result.allowed == 1


@pytest.mark.asyncio
async def test_update_admin_mapping_non_admin(adminAuth_factory):
    adminAuth, admin1, _ = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [pytest.user1.contract_address, 1, 1])

    execution_info = await adminAuth.get_admin_mapping(pytest.user1.contract_address, 1).call()
    assert execution_info.result.allowed == 1


@pytest.mark.asyncio
async def test_update_admin_mapping_one_approval(adminAuth_factory):
    adminAuth, admin1, _ = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [pytest.user2.contract_address, 0, 1])

    execution_info1 = await adminAuth.get_admin_mapping(pytest.user2.contract_address, 0).call()
    assert execution_info1.result.allowed == admin1.contract_address

    assert_revert(lambda: signer4.send_transaction(pytest.user2, adminAuth.contract_address,
                  'update_admin_mapping', [pytest.user2.contract_address, 0, 1]))


@pytest.mark.asyncio
async def test_update_admin_mapping_same_approval(adminAuth_factory):
    adminAuth, admin1, _ = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [pytest.user3.contract_address, 0, 1])

    execution_info1 = await adminAuth.get_admin_mapping(pytest.user2.contract_address, 0).call()
    assert execution_info1.result.allowed == admin1.contract_address

    assert_revert(lambda: signer1.send_transaction(pytest.user2, adminAuth.contract_address,
                  'update_admin_mapping', [pytest.user3.contract_address, 0, 1]))


@pytest.mark.asyncio
async def test_update_admin_mapping_no_permission(adminAuth_factory):
    adminAuth, _, _ = adminAuth_factory

    assert_revert(lambda: signer3.send_transaction(pytest.user1, adminAuth.contract_address,
                  'update_admin_mapping', [pytest.user1.contract_address, 0, 1]))


@pytest.mark.asyncio
async def test_update_admin_mapping_admin(adminAuth_factory):
    adminAuth, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [pytest.user1.contract_address, 0, 1])

    execution_info1 = await adminAuth.get_admin_mapping(pytest.user1.contract_address, 0).call()
    assert execution_info1.result.allowed == admin1.contract_address

    await signer2.send_transaction(admin2, adminAuth.contract_address, 'update_admin_mapping', [pytest.user1.contract_address, 0, 1])

    execution_info2 = await adminAuth.get_admin_mapping(pytest.user1.contract_address, 0).call()
    assert execution_info2.result.allowed == 1


@pytest.mark.asyncio
async def test_update_admin_mapping_revoke(adminAuth_factory):
    adminAuth, admin1, admin2 = adminAuth_factory

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [pytest.user3.contract_address, 1, 1])

    execution_info1 = await adminAuth.get_admin_mapping(pytest.user3.contract_address, 1).call()
    assert execution_info1.result.allowed == 1

    await signer2.send_transaction(admin2, adminAuth.contract_address, 'update_admin_mapping', [pytest.user3.contract_address, 1, 0])

    execution_info2 = await adminAuth.get_admin_mapping(pytest.user3.contract_address, 1).call()
    assert execution_info2.result.allowed == 0
