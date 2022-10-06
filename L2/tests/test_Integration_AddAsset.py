import pytest
import asyncio
import json
import os
from starkware.starknet.testing.starknet import Starknet
from utils import str_to_felt, MAX_UINT256, assert_event_emitted
from helpers import StarknetService, ContractType, AccountFactory
from starkware.eth.eth_test_utils import EthTestUtils, eth_reverts
from starkware.starknet.testing.contracts import MockStarknetMessaging
from starkware.starknet.testing.postman import Postman
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2


counter = 0
eth_test_utils = EthTestUtils()
# Generates unique asset params (id, ticker and name) to avoid conflicts

DUMMY_WITHDRAWAL_REQUEST_ADDRESS=12345

def generate_asset_info():
    global counter
    counter += 1
    id = f"ETH_${counter}"
    name = f"Ethereum_${counter}"
    return str_to_felt(id), str_to_felt(name)


def build_default_asset_properties(id, ticker, name):
    return [
        id,  # id
        0,  # asset_version
        name,  # short_name
        0,  # tradable
        0,  # collateral
        18,  # token_decimal
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
    

    dec_class = await starknet_service.declare(ContractType.AccountManager)

    global class_hash
    class_hash = dec_class.class_hash

    # Deploy infrustructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    account_registry = await starknet_service.deploy(ContractType.AccountRegistry, [registry.contract_address, 1])
    account_deployer = await starknet_service.deploy(ContractType.AccountDeployer, [registry.contract_address, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 1, 1])
    await signer1.send_transaction(admin1, adminAuth.contract_address, 'update_admin_mapping', [admin1.contract_address, 3, 1])
    await signer1.send_transaction(admin1,
                                   registry.contract_address, 'update_contract_registry', [14, 1, account_registry.contract_address])

    await signer1.send_transaction(admin1,
                                   registry.contract_address, 'update_contract_registry', [20, 1, account_deployer.contract_address])

    await signer1.send_transaction(admin1,
                                   registry.contract_address, 'update_contract_registry', [1, 1, asset.contract_address])

    mock_starknet_messaging_contract = eth_test_utils.accounts[0].deploy(
        MockStarknetMessaging, 0)

    script_dir = os.path.dirname(__file__)
    rel_path = "contract_abi_l1/L1ZKXContract.json"
    f = open(os.path.join(script_dir, rel_path))
    l1_zkx_contract_json = json.load(f)
    l1_zkx_contract = eth_test_utils.accounts[0].deploy(l1_zkx_contract_json,
                                                        mock_starknet_messaging_contract.address, 
                                                        asset.contract_address,
                                                        DUMMY_WITHDRAWAL_REQUEST_ADDRESS)

    script_dir = os.path.dirname(__file__)
    rel_path = "contract_abi_l1/ZKXToken.json" #this abi is for ZKXToken from L1 but has 18 decimals
    f = open(os.path.join(script_dir, rel_path))
    token_contract_json = json.load(f)
    token_contract = eth_test_utils.accounts[0].deploy(token_contract_json)

    postman = Postman(mock_starknet_messaging_contract,
                      starknet_service.starknet)

    await signer1.send_transaction(admin1, registry.contract_address,
                                   'update_contract_registry', [12, 1, int(l1_zkx_contract.address, 16)])
    return (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract,
            token_contract, account_deployer, account_registry)


@pytest.mark.asyncio
async def test_add_asset_positive_flow(adminAuth_factory):
    adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, account_deployer, account_registry = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    add_asset_tx = await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)
    assert_event_emitted(
        add_asset_tx,
        from_address=asset.contract_address,
        name="asset_added",
        data=[
            asset_id,
            admin1.contract_address
        ]
    )

    #following code snippet can be used to inspect exact fields of message being sent by L2 to L1
    #l2_to_l1_messages_log = postman.starknet.state.l2_to_l1_messages_log
    #assert len(l2_to_l1_messages_log) >= postman.n_consumed_l2_to_l1_messages
    #for message in l2_to_l1_messages_log[postman.n_consumed_l2_to_l1_messages:]:
    #    print(message)


    await postman.flush()

    # asset list should be empty
    asset_list = l1_zkx_contract.getAssetList.call()
    assert len(asset_list) == 0

    # no asset_id should exist for this ticker at this point
    stored_asset_id = l1_zkx_contract.assetID.call(asset_id)
    assert stored_asset_id == 0

    # this call only goes through if the message from L2 has reached the message queue
    l1_zkx_contract.updateAssetListInL1.transact(asset_id)

    asset_list = l1_zkx_contract.getAssetList.call()
    assert len(asset_list) == 1
    assert asset_list[0] == asset_id

    stored_asset_id = l1_zkx_contract.assetID.call(asset_id)
    assert stored_asset_id == asset_id


@pytest.mark.asyncio
async def test_add_asset_incorrect_payload(adminAuth_factory):

    adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, account_deployer, account_registry = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)
    
    add_asset_tx = await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)
    assert_event_emitted(
        add_asset_tx,
        from_address=asset.contract_address,
        name="asset_added",
        data=[
            asset_id,
            admin1.contract_address
        ]
    )

    await postman.flush()

    incorrect_ticker = 12345
    incorrect_asset_id = 12345
    stored_asset_id = l1_zkx_contract.assetID.call(incorrect_ticker)
    assert stored_asset_id == 0

    asset_list = l1_zkx_contract.getAssetList.call()
    assert len(asset_list) == 1

    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract.updateAssetListInL1.transact(incorrect_asset_id)
    
    asset_list = l1_zkx_contract.getAssetList.call()
    assert len(asset_list) == 1


@pytest.mark.asyncio
async def test_add_asset_impersonator_ZKX_L1(adminAuth_factory):

    adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, account_deployer, account_registry = adminAuth_factory
    asset_id, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(asset_id, asset_name)

    add_asset_tx = await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)
    assert_event_emitted(
        add_asset_tx,
        from_address=asset.contract_address,
        name="asset_added",
        data=[
            asset_id,
            admin1.contract_address
        ]
    )

    await postman.flush()

    script_dir = os.path.dirname(__file__)
    rel_path = "contract_abi_l1/L1ZKXContract.json"
    f = open(os.path.join(script_dir, rel_path))
    l1_zkx_contract_json = json.load(f)
    l1_zkx_contract_impersonator = eth_test_utils.accounts[0].deploy(l1_zkx_contract_json,
                                                        postman.mock_starknet_messaging_contract.address, 
                                                        asset.contract_address,
                                                        DUMMY_WITHDRAWAL_REQUEST_ADDRESS)
    
    asset_list = l1_zkx_contract.getAssetList.call()
    assert len(asset_list) == 1

    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract_impersonator.updateAssetListInL1.transact(asset_id)

    asset_list = l1_zkx_contract.getAssetList.call()
    assert len(asset_list)==1

    # however a genuine call should go through, proving that message is still there waiting to be consumed despite
    # attempts by malicious contract to consume it

    l1_zkx_contract.updateAssetListInL1.transact(asset_id)

    asset_list = l1_zkx_contract.getAssetList.call()
    assert len(asset_list) == 2
    assert asset_list[1] == asset_id

    stored_asset_id = l1_zkx_contract.assetID.call(asset_id)
    assert stored_asset_id == asset_id
