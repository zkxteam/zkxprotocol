import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
import math

SCALE = 2**61
PRIME = 3618502788666131213697322783095070105623107215331596699973092056135872020481
PRIME_HALF = PRIME/2
PI = 7244019458077122842

def from64x61(num):
    res = num
    if num > PRIME_HALF:
        res = res - PRIME
    return res / SCALE

def to64x61(num):
    res = num * SCALE
    if res > 2**125 or res <= -2*125:
        raise Exception("Number is out of valid range")
    return math.trunc(res)

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    test = await starknet.deploy(
        "contracts/Math_64x61.cairo",
        constructor_calldata=[]
    )

    return test


@pytest.mark.asyncio
async def test_revert(adminAuth_factory):
    test = adminAuth_factory

    x = await test.div_fp(to64x61(4), to64x61(2)).call()
    print(from64x61(x.result.res))

    y = await test.check(to64x61(10000), to64x61(9999)).call()
    print(y.result.res)
