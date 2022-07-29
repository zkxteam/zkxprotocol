import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import DeclaredClass
from starkware.starknet.core.os.class_hash import compute_class_hash
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.testing.contract import StarknetContract

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
        constructor_calldata=[signer1.public_key, 123, 0, 1, 1]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 123, 0, 1, 1]
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

    deposit_data_manager = await starknet.deploy(
        "contracts/DepositDataManager.cairo",
        constructor_calldata=[
            registry.contract_address,
            1
        ]
    )

    return adminAuth, registry, deposit_data_manager, admin1, admin2


@pytest.mark.asyncio
async def test_store_and_query(adminAuth_factory):
    adminAuth, registry, deposit_data_manager, admin1, admin2 = adminAuth_factory

    result = await deposit_data_manager.get_deposit_data(admin2.contract_address).call()
    result = result.result.res
    assert len(result) == 0

    await signer1.send_transaction(admin1,
                                   deposit_data_manager.contract_address, 
                                   'store_deposit_data', 
                                   [1, admin2.contract_address, 2, 3, 4, 5, 6])

    result = await deposit_data_manager.get_deposit_data(admin2.contract_address).call()
    result = result.result.res
    assert len(result) == 1
    assert result[0].user_L1_address == 1
    assert result[0].user_L2_address == admin2.contract_address
    assert result[0].ticker == 2
    assert result[0].amount == 3
    assert result[0].nonce == 4
    assert result[0].message_hash == 5
    assert result[0].timestamp == 6

    print('----')
    print(result)

    await signer1.send_transaction(admin1,
                                   deposit_data_manager.contract_address, 
                                   'store_deposit_data', 
                                   [10, admin2.contract_address, 20, 30, 40, 50, 60])

    result = await deposit_data_manager.get_deposit_data(admin2.contract_address).call()
    result = result.result.res
    assert len(result) == 2
    assert result[0].user_L1_address == 1
    assert result[0].user_L2_address == admin2.contract_address
    assert result[0].ticker == 2
    assert result[0].amount == 3
    assert result[0].nonce == 4
    assert result[0].message_hash == 5
    assert result[0].timestamp == 6

    assert result[1].user_L1_address == 10
    assert result[1].user_L2_address == admin2.contract_address
    assert result[1].ticker == 20
    assert result[1].amount == 30
    assert result[1].nonce == 40
    assert result[1].message_hash == 50
    assert result[1].timestamp == 60

    print('----')
    print(result)

    result = await deposit_data_manager.get_deposit_data(admin1.contract_address).call()
    result = result.result.res
    assert len(result) == 0


@pytest.mark.asyncio
async def test_store_with_0_address(adminAuth_factory):
    adminAuth, registry, deposit_data_manager, admin1, admin2 = adminAuth_factory

    # cannot store with L2 address as 0
    await assert_revert(signer1.send_transaction(admin1,
                                                 deposit_data_manager.contract_address, 
                                                 'store_deposit_data', 
                                                 [1, 0, 2, 3, 4, 5, 6]))


@pytest.mark.asyncio
async def test_registry_version_functions(adminAuth_factory):
    adminAuth, registry, deposit_data_manager, admin1, admin2 = adminAuth_factory

    result = await deposit_data_manager.get_registry_address().call()
    result = result.result.address

    assert result == registry.contract_address

    result = await deposit_data_manager.get_current_version().call()
    result = result.result.current_version

    assert result == 1

    await signer1.send_transaction(admin1,
                                   deposit_data_manager.contract_address, 'set_version', [2])

    result = await deposit_data_manager.get_current_version().call()
    result = result.result.current_version

    assert result == 2
