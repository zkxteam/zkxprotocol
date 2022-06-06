import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)
signer4 = Signer(123456789987654324)


@pytest.fixture
def global_var():
    pytest.user1 = None
    pytest.user2 = None


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def emergencyFund_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0]
    )

    pytest.user1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer3.public_key, 0]
    )

    pytest.user2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer4.public_key, 0]
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

    holding = await starknet.deploy(
        "contracts/Holding.cairo",
        constructor_calldata=[
            adminAuth.contract_address, registry.contract_address]
    )

    emergencyFund = await starknet.deploy(
        "contracts/EmergencyFund.cairo",
        constructor_calldata=[
            adminAuth.contract_address, registry.contract_address]
    )
    # Access 2 allows adding trusted contracts to the registry
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_registry', [emergencyFund.contract_address, 8, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_registry', [holding.contract_address, 5, 1])

    return emergencyFund, holding, admin1, admin2


@pytest.mark.asyncio
async def test_fund_invalid(emergencyFund_factory):
    emergencyFund, _, admin1, admin2 = emergencyFund_factory
    assert_revert(lambda: signer3.send_transaction(
        pytest.user1, emergencyFund.contract_address, 'fund', [str_to_felt("TSLA"), 0]))


@pytest.mark.asyncio
async def test_funding_flow(emergencyFund_factory):
    emergencyFund, _, admin1, admin2 = emergencyFund_factory

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'fund', [str_to_felt("TSLA"), 10])
    execution_info = await emergencyFund.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 10

    await signer2.send_transaction(admin2, emergencyFund.contract_address, 'defund', [str_to_felt("TSLA"), 3])
    execution_info = await emergencyFund.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 7


@pytest.mark.asyncio
async def test_fund_through_funding_invalid(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2 = emergencyFund_factory
    assert_revert(lambda: signer1.send_transaction(
        admin1, holding.contract_address, 'fund_holding', [str_to_felt("TSLA"), 10, holding.contract_address]))


@pytest.mark.asyncio
async def test_fund_through_funding_contract(emergencyFund_factory):
    emergencyFund, holding, admin1, admin2 = emergencyFund_factory

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'fund_holding', [str_to_felt("TSLA"), 10, holding.contract_address])
    execution_info = await holding.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 10

    await signer1.send_transaction(admin1, emergencyFund.contract_address, 'defund_holding', [str_to_felt("TSLA"), 3, holding.contract_address])
    execution_info = await holding.balance(str_to_felt("TSLA")).call()
    assert execution_info.result.amount == 7
