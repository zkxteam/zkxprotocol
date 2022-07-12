import pytest
import asyncio
import ABR_data
import time
import calculate_abr
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.business_logic.state.state import BlockInfo
from utils import Signer, from64x61, to64x61, assert_revert, convertTo64x61
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address, L1_ZKX_dummy_address


admin1_signer = Signer(123456789987654321)
admin2_signer = Signer(123456789987654322)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def abr_factory(starknet_service: StarknetService):

    # Deploy admins
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1, L1_ZKX_dummy_address)
    admin1 = await account_factory.deploy_account(admin1_signer.public_key)
    admin2 = await account_factory.deploy_account(admin2_signer.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    abr = await starknet_service.deploy(ContractType.ABR, [registry.contract_address, 1])
    
    await admin1_signer.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await admin1_signer.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [17, 1, abr.contract_address])

    # Deploy RelayABR contract
    relay_abr = await starknet_service.deploy(ContractType.RelayABR, [
        registry.contract_address, 
        1,
        17  # abr index
    ])

    timestamp = int(time.time())

    starknet_service.starknet.state.state.block_info = BlockInfo(
        block_number=1, 
        block_timestamp=timestamp, 
        gas_price=starknet_service.starknet.state.state.block_info.gas_price,
        sequencer_address=starknet_service.starknet.state.state.block_info.sequencer_address
    )

    btc_perp_spot_64x61 = convertTo64x61(ABR_data.btc_perp_spot)
    btc_perp_64x61 = convertTo64x61(ABR_data.btc_perp)

    eth_perp_spot_64x61 = convertTo64x61(ABR_data.eth_perp_spot)
    eth_perp_64x61 = convertTo64x61(ABR_data.eth_perp)

    return starknet_service.starknet, relay_abr, admin1, btc_perp_spot_64x61, btc_perp_64x61, eth_perp_spot_64x61, eth_perp_64x61


@pytest.mark.asyncio
async def test_should_revert_if_wrong_number_of_arguments_passed_for_BTC(abr_factory):
    _, abr, admin1, btc_spot, btc_perp, _, _ = abr_factory

    arguments = [1282193, 479] + btc_spot + [480]+btc_perp

    await assert_revert(
        admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments))


@pytest.mark.asyncio
async def test_should_calculate_correct_abr_ratio_for_BTC(abr_factory):
    _, abr, admin1, btc_spot, btc_perp, _, _ = abr_factory

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
    _, abr, admin1, btc_spot, btc_perp, _, _ = abr_factory

    arguments = [1282193, 480] + btc_spot + [480]+btc_perp

    await assert_revert(
        admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments))


@pytest.mark.asyncio
async def test_should_pass_if_called_after_8_hours(abr_factory):
    starknet, abr, admin1, btc_spot, btc_perp, _, _ = abr_factory

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
async def test_should_calculate_correct_abr_ratio_for_ETH(abr_factory):
    _, abr, admin1, _, _, eth_spot, eth_perp = abr_factory

    arguments = [1282198, 480] + eth_spot + [480] + eth_perp

    abr_python = calculate_abr.calculate_abr(
        ABR_data.eth_perp_spot, ABR_data.eth_perp, 0.0000125, 2.0)
    print("python rate", abr_python)

    abr_cairo = await admin1_signer.send_transaction(admin1, abr.contract_address, 'calculate_abr', arguments)
    print("cairo rate", from64x61(abr_cairo.result.response[0]))

    abr_value = await abr.get_abr_value(92391239).call()
    print("abr value of the market is:",
          from64x61(abr_value.result.abr))
    print("The last price is:",
          from64x61(abr_value.result.price))
    print("The last timestamp is:",
          from64x61(abr_value.result.timestamp))

    assert abr_python == pytest.approx(
        from64x61(abr_cairo.result.response[0]), abs=1e-6)
