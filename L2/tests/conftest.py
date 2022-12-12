import pytest
from cachetools import LRUCache
from starkware.starknet.testing.starknet import Starknet
from helpers import ContractsHolder, StarknetService, OptimizedStarknetState


@pytest.fixture(scope='session')
def compilation_cache() -> LRUCache:
    return LRUCache(1_000)


@pytest.fixture(scope='session')
def contracts_holder() -> ContractsHolder:
    return ContractsHolder()


@pytest.fixture(scope='module')
async def starknet_service(contracts_holder, compilation_cache) -> StarknetService:
    optimized_starknet_state = await OptimizedStarknetState.empty()
    starknet = Starknet(optimized_starknet_state)
    return StarknetService(starknet, contracts_holder, compilation_cache)