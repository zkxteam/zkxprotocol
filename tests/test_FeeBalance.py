import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer = Signer(123456789987654321)
signer1 = Signer(123456789987654322)
signer2 = Signer(123456789987654323)

@pytest.fixture
def global_var():
    pytest.user1 = None

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def feeBalance_factory():
    starknet = await Starknet.empty()
    admin = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer.public_key]
    )

    pytest.user1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key]
    )

    pytest.user2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key]
    )

    feeBalance = await starknet.deploy(
        "contracts/FeeBalance.cairo",
        constructor_calldata=[]
    )

    return feeBalance, admin

@pytest.mark.asyncio
async def test_update_fee_mapping(feeBalance_factory):
    feeBalance, admin = feeBalance_factory

    await signer.send_transaction(admin, feeBalance.contract_address, 'update_fee_mapping', [pytest.user1.contract_address, 10])

    execution_info = await feeBalance.get_total_fee().call()
    assert execution_info.result.fee == 10

    execution_info = await feeBalance.get_user_fee(pytest.user1.contract_address).call()
    assert execution_info.result.fee == 10

@pytest.mark.asyncio
async def test_update_fee_mapping_different_user(feeBalance_factory):
    feeBalance, admin = feeBalance_factory

    await signer.send_transaction(admin, feeBalance.contract_address, 'update_fee_mapping', [pytest.user1.contract_address, 10])

    execution_info = await feeBalance.get_total_fee().call()
    assert execution_info.result.fee == 20

    execution_info = await feeBalance.get_user_fee(pytest.user1.contract_address).call()
    assert execution_info.result.fee == 20

    await signer.send_transaction(admin, feeBalance.contract_address, 'update_fee_mapping', [pytest.user2.contract_address, 10])

    execution_info = await feeBalance.get_total_fee().call()
    assert execution_info.result.fee == 30

    execution_info = await feeBalance.get_user_fee(pytest.user1.contract_address).call()
    assert execution_info.result.fee == 20

    execution_info = await feeBalance.get_user_fee(pytest.user2.contract_address).call()
    assert execution_info.result.fee == 10