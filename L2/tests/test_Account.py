import pytest
import asyncio

from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.compiler.compile import get_selector_from_name
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.testing.contract import StarknetContract
from utils import Signer, str_to_felt

signer1 = Signer(123456789987654321)
asset_ID = str_to_felt('2jfk5jfk6n1jfmvnd')

Wrong_L1_ZKX_Contract_Address = 55
Correct_L1_ZKX_Contract_Address = 0x168De57b85fFfD1b1f760cD845D804c0e611EC69
User_Address = 1


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope="session")
async def session_starknet() -> Starknet:
    return await Starknet.empty()


@pytest.fixture(scope="session")
async def account_contract(
    session_starknet: Starknet
) -> StarknetContract:
    return await session_starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[
            signer1.public_key,
            0
        ]
    )

# @pytest.mark.asyncio
# async def test_deposit_wrong_l1_address(
#     session_starknet: Starknet,
#     account_contract: StarknetContract
# ):
#     with pytest.raises(StarkException, match="assert from_address = L1_CONTRACT_ADDRESS"):
#         await session_starknet.send_message_to_l2(
#             from_address=Wrong_L1_ZKX_Contract_Address,
#             to_address=account_contract.contract_address,
#             selector=get_selector_from_name("deposit"),
#             payload=[User_Address, 1000, asset_ID],
#         )


# @pytest.mark.asyncio
# async def test_deposit_happy_flow(
#     session_starknet: Starknet,
#     account_contract: StarknetContract
# ):
#     await session_starknet.send_message_to_l2(
#         from_address=Correct_L1_ZKX_Contract_Address,
#         to_address=account_contract.contract_address,
#         selector=get_selector_from_name("deposit"),
#         payload=[User_Address, 1000, asset_ID],
#     )
#     execution_info = await account_contract.get_balance(asset_ID).call()
#     assert execution_info.result == (1000,)


# @pytest.mark.asyncio
# async def test_withdraw_amount_bigger_than_balance(
#     account_contract: StarknetContract
# ):
#     with pytest.raises(StarkException, match="assert_nn\(new_balance\)"):
#         await account_contract.withdraw(
#             amount=10000, assetID_ = asset_ID
#         ).invoke(caller_address=Correct_L1_ZKX_Contract_Address)


# @pytest.mark.asyncio
# async def test_withdraw_happy_flow(
#     session_starknet: Starknet,
#     account_contract: StarknetContract
# ):
#     await session_starknet.send_message_to_l2(
#         from_address=Correct_L1_ZKX_Contract_Address,
#         to_address=account_contract.contract_address,
#         selector=get_selector_from_name("deposit"),
#         payload=[User_Address, 1000, asset_ID],
#     )
#     execution_info = await account_contract.get_balance(asset_ID).call()
#     assert execution_info.result == (2000,)
#     await account_contract.withdraw(
#         amount=100, assetID_ = asset_ID
#     ).invoke(caller_address=Correct_L1_ZKX_Contract_Address)
#     execution_info = await account_contract.get_balance(asset_ID).call()
#     assert execution_info.result == (1900,)
   