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

    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 1, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj7"), 0, str_to_felt("USDC"), str_to_felt("USDCoin"), 0, 1, 6, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj6"), 0, str_to_felt("DOT"), str_to_felt("Polkadot"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj9"), 0, str_to_felt("TSLA"), str_to_felt("Tesla"), 0, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj10"), 0, str_to_felt("USDT"), str_to_felt("USDTether"), 0, 1, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj11"), 0, str_to_felt("LINK"), str_to_felt("Chainlink"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj12"), 0, str_to_felt("BTC"), str_to_felt("Bitcoin"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj20"), 0, str_to_felt("SUPER"), str_to_felt("Super"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj21"), 0, str_to_felt("DOGE"), str_to_felt("Doge"), 1, 1, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj22"), 0, str_to_felt("ADA"), str_to_felt("Cardano"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', [str_to_felt("32f0406jz7qj23"), 0, str_to_felt("LUNA"), str_to_felt("Luna"), 1, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    return adminAuth, asset, market, admin1, admin2, user1


@pytest.mark.asyncio
async def test_add_new_market_not_admin(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( 
        signer3.send_transaction(user1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: Unauthorized call to manage markets"
    )


@pytest.mark.asyncio
async def test_add_new_market_invalid_leverage(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(11), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: Leverage must be <= max leverage"
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(0), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: Leverage must be >= 1"
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(-43)%PRIME, 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: Leverage must be >= 1"
    )

@pytest.mark.asyncio
async def test_add_new_market_invalid_ttl(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: ttl must be > 1"  
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 36001, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: ttl must be <= max ttl"    
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, -60%PRIME, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: ttl must be > 1"
    )

@pytest.mark.asyncio
async def test_add_new_market_invalid_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    # commented out the following test since tradable parameter can be 0 as per smart contract code
    # assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
    #    str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 0, 0, 60]))

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 3, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: Tradable must be <= max trabele"
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), -1%PRIME, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: Tradable cannot be less than zero"
    )

@pytest.mark.asyncio
async def test_add_new_market_non_existent_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("sk3j49udfsj32h4"), str_to_felt("32f0406jz7q348"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    )

@pytest.mark.asyncio
async def test_add_new_market_non_existent_collateral(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("342kldjslij54ll"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7q316"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
    )

@pytest.mark.asyncio
async def test_add_new_market_not_collateral(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("mdsf2dsgkljl5"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj9"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
    )

@pytest.mark.asyncio
async def test_add_new_tradable_market_non_tradable_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer1.send_transaction(user1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
    )


@pytest.mark.asyncio
async def test_add_new_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(10), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

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
        signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj11"), str_to_felt("32f0406jz7qj7=10"), to64x61(10), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]),
        reverted_with="Markets: market ID existence mismatch"    
    )


@pytest.mark.asyncio
async def test_add_new_market_with_existing_market_pair(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk9"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(10), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000]), 
        reverted_with="Markets: Market pair existence mismatch"
    )


@pytest.mark.asyncio
async def test_add_new_market_non_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk3"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk3")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj6")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(8)
    assert fetched_market.is_tradable == 1


@pytest.mark.asyncio
async def test_add_new_market_default_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk4"), str_to_felt("32f0406jz7qj11"), str_to_felt("32f0406jz7qj7"), to64x61(1), 2, 0, 10, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk4")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj11")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(1)
    assert fetched_market.is_tradable == 2


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

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk1"), 0]), reverted_with="Markets: Unauthorized call to manage markets")


@pytest.mark.asyncio
async def test_modify_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk1"), 0])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(5)
    assert fetched_market.is_tradable == 0

@pytest.mark.asyncio
async def test_modify_non_admin_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(
        signer3.send_transaction(user1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk1"), 1]), reverted_with="Markets: Unauthorized call to manage markets")


@pytest.mark.asyncio
async def test_modify_tradable_0_to_1(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk5"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj10"), to64x61(6), 1, 0, 10, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk5"), 1])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk5")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj10")
    assert fetched_market.leverage == to64x61(6)
    assert fetched_market.is_tradable == 1


@pytest.mark.asyncio
async def test_remove_market_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(
        user1, market.contract_address, 'remove_market', [str_to_felt("32f0406jz7qk1")]), reverted_with="Markets: Unauthorized call to manage markets")

@pytest.mark.asyncio
async def test_remove_tradable_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk1"), 1])

    await assert_revert(signer1.send_transaction(
        admin1, market.contract_address, 'remove_market', [str_to_felt("32f0406jz7qk1")]), reverted_with="Markets: Tradable market cannot be removed")

@pytest.mark.asyncio
async def test_remove_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [str_to_felt("32f0406jz7qk1"), 0])
    await signer1.send_transaction(admin1, market.contract_address, 'remove_market', [str_to_felt("32f0406jz7qk1")])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == 0
    assert fetched_market.asset_collateral == 0
    assert fetched_market.leverage == 0

@pytest.mark.asyncio
async def test_change_leverage_unauthorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'change_max_leverage', [to64x61(100)]), reverted_with="Markets: Unauthorized call to manage markets")

@pytest.mark.asyncio
async def test_change_ttl_unauthorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'change_max_ttl', [to64x61(7200)]), reverted_with="Markets: Unauthorized call to manage markets")


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

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("2dsyfdj289fdj"), str_to_felt("32f0406jz7qj12"), str_to_felt("32f0406jz7qj10"), to64x61(50), 1, 0, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])


    execution_info = await market.get_market(str_to_felt("32f0406jz7qk5")).call()
    fetched_market = execution_info.result.currMarket

    print(fetched_market)
    markets_new = await market.get_all_markets().call()

    assert len(list(markets_new.result.array_list)) == len(list(markets.result.array_list)) + 1

@pytest.mark.asyncio
async def test_modify_archived_state(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_archived_state', [str_to_felt("32f0406jz7qk5"), 1])

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk5")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj10")
    assert fetched_market.leverage == to64x61(6)
    assert fetched_market.is_tradable == 1
    assert fetched_market.is_archived == 1

@pytest.mark.asyncio
async def test_get_all_archived_tradable_markets(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdw"), str_to_felt("32f0406jz7qj20"), str_to_felt("32f0406jz7qj7"), to64x61(50), 1, 0, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdh"), str_to_felt("32f0406jz7qj21"), str_to_felt("32f0406jz7qj7"), to64x61(50), 1, 1, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdi"), str_to_felt("32f0406jz7qj22"), str_to_felt("32f0406jz7qj7"), to64x61(50), 0, 1, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdk"), str_to_felt("32f0406jz7qj23"), str_to_felt("32f0406jz7qj7"), to64x61(50), 0, 0, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    

    markets = await market.get_all_markets().call()
    print("Market list:", markets.result.array_list)
    print("Market list length:", len(list(markets.result.array_list)))

    markets_new = await market.get_all_markets_by_state(1, 1).call()
    print("New Market list:", markets_new.result.array_list)

    assert len(list(markets_new.result.array_list)) == len(list(markets.result.array_list)) - 6  

@pytest.mark.asyncio
async def test_modifying_trade_settings_by_admin(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    market_id = str_to_felt("2dsyfdj289fdw")
    new_tick_size = to64x61(2)
    new_step_size = to64x61(2)
    new_minimum_order_size = to64x61(0.25)
    new_minimum_leverage = to64x61(2)
    new_maximum_leverage = to64x61(100)
    new_currently_allowed_leverage = to64x61(100)
    new_maintenance_margin_fraction = to64x61(2)
    new_initial_margin_fraction = to64x61(2)
    new_incremental_initial_margin_fraction = to64x61(2)
    new_incremental_position_size = to64x61(200)
    new_baseline_position_size = to64x61(2000)
    new_maximum_position_size = to64x61(20000)

    modify_tx = await signer1.send_transaction(admin1, market.contract_address, 'modify_trade_settings', [
        market_id, 
        new_tick_size, 
        new_step_size, 
        new_minimum_order_size, 
        new_minimum_leverage, 
        new_maximum_leverage, 
        new_currently_allowed_leverage, 
        new_maintenance_margin_fraction, 
        new_initial_margin_fraction, 
        new_incremental_initial_margin_fraction, 
        new_incremental_position_size, 
        new_baseline_position_size, 
        new_maximum_position_size
    ])

    execution_info = await market.get_market(market_id).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.tick_size == new_tick_size
    assert fetched_market.step_size == new_step_size
    assert fetched_market.minimum_order_size == new_minimum_order_size
    assert fetched_market.minimum_leverage == new_minimum_leverage
    assert fetched_market.maximum_leverage == new_maximum_leverage
    assert fetched_market.currently_allowed_leverage == new_currently_allowed_leverage
    assert fetched_market.maintenance_margin_fraction == new_maintenance_margin_fraction
    assert fetched_market.initial_margin_fraction == new_initial_margin_fraction
    assert fetched_market.incremental_initial_margin_fraction == new_incremental_initial_margin_fraction
    assert fetched_market.incremental_position_size == new_incremental_position_size
    assert fetched_market.baseline_position_size == new_baseline_position_size
    assert fetched_market.maximum_position_size == new_maximum_position_size

@pytest.mark.asyncio
async def test_modifying_trade_settings_by_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    market_id = str_to_felt("2dsyfdj289fdw")
    assert_revert(lambda: 
        signer3.send_transaction(user1, market.contract_address, 'modify_trade_settings', [
            market_id, 
            to64x61(2), # tick_size 
            to64x61(2), # step_size
            to64x61(0.25), # minimum_order_size
            to64x61(2), # minimum_leverage
            to64x61(100), # maximum_leverage
            to64x61(100), # currently_allowed_leverage
            to64x61(2), # maintenance_margin_fraction
            to64x61(2), # initial_margin_fraction
            to64x61(2), # incremental_initial_margin_fraction
            to64x61(200), # incremental_position_size
            to64x61(2000), # baseline_position_size
            to64x61(20000) # maximum_position_size
        ]),
        reverted_with="Markets: Unauthorized call to manage markets"
    ) 