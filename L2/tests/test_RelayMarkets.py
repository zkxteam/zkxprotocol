import pytest
import asyncio
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
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    market = await starknet_service.deploy(ContractType.Markets, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [2, 1, market.contract_address])

    # Deploy Relay contracts with appropriate index as per entries in registry
    relay_asset = await starknet_service.deploy(ContractType.RelayAsset, [
        registry.contract_address, 
        1,
        1 # asset index
    ])
    relay_market = await starknet_service.deploy(ContractType.RelayMarkets, [
        registry.contract_address, 
        1,
        2 # market index
    ])

    # Give appropriate permissions to relays
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_asset.contract_address, 2, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_market.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [relay_market.contract_address, 2, 1])

    await signer1.send_transaction(admin1, relay_asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 1, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, relay_asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj7"), 0, str_to_felt("USDC"), str_to_felt("USDCoin"), 0, 1, 6, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, relay_asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj6"), 0, str_to_felt("DOT"), str_to_felt("Polkadot"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, relay_asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj9"), 0, str_to_felt("TSLA"), str_to_felt("Tesla"), 0, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, relay_asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj10"), 0, str_to_felt("USDT"), str_to_felt("USDTether"), 0, 1, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj11"), 0, str_to_felt("LINK"), str_to_felt("Chainlink"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj12"), 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    # Return relay versions of asset, market to test logic of underlying contracts
    return adminAuth, relay_asset, relay_market, admin1, admin2, user1


@pytest.mark.asyncio
async def test_add_new_market_not_admin(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer3.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60])
    )


@pytest.mark.asyncio
async def test_add_new_market_invalid_leverage(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(11), 1, 0, 60]))
    
    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(0), 1, 0, 60]))
    
    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(-43)%PRIME, 1, 0, 60]))

@pytest.mark.asyncio
async def test_add_new_market_invalid_ttl(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 0]))
    
    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 36001]))
    
    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, -60%PRIME]))

@pytest.mark.asyncio
async def test_add_new_market_invalid_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 0, 0, 60]))

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 3, 0, 60]))
    
    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), -1%PRIME, 0, 60]))

@pytest.mark.asyncio
async def test_add_new_market_non_existent_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7q348"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60]))

@pytest.mark.asyncio
async def test_add_new_market_non_existent_collateral(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7q316"), to64x61(8), 1, 0, 60]))

@pytest.mark.asyncio
async def test_add_new_market_not_collateral(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj9"), to64x61(8), 1, 0, 60]))

@pytest.mark.asyncio
async def test_add_new_tradable_market_non_tradable_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60]))


@pytest.mark.asyncio
async def test_add_new_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(10), 1, 0, 60])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(10)

    markets = await market.get_all_markets().call()
    parsed_list = list(markets.result.array_list)[0]

    assert parsed_list.id == str_to_felt("32f0406jz7qk1")
    assert parsed_list.asset == str_to_felt("32f0406jz7qj8")
    assert parsed_list.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert parsed_list.leverage == to64x61(10)

@pytest.mark.asyncio
async def test_override_existing_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj11"), str_to_felt("32f0406jz7qj7=10"), to64x61(10), 1, 0, 60]))


@pytest.mark.asyncio
async def test_add_new_market_with_existing_market_pair(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk9"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(10), 1, 0, 60]))


@pytest.mark.asyncio
async def test_add_new_market_non_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk3"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk3")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj6")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(8)
    assert fetched_market.tradable == 1


@pytest.mark.asyncio
async def test_add_new_market_default_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk4"), str_to_felt("32f0406jz7qj11"), str_to_felt("32f0406jz7qj7"), to64x61(1), 2, 0, 10])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk4")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj11")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(1)
    assert fetched_market.tradable == 2


@pytest.mark.asyncio
async def test_modify_leverage(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_leverage', [str_to_felt("32f0406jz7qk1"), to64x61(5)])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(5)


@pytest.mark.asyncio
async def test_modify_tradable_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk1"), 0]))

@pytest.mark.asyncio
async def test_modify_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk1"), 0])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(5)
    assert fetched_market.tradable == 0


@pytest.mark.asyncio
async def test_modify_tradable_0_to_1(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk5"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj10"), to64x61(6), 1, 0, 10])
    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk5"), 1])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk5")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj10")
    assert fetched_market.leverage == to64x61(6)
    assert fetched_market.tradable == 1


@pytest.mark.asyncio
async def test_remove_market_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(
        user1, market.contract_address, 'remove_market', [str_to_felt("32f0406jz7qk1")]))


@pytest.mark.asyncio
async def test_remove_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'remove_market', [str_to_felt("32f0406jz7qk1")])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == 0
    assert fetched_market.asset_collateral == 0
    assert fetched_market.leverage == 0

@pytest.mark.asyncio
async def test_change_leverage_unauthorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'change_max_leverage', [to64x61(100)]))


@pytest.mark.asyncio
async def test_change_ttl_unauthorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'change_ttl_leverage', [to64x61(7200)]))


@pytest.mark.asyncio
async def test_change_leverage_authorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'change_max_leverage', [to64x61(100)])

@pytest.mark.asyncio
async def test_change_ttl_authorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'change_max_ttl', [7200])

@pytest.mark.asyncio
async def test_retrieve_markets(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    markets = await market.get_all_markets().call()

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdj"), str_to_felt("32f0406jz7qj12"), str_to_felt("32f0406jz7qj10"), to64x61(50), 1, 0, 3610])


    execution_info = await market.get_market(str_to_felt("32f0406jz7qk5")).call()
    fetched_market = execution_info.result.currMarket

    print(fetched_market)
    markets_new = await market.get_all_markets().call()

    assert len(list(markets_new.result.array_list)) == len(list(markets.result.array_list)) + 1
       
