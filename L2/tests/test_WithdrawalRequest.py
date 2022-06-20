import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0, 1]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0, 1]
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
            adminAuth.contract_address
        ]
    )

    withdrawal_request = await starknet.deploy(
        "contracts/WithdrawalRequest.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    return adminAuth, withdrawal_request, admin1, admin2


@pytest.mark.asyncio
async def test_add_to_withdrawal_request(adminAuth_factory):
    adminAuth, withdrawal_request, admin1, admin2 = adminAuth_factory

    l2_account_address_1 = 0x1234
    collateral_id_1 = str_to_felt("fghj3am52qpzsib")
    amount_1 = to64x61(5000)
    status_1 = 0

    l2_account_address_2 = 0x5678
    collateral_id_2 = str_to_felt("yjk45lvmasopq")
    amount_2 = to64x61(10000)
    status_2 = 0

    await signer1.send_transaction(admin1, withdrawal_request.contract_address, 'add_withdrawal_request', [l2_account_address_1, collateral_id_1, amount_1, status_1])
    await signer1.send_transaction(admin1, withdrawal_request.contract_address, 'add_withdrawal_request', [l2_account_address_2, collateral_id_2, amount_2, status_2])

    fetched_withdrawal_request = await withdrawal_request.get_withdrawal_request_data().call()
    print(fetched_withdrawal_request.result.withdrawal_request_list)

    res1 = list(fetched_withdrawal_request.result.withdrawal_request_list[0])

    assert res1 == [
        l2_account_address_1,
        collateral_id_1,
        amount_1,
        status_1
    ]
    
    res2 = list(fetched_withdrawal_request.result.withdrawal_request_list[1])

    assert res2 == [
        l2_account_address_2,
        collateral_id_2,
        amount_2,
        status_2
    ]