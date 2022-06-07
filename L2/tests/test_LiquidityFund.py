import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)


@pytest.fixture
def global_var():
    pytest.user1 = None


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def holding_factory():
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

    liquidity = await starknet.deploy(
        "contracts/LiquidityFund.cairo",
        constructor_calldata=[
            adminAuth.contract_address, registry.contract_address]
    )

    return adminAuth, liquidity, admin1, admin2


@pytest.mark.asyncio
async def test_fund_admin(holding_factory):
    _, liquidity, admin1, _ = holding_factory

    await signer1.send_transaction(admin1, liquidity.contract_address, 'fund', [str_to_felt("USDC"), 100])

    execution_info = await liquidity.balance(str_to_felt("USDC")).call()
    assert execution_info.result.amount == 100


@pytest.mark.asyncio
async def test_fund_reject(holding_factory):
    _, liquidity, _, _ = holding_factory

    assert_revert(lambda: signer3.send_transaction(
        pytest.user1, liquidity.contract_address, 'fund', [str_to_felt("USDC"), 100]))


@pytest.mark.asyncio
async def test_defund_admin(holding_factory):
    _, liquidity, admin1, _ = holding_factory

    await signer1.send_transaction(admin1, liquidity.contract_address, 'defund', [str_to_felt("USDC"), 100])

    execution_info = await liquidity.balance(str_to_felt("USDC")).call()
    assert execution_info.result.amount == 0


@pytest.mark.asyncio
async def test_defund_reject(holding_factory):
    _, liquidity, _, _ = holding_factory

    assert_revert(lambda: signer3.send_transaction(
        pytest.user1, liquidity.contract_address, 'defund', [str_to_felt("USDC"), 100]))
