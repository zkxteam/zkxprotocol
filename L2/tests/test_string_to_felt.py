import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, from64x61


@pytest.mark.asyncio
async def test_str_to_felt():
    asset_felt = str_to_felt("ETH")
    asset_value = to64x61(.000194)
    res = from64x61(209078143475155881079725)
    res1 = from64x61(230584300921369395200000 - 21506157446213514129600)
    print("\nasset_felt:", asset_felt)
    print("asset_value", asset_value)
    print("value", res)
    print("value", res1)
