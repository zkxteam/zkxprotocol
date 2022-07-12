import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, from64x61


@pytest.mark.asyncio
async def test_str_to_felt():
    asset_felt = str_to_felt("USDC")
    amount = to64x61(10000000)
    price = from64x61(1844674407370955161600)
    margin = from64x61(11531451713787407040000)
    borrowed = from64x61(8718657198078)
    leverage = from64x61(2305843009213693952)
    print("\namount:", amount)
    print("\nasset_felt:", asset_felt)
    print("\n price", price)
    print("\n margin", margin)
    print("\n borrowed", borrowed)
    print("\n leverage", leverage)
