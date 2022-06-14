import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, from64x61


@pytest.mark.asyncio
async def test_str_to_felt():
    asset_felt = str_to_felt("ETH")
    price = from64x61(5858937464320249856000)
    margin = from64x61(5858937464320249823232)
    borrowed = from64x61(5858937464320249856000)
    leverage = from64x61(2305843009213693952)
    print("\nasset_felt:", asset_felt)
    print("\n price", price)
    print("\n margin", margin)
    print("\n borrowed", borrowed)
    print("\n leverage", leverage)
