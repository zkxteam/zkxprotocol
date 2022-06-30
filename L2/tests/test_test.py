from copyreg import constructor
import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61
admin1_signer = Signer(123456789987654321)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin1_signer.public_key, 0, 1, 0]
    )

    test = await starknet.deploy(
        "contracts/Test.cairo",
        constructor_calldata=[]
    )

    return starknet, admin1, test


@pytest.mark.asyncio
async def test_timestamp(adminAuth_factory):
    starknet, admin1, test = adminAuth_factory

    timestamp = int(time.time())

    starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet.state.state.block_info.gas_price,
        sequencer_address=starknet.state.state.block_info.sequencer_address
    )

    curr_time = await test.return_timestamp().call()
    print(curr_time.result.res)

    new_timestamp = int(time.time()) + 28800

    starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=new_timestamp, gas_price=starknet.state.state.block_info.gas_price,
        sequencer_address=starknet.state.state.block_info.sequencer_address
    )

    curr_time = await test.return_timestamp().call()
    print(curr_time.result.res)
