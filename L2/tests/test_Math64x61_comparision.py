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
   
   # When difference between x and y is less than given precision(6)
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 1

   # When difference between x and y is more than given precision(6)
   x = to64x61(0.5578945678393322)
   y = to64x61(0.555555555555553)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 0

   # When difference between x and y is more than given precision(18)
   res = await test.math64x61_is_le(x,y,18).call()
   assert res.result.res == 0

@pytest.mark.asyncio
async def test_math64x61_assert_le(adminAuth_factory):
   test = adminAuth_factory

   # When difference between x and y is less than given precision(6)
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   await test.math64x61_assert_le(x,y,6).call()

   # When difference between x and y is more than given precision(6)
   x = to64x61(0.5578945678393322)
   y = to64x61(0.5555555555555531)
   await assert_revert(
        test.math64x61_assert_le(x,y,6).call(),
        "Math64x61_assert_le failed"
   )

   # When difference between x and y is more than given precision(18)
   await assert_revert(
        test.math64x61_assert_le(x,y,18).call(),
        "Math64x61_assert_le failed"
    )