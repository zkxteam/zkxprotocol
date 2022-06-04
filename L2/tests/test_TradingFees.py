# import pytest
# import asyncio
# from starkware.starknet.testing.starknet import Starknet
# from starkware.starkware_utils.error_handling import StarkException
# from starkware.starknet.definitions.error_codes import StarknetErrorCode
# from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

# signer1 = Signer(123456789987654321)
# signer2 = Signer(123456789987654322)
# signer3 = Signer(123456789987654323)

# long_trading_fees = 12
# short_trading_fees = 8


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

#     fees = await starknet.deploy(
#         "contracts/TradingFees.cairo",
#         constructor_calldata=[
#             long_trading_fees,
#             short_trading_fees,
#             adminAuth.contract_address,
#             0, 0, 1,
#             100, 100, 3,
#             500, 500, 4,
#             1, 0, 0,
#             1, 1, 0,
#             1, 1, 1
#         ]
#     )

#     await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])

#     return adminAuth, fees, admin1, admin2, user1


# @pytest.mark.asyncio
# async def test_get_admin_mapping(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, user1 = adminAuth_factory

#     execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 2).call()
#     assert execution_info.result.allowed == 1

#     execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 2).call()
#     assert execution_info1.result.allowed == 0


# @pytest.mark.asyncio
# async def test_modify_tier_by_admin(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, user1 = adminAuth_factory

#     await signer1.send_transaction(admin1, fees.contract_address, 'update_tier_criteria', [1, 10, 10, 2])

#     execution_info = await fees.get_tier_criteria(1).call()
#     result = execution_info.result.tier_criteria_curr

#     assert result.min_balance == 10
#     assert result.min_trading_vol == 10
#     assert result.discount == 2

#     await signer1.send_transaction(admin1, fees.contract_address, 'update_tier_criteria', [2, 110, 110, 3])

#     execution_info = await fees.get_tier_criteria(2).call()
#     result = execution_info.result.tier_criteria_curr

#     assert result.min_balance == 110
#     assert result.min_trading_vol == 110
#     assert result.discount == 3

#     await signer1.send_transaction(admin1, fees.contract_address, 'update_tier_criteria', [3, 600, 600, 6])

#     execution_info = await fees.get_tier_criteria(3).call()
#     result = execution_info.result.tier_criteria_curr

#     assert result.min_balance == 600
#     assert result.min_trading_vol == 600
#     assert result.discount == 6


# @pytest.mark.asyncio
# async def test_modify_tier_by_user(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, user1 = adminAuth_factory

#     assert_revert(lambda: signer3.send_transaction(
#         user1, fees.contract_address, 'update_tier_criteria', [1, 10, 10, 2]))

#     assert_revert(lambda: signer3.send_transaction(
#         user1, fees.contract_address, 'update_tier_criteria', [2, 110, 110, 3]))

#     assert_revert(lambda: signer3.send_transaction(
#         user1, fees.contract_address, 'update_tier_criteria', [3, 600, 600, 5]))


# @pytest.mark.asyncio
# async def test_modify_base_fees(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, user1 = adminAuth_factory

#     await signer1.send_transaction(admin1, fees.contract_address, 'update_fees', [13, 10])

#     execution_info = await fees.get_fees().call()
#     result = execution_info.result

#     assert result.long_fees == 13
#     assert result.short_fees == 10


# @pytest.mark.asyncio
# async def test_modify_base_fees_by_user(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, user1 = adminAuth_factory

#     assert_revert(lambda: signer3.send_transaction(
#         user1, fees.contract_address, 'update_fees', [13, 10]))


# @pytest.mark.asyncio
# async def test_modify_trade_access(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, user1 = adminAuth_factory

#     await signer1.send_transaction(admin1, fees.contract_address, 'update_trade_access', [1, 1, 1, 1])

#     execution_info = await fees.get_trade_access(1).call()
#     result = execution_info.result.trade_access_curr

#     assert result.market == 1
#     assert result.limit == 1
#     assert result.stop == 1

#     await signer1.send_transaction(admin1, fees.contract_address, 'update_trade_access', [2, 1, 0, 1])

#     execution_info = await fees.get_trade_access(2).call()
#     result = execution_info.result.trade_access_curr

#     assert result.market == 1
#     assert result.limit == 0
#     assert result.stop == 1

#     await signer1.send_transaction(admin1, fees.contract_address, 'update_trade_access', [3, 1, 0, 0])

#     execution_info = await fees.get_trade_access(3).call()
#     result = execution_info.result.trade_access_curr

#     assert result.market == 1
#     assert result.limit == 0
#     assert result.stop == 0


# @pytest.mark.asyncio
# async def test_modify_trade_access_by_user(adminAuth_factory):
#     adminAuth, fees, admin1, admin2, user1 = adminAuth_factory

#     assert_revert(lambda: signer3.send_transaction(
#         user1, fees.contract_address, 'update_trade_access', [1, 1, 1, 1]))

#     assert_revert(lambda: signer3.send_transaction(
#         user1, fees.contract_address, 'update_trade_access', [2, 1, 1, 1]))

#     assert_revert(lambda: signer3.send_transaction(
#         user1, fees.contract_address, 'update_trade_access', [3, 0, 0, 1]))
