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
   x = to64x61(0.5555555555555554)
   y = to64x61(0.5555555555555553)
   a = await test.math64x61_is_le(x,y,6).call()
   print("is_le result", a.result)