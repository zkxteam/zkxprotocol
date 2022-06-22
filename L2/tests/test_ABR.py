import pytest
import asyncio
import ABR_data
import calculate_abr
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, from64x61, to64x61

admin1_signer = Signer(123456789987654321)


def convertTo64x61(nums):

    for i in range(len(nums)):
        nums[i] = to64x61(nums[i])

    return nums


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def abr_factory():
    starknet = await Starknet.empty()

    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin1_signer.public_key, 0, 1]
    )

    abr = await starknet.deploy(
        "contracts/ABR.cairo",
        constructor_calldata=[
        ]
    )

    return abr, admin1


@pytest.mark.asyncio
async def test_should_calculate_correct_abr_ratio_for_BTC(abr_factory):
    abr, admin1 = abr_factory

    arguments = [
        480] + convertTo64x61(ABR_data.btc_perp_spot) + [480]+convertTo64x61(ABR_data.btc_perp)

    abr_python = calculate_abr.calculate_abr(
        ABR_data.btc_perp_spot, ABR_data.btc_perp)
    print("python rate", abr_python)

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    print("cairo rate", from64x61(abr_cairo.result.response[0]))

    assert abr_python == pytest.approx(
        from64x61(abr_cairo.result.response[0]), abs=1e-6)


@pytest.mark.asyncio
async def test_should_calculate_correct_abr_ratio_for_ETH(abr_factory):
    abr, admin1 = abr_factory

    arguments = [
        480] + convertTo64x61(ABR_data.eth_perp_spot) + [480]+convertTo64x61(ABR_data.eth_perp)

    abr_python = calculate_abr.calculate_abr(
        ABR_data.eth_perp_spot, ABR_data.eth_perp)
    print("python rate", abr_python)

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    print("cairo rate", from64x61(abr_cairo.result.response[0]))

    assert abr_python == pytest.approx(
        from64x61(abr_cairo.result.response[0]), abs=1e-6)