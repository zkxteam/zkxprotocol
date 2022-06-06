import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert

signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory():
    starknet = await Starknet.empty()
    admin1 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer1.public_key, 0]
    )

    admin2 = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer2.public_key, 0]
    )

    user1 = await starknet.deploy(
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

    asset = await starknet.deploy(
        "contracts/Asset.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
            0
        ]
    )

    market = await starknet.deploy(
        "contracts/Markets.cairo",
        constructor_calldata=[
            adminAuth.contract_address,
            asset.contract_address
        ]
    )

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 2, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', [str_to_felt("32f0406jz7qj8"), 0, str_to_felt("ETH"), str_to_felt("Ethereum"), 1, 0, 18, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', [str_to_felt("32f0406jz7qj7"), 0, str_to_felt("USDC"), str_to_felt("USDCoin"), 0, 1, 6, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])
    await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', [str_to_felt("32f0406jz7qj6"), 0, str_to_felt("DOT"), str_to_felt("Polkadot"), 0, 0, 10, 0, 1, 1, 10, 1, 5, 3, 1, 1, 1, 100, 1000, 10000])

    return adminAuth, asset, market, admin1, admin2, user1


@pytest.mark.asyncio
async def test_get_admin_mapping(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    execution_info = await adminAuth.get_admin_mapping(admin1.contract_address, 1).call()
    assert execution_info.result.allowed == 1

    execution_info1 = await adminAuth.get_admin_mapping(admin2.contract_address, 1).call()
    assert execution_info1.result.allowed == 0


@pytest.mark.asyncio
async def test_add_new_market_no_collateral(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer3.send_transaction(user1, market.contract_address, 'addMarket', [
                  str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj6"), 1, 0]))


@pytest.mark.asyncio
async def test_add_new_market_invalid_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer1.send_transaction(admin1, market.contract_address, 'addMarket', [
                  str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7ql8"), str_to_felt("32f0406jz7qj7"), 1, 0]))


@pytest.mark.asyncio
async def test_add_new_tradable_market_non_tradable_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer3.send_transaction(user1, market.contract_address, 'addMarket', [
                  str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), 1, 1]))


@pytest.mark.asyncio
async def test_add_new_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'addMarket', [str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), 1, 1])

    execution_info = await market.getMarket(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.assetCollateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == 1


@pytest.mark.asyncio
async def test_add_new_market_non_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'addMarket', [str_to_felt("32f0406jz7qk3"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), 1, 0])

    execution_info = await market.getMarket(str_to_felt("32f0406jz7qk3")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj6")
    assert fetched_market.assetCollateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == 1
    assert fetched_market.tradable == 0


@pytest.mark.asyncio
async def test_add_new_market_default_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'addMarket', [str_to_felt("32f0406jz7qk4"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), 1, 2])

    execution_info = await market.getMarket(str_to_felt("32f0406jz7qk4")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj6")
    assert fetched_market.assetCollateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == 1
    assert fetched_market.tradable == 0


@pytest.mark.asyncio
async def test_add_new_market_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer3.send_transaction(user1, market.contract_address, 'addMarket', [
                  str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), 1, 1]))


@pytest.mark.asyncio
async def test_add_new_market_non_tradable_asset(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'addMarket', [str_to_felt("32f0406jz7qk1"), str_to_felt("32f0406jz7qj6"), str_to_felt("32f0406jz7qj7"), 1, 0])


@pytest.mark.asyncio
async def test_modify_leverage_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer1.send_transaction(
        admin1, market.contract_address, 'modifyLeverage', [str_to_felt("32f0406jz7qk1"), 2]))


@pytest.mark.asyncio
async def test_modify_leverage(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modifyLeverage', [str_to_felt("32f0406jz7qk1"), 2])

    execution_info = await market.getMarket(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj6")
    assert fetched_market.assetCollateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == 2


@pytest.mark.asyncio
async def test_modify_tradable_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer1.send_transaction(
        admin1, market.contract_address, 'modifyLeverage', [str_to_felt("32f0406jz7qk1"), 0]))


@pytest.mark.asyncio
async def test_modify_tradable(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'modifyTradable', [str_to_felt("32f0406jz7qk1"), 0])

    execution_info = await market.getMarket(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj6")
    assert fetched_market.assetCollateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == 2
    assert fetched_market.tradable == 0


@pytest.mark.asyncio
async def test_modify_tradable_0_to_1(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'addMarket', [str_to_felt("32f0406jz7qk5"), str_to_felt("32f0406jz7qj8"), str_to_felt("32f0406jz7qj7"), 1, 0])
    await signer1.send_transaction(admin1, market.contract_address, 'modifyTradable', [str_to_felt("32f0406jz7qk5"), 1])

    execution_info = await market.getMarket(str_to_felt("32f0406jz7qk5")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == str_to_felt("32f0406jz7qj8")
    assert fetched_market.assetCollateral == str_to_felt("32f0406jz7qj7")
    assert fetched_market.leverage == 1
    assert fetched_market.tradable == 1


@pytest.mark.asyncio
async def test_remove_market_unauthorized_user(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    assert_revert(lambda: signer1.send_transaction(
        admin1, market.contract_address, 'removeMarket', [str_to_felt("32f0406jz7qk1")]))


@pytest.mark.asyncio
async def test_remove_market(adminAuth_factory):
    adminAuth, asset, market, admin1, admin2, user1 = adminAuth_factory

    await signer1.send_transaction(admin1, market.contract_address, 'removeMarket', [str_to_felt("32f0406jz7qk1")])

    execution_info = await market.getMarket(str_to_felt("32f0406jz7qk1")).call()
    fetched_market = execution_info.result.currMarket

    assert fetched_market.asset == 0
    assert fetched_market.assetCollateral == 0
    assert fetched_market.leverage == 0
