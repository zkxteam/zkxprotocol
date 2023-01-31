import pytest
import asyncio
from helpers import StarknetService, ContractType
from utils import from64x61, to64x61

@pytest.fixture(scope='module')
def event_loop():
   return asyncio.new_event_loop()

@pytest.fixture(scope='module')
async def math64x61_factory(starknet_service: StarknetService):
   math = await starknet_service.deploy(ContractType.TestMath64x61, [])
   return math

@pytest.mark.asyncio
async def test_approx_1(math64x61_factory):
   math = math64x61_factory

   approx = await math.calc(to64x61(1.222), 0).call()
   assert from64x61(approx.result.res) == 1
   
   approx = await math.calc(to64x61(1.222), 1).call()
   assert from64x61(approx.result.res) == 1.2

   approx = await math.calc(to64x61(1.222), 2).call()
   assert from64x61(approx.result.res) == 1.22

   approx = await math.calc(to64x61(1.222), 3).call()
   assert from64x61(approx.result.res) == 1.222

@pytest.mark.asyncio
async def test_approx_2(math64x61_factory):
   math = math64x61_factory

   approx = await math.calc(to64x61(1.24567), 1).call()
   assert from64x61(approx.result.res) == 1.2

   approx = await math.calc(to64x61(1.24567), 2).call()
   assert from64x61(approx.result.res) == 1.25

   approx = await math.calc(to64x61(1.24567), 3).call()
   assert from64x61(approx.result.res) == 1.246

   approx = await math.calc(to64x61(1.24567), 4).call()
   assert from64x61(approx.result.res) == 1.2457

@pytest.mark.asyncio
async def test_approx_3(math64x61_factory):
   math = math64x61_factory

   approx = await math.calc(to64x61(100), 1).call()
   assert from64x61(approx.result.res) == 100

   approx = await math.calc(to64x61(100), 2).call()
   assert from64x61(approx.result.res) == 100

   approx = await math.calc(to64x61(100), 3).call()
   assert from64x61(approx.result.res) == 100

@pytest.mark.asyncio
async def test_approx_4(math64x61_factory):
   math = math64x61_factory

   approx = await math.calc(to64x61(0.001), 3).call()
   assert pytest.approx(from64x61(approx.result.res), abs=1e-3) == 0.001

   approx = await math.calc(to64x61(0.156), 1).call()
   assert from64x61(approx.result.res) == 0.2

   approx = await math.calc(to64x61(0.156), 2).call()
   assert from64x61(approx.result.res) == 0.16

   approx = await math.calc(to64x61(0.156), 3).call()
   assert from64x61(approx.result.res) == 0.156

   approx = await math.calc(to64x61(0.000000001), 2).call()
   assert from64x61(approx.result.res) == 0

@pytest.mark.asyncio
async def test_approx_5(math64x61_factory):
   math = math64x61_factory

   approx = await math.calc(to64x61(10000000000000.98123456789), 6).call()
   assert from64x61(approx.result.res) == 10000000000000.981235

   approx = await math.calc(to64x61(10000000000000.98123456789), 3).call()
   assert from64x61(approx.result.res) == 10000000000000.981

   approx = await math.calc(to64x61(10000000000000.98123456789), 2).call()
   assert from64x61(approx.result.res) == 10000000000000.98

   approx = await math.calc(to64x61(10000000000000.98123456789), 1).call()
   assert from64x61(approx.result.res) == 10000000000001

@pytest.mark.asyncio
async def test_approx_6(math64x61_factory):
   math = math64x61_factory

   approx = await math.calc(to64x61(1467.0000001), 3).call()
   assert from64x61(approx.result.res) == 1467

   approx = await math.calc(to64x61(756.99999999), 4).call()
   assert from64x61(approx.result.res) == 757

   approx = await math.calc(to64x61(10000000000000.123456789123456789), 18).call()
   assert from64x61(approx.result.res) == 10000000000000.123456789123456789

   approx = await math.calc(to64x61(10000000000000.123456789123456789), 16).call()
   assert from64x61(approx.result.res) == 10000000000000.1234567891234568

   approx = await math.calc(to64x61(10000000000000.123456789123456789), 1).call()
   assert from64x61(approx.result.res) == 10000000000000.1