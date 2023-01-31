import pytest
import asyncio
from helpers import StarknetService, ContractType
from utils import str_to_felt, to64x61, from64x61

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
   # when difference between x and y is less than given precision
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 1

   # when difference between x and y is more than given precision
   x = to64x61(0.5578945678393322)
   y = to64x61(0.555555555555553)
   res = await test.math64x61_is_le(x,y,6).call()
   assert res.result.res == 0