import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType

signer1 = Signer(123456789987654321)
signer2= Signer(12345)
L1_dummy_address = 0x01234567899876543210

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def contract_factory(starknet_service: StarknetService):
    
    admin1 = await starknet_service.deploy(ContractType.Account, [
        signer1.public_key,
    ])

    admin2 = await starknet_service.deploy(ContractType.Account, [
        signer2.public_key,
    ])

    arrayTesting = await starknet_service.deploy(ContractType.ArrayTesting, [])

    return arrayTesting, admin1, admin2


@pytest.mark.asyncio
async def create_positions(contract, account):
    for i in range(5):
        await signer1.send_transaction(account, contract.contract_address, 'add_position', [i+1, (i+1)*10, (i+1)*100])


@pytest.mark.asyncio
async def test_get_admin_mapping(contract_factory):
    arrayTesting, admin1, admin2 = contract_factory

    await create_positions(arrayTesting, admin1)

    for i in range(1, 6):
        position = await arrayTesting.get_position(i).call()
        print("Index ", i, ": ", position.result.res)

        position_array = await arrayTesting.get_position_array(i-1).call()
        print("Index ", i, ": ", position_array.result.res)

        assert position.result.res == position_array.result.res

    # Removing Assets
    await signer1.send_transaction(admin1, arrayTesting.contract_address, 'remove_from_array', [0])

    position_last = await arrayTesting.get_position(5).call()
    print("After deletion: ", position_last.result.res)

    position_array = await arrayTesting.get_position_array(0).call()
    print(position_array.result.res)

    assert position_last.result.res == position_array.result.res

    array = await arrayTesting.return_array().call()
    print(array.result)