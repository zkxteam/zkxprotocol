import pytest
import asyncio
import ABR_data
import time
import calculate_abr
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, from64x61, to64x61, assert_revert

admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)
alice_signer = Signer(123456789987654323)


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
        constructor_calldata=[admin1_signer.public_key, 0, 1, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[admin2_signer.public_key, 0, 1, 0]
    )

    alice = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[alice_signer.public_key, 0, 1, 0]
    )

    adminAuth = await starknet.deploy(
        "contracts/AdminAuth.cairo",
        constructor_calldata=[
            admin1.contract_address,
            admin2.contract_address
        ]
    )

    registry = await starknet.deploy(
        "contracts/AuthorizedRegistry.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
        ]
    )

    abr = await starknet.deploy(
        "contracts/ABR.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    timestamp = int(time.time())

    starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet.state.state.block_info.gas_price,
        sequencer_address=starknet.state.state.block_info.sequencer_address
    )

    btc_perp_spot_64x61 = convertTo64x61(ABR_data.btc_perp_spot)
    btc_perp_64x61 = convertTo64x61(ABR_data.btc_perp)

    eth_perp_spot_64x61 = convertTo64x61(ABR_data.eth_perp_spot)
    eth_perp_64x61 = convertTo64x61(ABR_data.eth_perp)

    return starknet, abr, admin1, alice, btc_perp_spot_64x61, btc_perp_64x61, eth_perp_spot_64x61, eth_perp_64x61


@pytest.mark.asyncio
async def test_should_revert_if_wrong_number_of_arguments_passed_for_BTC(abr_factory):
    _, abr, admin1, _, btc_spot, btc_perp, _, _ = abr_factory

    arguments = [1282193, 479] + btc_spot + [480]+btc_perp

    await assert_revert(
        admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments))


@pytest.mark.asyncio
async def test_should_revert_if_non_admin_changed_base_abr(abr_factory):
    _, abr, admin1, alice, btc_spot, btc_perp, _, _ = abr_factory

    new_base_abr = to64x61(0.000025)
    await assert_revert(
        alice_signer.send_transaction(alice, abr.contract_address, 'modify_base_abr', [new_base_abr]))


@pytest.mark.asyncio
async def test_should_calculate_correct_abr_ratio_for_BTC(abr_factory):
    _, abr, admin1, _, btc_spot, btc_perp, _, _ = abr_factory

    arguments = [1282193, 480] + btc_spot + [480]+btc_perp

    abr_python = calculate_abr.calculate_abr(
        ABR_data.btc_perp_spot, ABR_data.btc_perp, 0.0000125, 2.0)
    print("python rate", abr_python)

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    print("cairo rate", from64x61(abr_cairo.result.response[0]))

    abr_value = await abr.get_abr_value(1282193).call()
    print("abr value of the market is:",
          from64x61(abr_value.result.abr))
    print("The last price is:",
          from64x61(abr_value.result.price))
    print("The last timestamp is:",
          from64x61(abr_value.result.timestamp))

    assert abr_python == pytest.approx(
        from64x61(abr_cairo.result.response[0]), abs=1e-6)


@pytest.mark.asyncio
async def test_should_revert_if_called_before_8_hours(abr_factory):
    _, abr, admin1, _, btc_spot, btc_perp, _, _ = abr_factory

    arguments = [1282193, 480] + btc_spot + [480]+btc_perp

    await assert_revert(
        admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments))


@pytest.mark.asyncio
async def test_should_pass_if_called_after_8_hours(abr_factory):
    starknet, abr, admin1, _, btc_spot, btc_perp, _, _ = abr_factory

    timestamp = int(time.time()) + 28810

    starknet.state.state.block_info = BlockInfo(
        block_number=1, block_timestamp=timestamp, gas_price=starknet.state.state.block_info.gas_price,
        sequencer_address=starknet.state.state.block_info.sequencer_address
    )

    arguments = [1282193, 480] + btc_spot + [480]+btc_perp

    abr_python = calculate_abr.calculate_abr(
        ABR_data.btc_perp_spot, ABR_data.btc_perp, 0.0000125, 2.0)
    print("python rate", abr_python)

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    print("cairo rate", from64x61(abr_cairo.result.response[0]))

    abr_value = await abr.get_abr_value(1282193).call()
    print("abr value of the market is:",
          from64x61(abr_value.result.abr))
    print("The last price is:",
          from64x61(abr_value.result.price))
    print("The last timestamp is:",
          from64x61(abr_value.result.timestamp))

    assert abr_python == pytest.approx(
        from64x61(abr_cairo.result.response[0]), abs=1e-6)


@pytest.mark.asyncio
async def test_should_pass_if_admin_changed_base_abr(abr_factory):
    _, abr, admin1, alice, btc_spot, btc_perp, _, _ = abr_factory

    new_base_abr = to64x61(0.000025)
    await admin1_signer.send_transaction(admin1, abr.contract_address, 'modify_base_abr', [new_base_abr])


@pytest.mark.asyncio
async def test_should_calculate_correct_abr_ratio_for_ETH(abr_factory):
    _, abr, admin1, _, _, _, eth_spot, eth_perp = abr_factory

    arguments = [1282198, 480] + eth_spot + [480] + eth_perp

    abr_python = calculate_abr.calculate_abr(
        ABR_data.eth_perp_spot, ABR_data.eth_perp, 0.000025, 2.0)
    print("python rate", abr_python)

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    print("cairo rate", from64x61(abr_cairo.result.response[0]))

    abr_value = await abr.get_abr_value(1282198).call()
    print("abr value of the market is:",
          from64x61(abr_value.result.abr))
    print("The last price is:",
          from64x61(abr_value.result.price))
    print("The last timestamp is:",
          abr_value.result.timestamp)

    assert abr_python == pytest.approx(
        from64x61(abr_cairo.result.response[0]), abs=1e-4)
