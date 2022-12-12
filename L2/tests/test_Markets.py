import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import ContractIndex, ManagerAction, str_to_felt, assert_revert, to64x61, PRIME
from utils_asset import AssetID, build_asset_properties
from utils_links import DEFAULT_LINK_1, DEFAULT_LINK_2, prepare_starknet_string, encode_characters
from helpers import StarknetService, ContractType, AccountFactory
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3

DEFAULT_MARKET_ID = str_to_felt("32f0406jz7qk1")

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

    # Give permissions
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAssets, True])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageMarkets, True])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, ManagerAction.ManageAuthRegistry, True])

    # Add contracts to registry
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Asset, 1, asset.contract_address])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [ContractIndex.Market, 1, market.contract_address])

    # Add assets
    async def add_asset(id, name, is_tradable, is_collateral, decimals):
        asset_properties = build_asset_properties(
            id = id,
            short_name = str_to_felt(name),
            asset_version = 0,
            is_tradable = is_tradable,
            is_collateral = is_collateral,
            token_decimal = decimals
        )
        await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)

    await add_asset(AssetID.ETH, "Ethereum", True, False, 18)
    await add_asset(AssetID.USDC, "USDCoin", False, True, 6)
    await add_asset(AssetID.DOT, "Polkadot", True, False, 10)
    await add_asset(AssetID.TSLA, "Tesla", False, False, 10)
    await add_asset(AssetID.USDT, "USDTether", False, True, 10)
    await add_asset(AssetID.LINK, "Chainlink", True, False, 10)
    await add_asset(AssetID.BTC, "Bitcoin", True, False, 10)
    await add_asset(AssetID.SUPER, "Super", True, False, 10)
    await add_asset(AssetID.DOGE, "Doge", True, True, 18)
    await add_asset(AssetID.ADA, "Cardano", True, False, 10)
    await add_asset(AssetID.LUNA, "Luna", True, False, 10)

    return adminAuth, asset, market, admin1, admin2, user1


@pytest.mark.asyncio
async def test_add_new_market_not_admin(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer3.send_transaction(user1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    )


@pytest.mark.asyncio
async def test_add_new_market_invalid_leverage(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(11), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)),
        reverted_with="Markets: Leverage must be <= MAX leverage"
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(0), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)),
        reverted_with="Markets: Leverage must be >= MIN leverage"
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(-43)%PRIME, 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)),
        reverted_with="Markets: Leverage must be >= MIN leverage"
    )

@pytest.mark.asyncio
async def test_add_new_market_invalid_ttl(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)),
        reverted_with="Markets: ttl must be in range [1...max_ttl]"
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 36001, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)),
        reverted_with="Markets: ttl must be in range [1...max_ttl]"
    )
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, -60%PRIME, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)),
        reverted_with="Markets: ttl must be in range [1...max_ttl]"
    )

@pytest.mark.asyncio
async def test_add_new_market_invalid_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    # commented out the following test since is_tradable parameter can be 0 as per smart contract code
    # assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
    #    DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 0, 0, 60]))

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), 3, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)))
    
    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(8), -1%PRIME, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)),
        "Markets: is_tradable must 0, 1 or 2"
    )

@pytest.mark.asyncio
async def test_add_new_market_non_existent_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7q348"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    )

@pytest.mark.asyncio
async def test_add_new_market_non_existent_collateral(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(user1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7q316"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)))

@pytest.mark.asyncio
async def test_add_new_market_not_collateral(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert( signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj9"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)))

@pytest.mark.asyncio
async def test_add_new_tradable_market_non_tradable_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)))


@pytest.mark.asyncio
async def test_add_new_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(10), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))

    execution_info = await market.get_market(DEFAULT_MARKET_ID).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(10)

    markets = await market.get_all_markets().call()
    parsed_list = list(markets.result.array_list)[0]

    assert parsed_list.id == DEFAULT_MARKET_ID
    assert parsed_list.asset == str_to_felt("32f0406jz7qj8")
    assert parsed_list.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert parsed_list.leverage == to64x61(10)

@pytest.mark.asyncio
async def test_override_existing_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        DEFAULT_MARKET_ID, str_to_felt("32f0406jz7qj11"), str_to_felt("32f0406jz7qj7=10"), to64x61(10), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)))


@pytest.mark.asyncio
async def test_add_new_market_with_existing_market_pair(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(
        signer1.send_transaction(admin1, market.contract_address, 'add_market', [
            str_to_felt("32f0406jz7qk9"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), to64x61(10), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1)))


@pytest.mark.asyncio
async def test_add_new_market_non_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk3"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), to64x61(8), 1, 0, 60, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk3")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj6")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(8)
    assert fetched_market.is_tradable == 1


@pytest.mark.asyncio
async def test_add_new_market_default_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("32f0406jz7qk4"), str_to_felt("32f0406jz7qj11"), str_to_felt("32f0406jz7qj7"), to64x61(1), 2, 0, 10, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))

    execution_info = await market.get_market(str_to_felt("32f0406jz7qk4")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj11")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(1)
    # assert fetched_market.is_tradable == 2


@pytest.mark.asyncio
async def test_modify_leverage(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_leverage', [DEFAULT_MARKET_ID, to64x61(5)])

    execution_info = await market.get_market(DEFAULT_MARKET_ID).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(5)


@pytest.mark.asyncio
async def test_modify_tradable_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'modify_tradable', [DEFAULT_MARKET_ID, 0]))


@pytest.mark.asyncio
async def test_modify_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [DEFAULT_MARKET_ID, 0])

    execution_info = await market.get_market(DEFAULT_MARKET_ID).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.asset_collateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == to64x61(5)
    assert fetched_market.is_tradable == 0

@pytest.mark.asyncio
async def test_modify_non_admin_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(
        signer3.send_transaction(user1, market.contract_address, 'modify_tradable', [DEFAULT_MARKET_ID, 1]))


@pytest.mark.asyncio
async def test_modify_tradable_0_to_1(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [
        str_to_felt("32f0406jz7qk5"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj10"), to64x61(6), 1, 0, 10, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
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
        user1, market.contract_address, 'remove_market', [DEFAULT_MARKET_ID]))

@pytest.mark.asyncio
async def test_remove_tradable_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [DEFAULT_MARKET_ID, 1])

    await assert_revert(signer3.send_transaction(
        admin1, market.contract_address, 'remove_market', [DEFAULT_MARKET_ID]))

@pytest.mark.asyncio
async def test_remove_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modify_tradable', [DEFAULT_MARKET_ID, 0])
    await signer1.send_transaction(admin1, market.contract_address, 'remove_market', [DEFAULT_MARKET_ID])

    execution_info = await market.get_market(DEFAULT_MARKET_ID).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == 0
    assert fetched_market.asset_collateral == 0
    assert fetched_market.leverage == 0

@pytest.mark.asyncio
async def test_change_leverage_unauthorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'change_max_leverage', [to64x61(100)]), reverted_with="Markets: Caller not authorized to manage markets")

@pytest.mark.asyncio
async def test_change_ttl_unauthorized(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await assert_revert(signer3.send_transaction(user1, market.contract_address, 'change_max_ttl', [to64x61(7200)]), reverted_with="Markets: Caller not authorized to manage markets")


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
        str_to_felt("2dsyfdj289fdj"), str_to_felt("32f0406jz7qj12"), str_to_felt("32f0406jz7qj10"), to64x61(50), 1, 0, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))


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

    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdw"), str_to_felt("32f0406jz7qj20"), str_to_felt("32f0406jz7qj7"), to64x61(50), 1, 0, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdh"), str_to_felt("32f0406jz7qj21"), str_to_felt("32f0406jz7qj7"), to64x61(50), 1, 1, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdi"), str_to_felt("32f0406jz7qj22"), str_to_felt("32f0406jz7qj7"), to64x61(50), 0, 1, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    await signer1.send_transaction(admin1, market.contract_address, 'add_market', [str_to_felt("2dsyfdj289fdk"), str_to_felt("32f0406jz7qj23"), str_to_felt("32f0406jz7qj7"), to64x61(50), 0, 0, 3610, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000] + prepare_starknet_string(DEFAULT_LINK_1))
    

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
    await assert_revert(
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
        ])
    )

@pytest.mark.asyncio
async def test_update_metadata_link_by_admin(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    market_id = str_to_felt("2dsyfdj289fdw")
    metadata_link_call = await market.get_metadata_link(market_id).call()
    metadata_link = list(metadata_link_call.result.link)
    assert metadata_link == encode_characters(DEFAULT_LINK_1)

    NEW_LINK = DEFAULT_LINK_2
    await signer1.send_transaction(
        admin1, 
        market.contract_address, 
        'update_metadata_link',
        [market_id] + prepare_starknet_string(NEW_LINK)
    )

    new_metadata_link_call = await market.get_metadata_link(market_id).call()
    new_metadata_link = list(new_metadata_link_call.result.link)
    assert new_metadata_link == encode_characters(NEW_LINK)

async def test_remove_metadata_link_by_admin(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    market_id = str_to_felt("2dsyfdj289fdw")
    await signer1.send_transaction(
        admin1, 
        market.contract_address, 
        'update_metadata_link',
        [market_id] + prepare_starknet_string("")
    )

    new_metadata_link_call = await market.get_metadata_link(market_id).call()
    new_metadata_link = list(new_metadata_link_call.result.link)
    assert new_metadata_link == encode_characters("")

@pytest.mark.asyncio
async def test_update_metadata_link_by_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    market_id = str_to_felt("2dsyfdj289fdw")
    NEW_LINK = DEFAULT_LINK_2

    await assert_revert(
        signer3.send_transaction(
            user1, 
            market.contract_address, 
            'update_metadata_link', 
            [market_id] + prepare_starknet_string(NEW_LINK)
        )
    )
