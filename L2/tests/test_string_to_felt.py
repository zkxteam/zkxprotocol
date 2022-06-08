import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, from64x61


@pytest.mark.asyncio
async def test_str_to_felt():
    asset_felt = str_to_felt("ETH")
    asset_value = to64x61(2)
    res = from64x61(2236667718937283072)
    res1 = from64x61(2236667718937280000)
    print("\nasset_felt:", asset_felt)
    print("asset_value", asset_value)
    print("value", res)
    print("value", res1)
