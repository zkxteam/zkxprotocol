# import pytest
# import asyncio
# from starkware.starknet.testing.starknet import Starknet
# from starkware.starkware_utils.error_handling import StarkException
# from starkware.starknet.definitions.error_codes import StarknetErrorCode

# from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

# signer1 = Signer(123456789987654321)
# signer2 = Signer(123456789987654322)
# signer3 = Signer(123456789987654323)

# @pytest.fixture(scope='module')
# def event_loop():
#     return asyncio.new_event_loop()

# @pytest.fixture(scope='module')
# async def adminAuth_factory():
#     starknet = await Starknet.empty()
#     admin1 = await starknet.deploy(
#         "contracts/Account.cairo",
#         constructor_calldata=[signer1.public_key, 0]
#     )

#     admin2 = await starknet.deploy(
#         "contracts/Account.cairo",
#         constructor_calldata=[signer2.public_key, 0]
#     )

#     user1 = await starknet.deploy(
#         "contracts/Account.cairo",
#         constructor_calldata=[signer3.public_key, 0]
#     )

#     adminAuth = await starknet.deploy(
#         "contracts/AdminAuth.cairo",
#         constructor_calldata=[
#             admin1.contract_address,
#             admin2.contract_address
#         ]
#     )

#     registry = await starknet.deploy(
#         "contracts/AuthorizedRegistry.cairo",
#         constructor_calldata=[
#             adminAuth.contract_address
#         ]
#     )

#     await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])

#     return adminAuth, registry, admin1, admin2, user1

# @pytest.mark.asyncio
# async def test_get_admin_mapping(adminAuth_factory):
#     adminAuth, _, admin1, admin2, user1 = adminAuth_factory

#     execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 3).call()
#     assert execution_info.result.allowed == 1

#     execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 3).call()
#     assert execution_info1.result.allowed == 0

# @pytest.mark.asyncio
# async def test_modify_registry_by_admin(adminAuth_factory):
#     adminAuth, registry, admin1, admin2, user1 = adminAuth_factory

#     await signer1.send_transaction(admin1, registry.contract_address, 'update_registry', [1, 1, 1])

#     execution_info = await registry.get_registry_value(1, 1).call()
#     result = execution_info.result.allowed

#     assert result == 1

# @pytest.mark.asyncio
# async def test_modify_registry_by_unauthorized(adminAuth_factory):
#     adminAuth, registry, admin1, admin2, user1 = adminAuth_factory

#     assert_revert(lambda: signer3.send_transaction(user1, registry.contract_address, 'update_registry', [1, 1, 1]))
#     assert_revert(lambda: signer3.send_transaction(user1, registry.contract_address, 'update_registry', [1, 1, 0]))
#     assert_revert(lambda: signer3.send_transaction(user1, registry.contract_address, 'update_registry', [2, 1, 1]))