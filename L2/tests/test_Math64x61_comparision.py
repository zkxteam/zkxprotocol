import pytest
import asyncio
from helpers import StarknetService, ContractType
from utils import str_to_felt, to64x61, from64x61, assert_revert

@pytest.fixture(scope='module')
def event_loop():
   return asyncio.new_event_loop()

@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
   test = await starknet_service.deploy(ContractType.TestMath64x61, [])
   return test

@pytest.mark.asyncio
async def test_math64x61_is_le(adminAuth_factory):
   test = adminAuth_factory

   # Case 1: When both are equal
   # x == y, (x-y) <= 10^-16
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_le(x,y,16).call()
   assert res.result.res == 1

   # Case 2: When both are positive
   # x > y, (x-y) <= 10^-6
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 1

   # x < y, (x-y) <= 10^-6
   x = to64x61(0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 1

   # x > y, (x-y) > 10^-18
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   res = await test.math64x61_is_le(x,y,18).call()
   assert res.result.res == 0

   # x < y, (x-y) <= 10^-18
   x = to64x61(0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_le(x,y,18).call()
   assert res.result.res == 1

   # Case 3: When one is negative
   # x > y, (x-y) > 10^-6
   x = to64x61(0.5555555555555554)
   y = to64x61(-0.5555555555555553)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 0

   # x < y, (x-y) <= 10^-6
   x = to64x61(-0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 1

   # x > y, (x-y) > 10^-18
   x = to64x61(0.5555555555555554)
   y = to64x61(-0.5555555555555553)
   res = await test.math64x61_is_le(x,y,18).call()
   assert res.result.res == 0

   # x < y, (x-y) <= 10^-18
   x = to64x61(-0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_le(x,y,18).call()
   assert res.result.res == 1

   # Case 4: When both are negative 
   # x > y, (x-y) > 10^-4
   x = to64x61(-1)
   y = to64x61(-1.001)
   res = await test.math64x61_is_le(x,y,4).call()
   assert res.result.res == 0

   # x < y, (x-y) <= 10^-4
   x = to64x61(-1.001)
   y = to64x61(-1)
   res = await test.math64x61_is_le(x,y,4).call()
   assert res.result.res == 1

   # x > y, (x-y) <= 10^-2
   x = to64x61(-1)
   y = to64x61(-1.001)
   res = await test.math64x61_is_le(x,y,2).call()
   assert res.result.res == 1

   # x < y, (x-y) <= 10^-2
   x = to64x61(-1.001)
   y = to64x61(-1)
   res = await test.math64x61_is_le(x,y,2).call()
   assert res.result.res == 1

@pytest.mark.asyncio
async def test_math64x61_assert_le(adminAuth_factory):
   test = adminAuth_factory

   # When difference between x and y is 0
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555554)
   await test.math64x61_assert_le(x,y,6).call()

   # When difference between x and y is less than given precision(6)
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   await test.math64x61_assert_le(x,y,6).call()

   # When difference between x and y is more than given precision(6)
   x = to64x61(0.5578945678393322)
   y = to64x61(-0.5555555555555531)
   await assert_revert(
        test.math64x61_assert_le(x,y,6).call(),
        "Math64x61_assert_le failed"
   )

   # When difference between x and y is more than given precision(18)
   x = to64x61(-0.5555555555555531)
   y = to64x61(-0.5578945678393322)
   await assert_revert(
        test.math64x61_assert_le(x,y,18).call(),
        "Math64x61_assert_le failed"
    )

@pytest.mark.asyncio
async def test_math64x61_is_equal(adminAuth_factory):
   test = adminAuth_factory

   # Case 1: When both are equal
   # x == y, |x-y| <= 10^-16
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_equal(x,y,16).call()
   assert res.result.res == 1

   # Case 2: When both are positive
   # x > y, |x-y| <= 10^-6
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   res = await test.math64x61_is_equal(x,y,6).call()
   assert res.result.res == 1

   # x < y, |x-y| <= 10^-6
   x = to64x61(0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_equal(x,y,6).call()
   assert res.result.res == 1

   # x > y, |x-y| > 10^-18
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   res = await test.math64x61_is_equal(x,y,18).call()
   assert res.result.res == 0

   # x < y, |x-y| > 10^-18
   x = to64x61(0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_equal(x,y,18).call()
   assert res.result.res == 0

   # Case 3: When one is negative
   # x > y, |x-y| > 10^-6
   x = to64x61(0.5555555555555554)
   y = to64x61(-0.5555555555555553)
   res = await test.math64x61_is_equal(x,y,6).call()
   assert res.result.res == 0

   # x < y, |x-y| > 10^-6
   x = to64x61(-0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_equal(x,y,6).call()
   assert res.result.res == 0

   # x > y, |x-y| > 10^-18
   x = to64x61(0.5555555555555554)
   y = to64x61(-0.5555555555555553)
   res = await test.math64x61_is_equal(x,y,18).call()
   assert res.result.res == 0

   # x < y, |x-y| > 10^-18
   x = to64x61(-0.5555555555555553)
   y = to64x61(0.5555555555555554)
   res = await test.math64x61_is_equal(x,y,18).call()
   assert res.result.res == 0

   # Case 4: When both are negative 
   # x > y, |x-y| > 10^-4
   x = to64x61(-1)
   y = to64x61(-1.001)
   res = await test.math64x61_is_equal(x,y,4).call()
   assert res.result.res == 0

   # x < y, |x-y| > 10^-4
   x = to64x61(-1.001)
   y = to64x61(-1)
   res = await test.math64x61_is_equal(x,y,4).call()
   assert res.result.res == 0

   # x > y, |x-y| < 10^-2
   x = to64x61(-1)
   y = to64x61(-1.001)
   res = await test.math64x61_is_equal(x,y,2).call()
   assert res.result.res == 1

   # x < y, |x-y| > 10^-2
   x = to64x61(-1.001)
   y = to64x61(-1)
   res = await test.math64x61_is_equal(x,y,2).call()
   assert res.result.res == 1