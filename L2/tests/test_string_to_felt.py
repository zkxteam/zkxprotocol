import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, from64x61
from starkware.starknet.compiler.compile import get_selector_from_name

@pytest.mark.asyncio
async def test_str_to_felt():
    asset_felt = str_to_felt("USDC")
    amount = to64x61(0.5555555555555553)
    price = from64x61(2536427310135063347200)
    margin = from64x61(16232806235124623343711705154)
    borrowed = from64x61(1281023894007607296)
    leverage = from64x61(2305843009213693952)
    print("\namount:", amount)
    print("\nasset_felt:", asset_felt)
    print("\n price", price)
    print("\n margin", margin)
    print("\n borrowed", borrowed)
    print("\n leverage", leverage)
    print("\n selector",get_selector_from_name('activate_high_tide'))
