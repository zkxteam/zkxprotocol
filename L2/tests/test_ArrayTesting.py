# import pytest
# import asyncio
# from starkware.starknet.testing.starknet import Starknet
# from starkware.starkware_utils.error_handling import StarkException
# from starkware.starknet.definitions.error_codes import StarknetErrorCode

# from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

# signer1 = Signer(123456789987654321)


# @pytest.fixture(scope='module')
# def event_loop():
#     return asyncio.new_event_loop()


# @pytest.fixture(scope='module')
# async def contract_factory():
#     starknet = await Starknet.empty()
#     admin1 = await starknet.deploy(
#         "contracts/Account.cairo",
#         constructor_calldata=[signer1.public_key, 0]
#     )

#     arrayTesting = await starknet.deploy(
#         "contracts/ArrayTesting.cairo",
#         constructor_calldata=[]
#     )

#     return arrayTesting, admin1


# @pytest.mark.asyncio
# async def create_positions(contract, account):
#     for i in range(5):
#         await signer1.send_transaction(account, contract.contract_address, 'add_position', [i+1, (i+1)*10, (i+1)*100])


# @pytest.mark.asyncio
# async def test_get_admin_mapping(contract_factory):
#     arrayTesting, admin1 = contract_factory

#     await create_positions(arrayTesting, admin1)

#     # await signer1.send_transaction(admin1, arrayTesting.contract_address, 'add_position', [ 1, 261, 361])

#     for i in range(1, 6):
#         position = await arrayTesting.get_position(i).call()
#         print("Index ", i, ": ", position.result.res)

#         position_array = await arrayTesting.get_position_array(i-1).call()
#         print("Index ", i, ": ", position_array.result.res)

#         assert position.result.res == position_array.result.res

#     # Removing Assets
#     await signer1.send_transaction(admin1, arrayTesting.contract_address, 'remove_from_array', [0])

#     position_last = await arrayTesting.get_position(5).call()
#     print("After deletion: ", position_last.result.res)

#     position_array = await arrayTesting.get_position_array(0).call()
#     print(position_array.result.res)

#     assert position_last.result.res == position_array.result.res

#     array = await arrayTesting.return_array().call()
#     print(array.result)
