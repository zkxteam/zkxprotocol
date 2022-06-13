from copyreg import constructor
from operator import index
from turtle import end_fill
import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, hash_order, from64x61, to64x61, convertList

admin1_signer = Signer(123456789987654321)


def convertTo64x61(nums):

    for i in range(len(nums)):
        nums[i] = to64x61(nums[i])

    return nums


def convertFrom64x61(nums):

    for i in range(len(nums)):
        nums[i] = from64x61(nums[i])

    return nums


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def abr_factory():
    starknet = await Starknet.empty()
    print(to64x61(2))

    abr = await starknet.deploy(
        "contracts/ABR.cairo",
        constructor_calldata=[]
    )

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin1_signer.public_key, 0, 1]
    )

    return abr, admin1


@pytest.mark.asyncio
async def test_should_calculate_correct_abr_ratio(abr_factory):
    abr, admin1 = abr_factory

    mark_prices = convertTo64x61([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    index_prices = convertTo64x61([2, 2, 2, 2, 2, 2, 2, 2, 2, 2])

    arguments = [10]+index_prices+[10]+mark_prices
    print(arguments)

    avg_prices = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    print("result 64", convertFrom64x61(avg_prices.result.response))
    # print("result", (avg_prices.result.response))

    sum = await abr.return_total().call()
    mean64 = await abr.return_mean64().call()

    print("Sum is", from64x61(sum.result.res))
    print("mean in 64x61", from64x61(mean64.result.res))
