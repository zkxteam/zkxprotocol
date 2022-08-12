import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from helpers import StarknetService, ContractType

signer1 = Signer(123456789987654321)

L1_dummy_address = 0x01234567899876543210

@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def contract_factory(starknet_service: StarknetService):
    
    admin1 = await starknet_service.deploy(ContractType.Account, [
        signer1.public_key,
        L1_dummy_address,
        0,
        1
    ])

    arrayTesting = await starknet_service.deploy(ContractType.ArrayTesting, [])

    return arrayTesting, admin1


@pytest.mark.asyncio
async def create_positions(contract, account):
    for i in range(4000):
        await signer1.send_transaction(account, contract.contract_address, 'add_position', [i+1, (i+1)*10, (i+1)*100, i, i, i, i, i, i, i, i, i, i])


@pytest.mark.asyncio
async def test_get_admin_mapping(contract_factory):
    arrayTesting, admin1 = contract_factory

    await create_positions(arrayTesting, admin1)

    array = await arrayTesting.return_array().call()
    print(len(array.result.array_list))
