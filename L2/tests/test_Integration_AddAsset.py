import pytest
import asyncio
import json
import os
from starkware.starknet.testing.starknet import Starknet
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, assert_event_emitted
from helpers import StarknetService, ContractType, AccountFactory
from starkware.eth.eth_test_utils import EthTestUtils
from starkware.starknet.testing.contracts import MockStarknetMessaging
from starkware.starknet.testing.postman import Postman
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3


counter = 0
eth_test_utils = EthTestUtils()
# Generates unique asset params (id, ticker and name) to avoid conflicts
def generate_asset_info():
    global counter
    counter += 1
    id = f"32f0406jz7qj8_${counter}"
    ticker = f"ETH_${counter}"
    name = f"Ethereum_${counter}"
    return str_to_felt(id), str_to_felt(ticker), str_to_felt(name)

def build_default_asset_properties(id, ticker, name):
    return [
        id, # id
        0, # asset_version
        ticker, # ticker
        name, # short_name
        0, # tradable
        0, # collateral
        18, # token_decimal
        0, # metadata_id
        1, # tick_size
        1, # step_size
        10, # minimum_order_size
        1, # minimum_leverage
        5, # maximum_leverage
        3, # currently_allowed_leverage
        1, # maintenance_margin_fraction
        1, # initial_margin_fraction
        1, # incremental_initial_margin_fraction
        100, # incremental_position_size
        1000, # baseline_position_size
        10000 # maximum_position_size
    ]

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

    # Deploy infrustructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])

    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    
   
    mock_starknet_messaging_contract=eth_test_utils.accounts[0].deploy(MockStarknetMessaging,0)
    script_dir = os.path.dirname(__file__)
    rel_path ="contract_abi_l1/L1ZKXContract.json" 
    f=open(os.path.join(script_dir,rel_path))
    l1_zkx_contract_json = json.load(f)
    l1_zkx_contract = eth_test_utils.accounts[0].deploy(l1_zkx_contract_json,
                                                mock_starknet_messaging_contract.address,asset.contract_address,1234)
    postman = Postman(mock_starknet_messaging_contract, starknet_service.starknet)
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, int(l1_zkx_contract.address,16)])
    return adminAuth, registry, asset, admin1, admin2, user1, postman, l1_zkx_contract

@pytest.mark.asyncio
async def test_adding_asset_by_admin(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, user1, postman, l1_zkx_contract = adminAuth_factory
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_ticker, asset_name)

    add_asset_tx = await signer1.send_transaction(admin1, asset.contract_address, 'addAsset', asset_properties)
    assert_event_emitted(
        add_asset_tx,
        from_address=asset.contract_address,
        name="Asset_Added",
        data=[
            asset_id,
            asset_ticker,
            admin1.contract_address
        ]
    )

    l2_to_l1_messages_log = postman.starknet.state.l2_to_l1_messages_log
    assert len(l2_to_l1_messages_log) >= postman.n_consumed_l2_to_l1_messages
    for message in l2_to_l1_messages_log[postman.n_consumed_l2_to_l1_messages :]:
        print(message)

    await postman.flush()

    asset_list = l1_zkx_contract.getAssetList.call()
    print(asset_list)

    stored_asset_id = l1_zkx_contract.assetID.call(asset_ticker)
    print(stored_asset_id)

    l1_zkx_contract.updateAssetListInL1.transact(asset_ticker, asset_id)

    asset_list = l1_zkx_contract.getAssetList.call()
    print(asset_list)

    stored_asset_id = l1_zkx_contract.assetID.call(asset_ticker)
    print(stored_asset_id)
