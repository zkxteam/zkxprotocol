import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def test_factory():
    starknet = await Starknet.empty()
    test_contract = await starknet.deploy(
        "contracts/Test.cairo",
        constructor_calldata=[]
    )

    return test_contract

@pytest.mark.asyncio
async def test(test_factory):
    test_contract = test_factory

    execution_info = await test_contract.test().call()
    # assert execution_info.result.allowed == 1