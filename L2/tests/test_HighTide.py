import pytest
import asyncio
import time
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, to64x61, PRIME
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):
    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    user1 = await account_factory.deploy_account(signer3.public_key)
    
    # Deploy infrastructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    hightide = await starknet_service.deploy(ContractType.HighTide, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 8, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [24, 1, hightide.contract_address])

    return adminAuth, hightide, admin1, admin2, user1

@pytest.mark.asyncio
async def test_setup_trading_season_unauthorized_user(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1 = adminAuth_factory

    timestamp = int(time.time())
    await assert_revert( signer3.send_transaction(user1, hightide.contract_address, 'setup_trade_season', [
        str_to_felt("100"), timestamp, to64x61(30)]))

@pytest.mark.asyncio
async def test_setup_trading_season_authorized_admin(adminAuth_factory):
    adminAuth, hightide, admin1, admin2, user1 = adminAuth_factory

    timestamp = int(time.time())
    await signer1.send_transaction(admin1, hightide.contract_address, 'setup_trade_season', [
        str_to_felt("100"), timestamp, to64x61(30)])

    execution_info = await hightide.get_season(str_to_felt("100")).call()
    fetched_trading_season = execution_info.result.trading_season

    assert fetched_trading_season.start_timestamp == timestamp
    assert fetched_trading_season.num_trading_days == to64x61(30)