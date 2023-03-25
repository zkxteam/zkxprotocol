import pytest
import asyncio
import json
import os
from starkware.starknet.testing.starknet import Starknet
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, assert_event_emitted, from64x61
from utils_asset import build_default_asset_properties
from helpers import StarknetService, ContractType, AccountFactory
from starkware.eth.eth_test_utils import EthTestUtils, eth_reverts
from starkware.starknet.testing.contracts import MockStarknetMessaging
from starkware.starknet.services.api.feeder_gateway.response_objects import LATEST_BLOCK_ID
from starkware.starknet.testing.postman import Postman
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import StarknetContract
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3
from web3 import Web3

counter = 0
eth_test_utils = EthTestUtils()
ETH_ID = 4543560
ETH_NAME = str_to_felt("ETH")
DUMMY_WITHDRAWAL_REQUEST_ADDRESS=12345
collateral_id=7788

def generate_asset_info():
    global counter
    counter += 1
    id = f"32f0406jz7qj8_${counter}"
    name = f"Ethereum_${counter}"
    return str_to_felt(id), str_to_felt(name)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def adminAuth_factory(starknet_service: StarknetService):

    # Deploy accounts
    account_factory = AccountFactory(starknet_service, L1_dummy_address, 0, 1)
    admin1 = await account_factory.deploy_account(signer1.public_key)
    admin2 = await account_factory.deploy_account(signer2.public_key)
    pubkey = signer3.public_key

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
    rel_path = "contract_abi_l1/ZKXToken.json"
    f = open(os.path.join(script_dir, rel_path))
    token_contract_json = json.load(f)

    token_contract = eth_test_utils.accounts[0].deploy(token_contract_json)
    postman = Postman(mock_starknet_messaging_contract,
                      starknet_service.starknet)

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, int(l1_zkx_contract.address, 16)])

    asset_properties = build_default_asset_properties(id=ETH_ID, short_name=ETH_NAME)
    add_asset_tx = await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)
    assert_event_emitted(
        add_asset_tx,
        from_address=asset.contract_address,
        name="asset_added",
        data=[
            ETH_ID,
            admin1.contract_address
        ]
    )
    await postman.flush()
    l1_zkx_contract.updateAssetListInL1.transact(ETH_ID)
    
    tx_exec_info = await signer1.send_transaction(admin1,
                                                  account_deployer.contract_address,
                                                  'set_account_class_hash',
                                                  [class_hash])

    tx_exec_info = await signer1.send_transaction(admin1,
                                                  account_deployer.contract_address, 'deploy_account', [pubkey, int(eth_test_utils.accounts[0].address,16), collateral_id])

    deployed_address = await account_deployer.get_pubkey_L1_to_address(pubkey, int(eth_test_utils.accounts[0].address,16)).call()
    deployed_address=deployed_address.result.address
    return (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract,
            token_contract, account_deployer, account_registry, deployed_address)


@pytest.mark.asyncio
async def test_deposit_positive_flow(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, deployed_address) = adminAuth_factory

    balance_before = l1_zkx_contract.balance

    l1_zkx_contract.depositEthToL1.transact(
        deployed_address,transact_args={"value":2*(10**18)})
    
    balance_after = l1_zkx_contract.balance

    assert balance_after == balance_before + 2*(10**18)
    
    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    result = await new_account_contract.get_balance(ETH_ID).call()
    assert result.result.res==0

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    nonce=0
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]

    # call l1_handler (deposit) on L2
    await postman.flush()

    result = await new_account_contract.get_balance(ETH_ID).call()
    assert from64x61(result.result.res)==2

    # cannot cancel a message which has been successfully consumed on L2
    with eth_reverts("NO_MESSAGE_TO_CANCEL"):
        l1_zkx_contract.depositCancelRequest(
            deployed_address,
            ETH_ID,
            2*(10**18),
            nonce
        )



@pytest.mark.asyncio
async def test_deposit_incorrect_L2_address(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, deployed_address) = adminAuth_factory

    incorrect_L2_address=12345

   
    balance_before = l1_zkx_contract.balance
    
    l1_zkx_contract.depositEthToL1.transact(
        incorrect_L2_address,transact_args={"value":2*(10**18)})
    
    balance_after = l1_zkx_contract.balance

    assert balance_after == balance_before + 2*(10**18)
    
    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    result = await new_account_contract.get_balance(ETH_ID).call()
    assert from64x61(result.result.res) == 2

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    nonce=0
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]

    # this should revert since it will call l1_handler on L2 and that function will revert
    await assert_revert(postman.flush())


    result = await new_account_contract.get_balance(ETH_ID).call()
    assert from64x61(result.result.res) == 2

    # check that message cancellation should go through since message was not consumed on L2
    l1_zkx_contract.depositCancelRequest.transact(
            incorrect_L2_address,
            ETH_ID,
            2*(10**18),
            nonce
        )

    # check that appropriate log message was emitted with correct details
    deposit_cancellation_filter = l1_zkx_contract.w3_contract.events.LogDepositCancelRequest.createFilter(
        fromBlock=LATEST_BLOCK_ID
    )
    message_cancel_event=None
    for event in deposit_cancellation_filter.get_all_entries():
        message_cancel_event=event
    
    assert message_cancel_event.args["sender"]==eth_test_utils.accounts[0].address
    assert message_cancel_event.args["l2Recipient"]==incorrect_L2_address
    assert message_cancel_event.args["assetId"]==ETH_ID
    assert message_cancel_event.args["amount"]==2*(10**18)
    assert message_cancel_event.args["nonce"]==nonce


@pytest.mark.asyncio
async def test_deposit_impersonater_ZKX_L1(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, deployed_address) = adminAuth_factory

    incorrect_L2_address=12345

    # setting dummy address as L1_ZKX_contract address on L2
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, 12345])
    # eth_test_utils.accounts[0] is the caller for the L1_ZKX_contract function since that is the account that deployed it
    # hence the following call is with the correct and registered combination of <L1 address, L2 address>
    # except that it is through a contract which has been removed as the registered L1_ZKX_contract in L2 authorised
    # registry - this can effectively be any contract impersonating as L1_ZKX_contract on L1
    # to be sure no token transfer needs to take place for an impersonating contract to send message to L2 to increase balance
    l1_zkx_contract.depositEthToL1.transact(
        deployed_address, transact_args={"value":1*(10**18)})
    
    

    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    result = await new_account_contract.get_balance(ETH_ID).call()
    assert from64x61(result.result.res)==2

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    
    nonce=None
    message_event=None
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]
        message_event=event
    
    # this should revert since it will call l1_handler on L2 and that function will revert
    await assert_revert(postman.flush())


    result = await new_account_contract.get_balance(ETH_ID).call()
    assert from64x61(result.result.res)==2

    deposit_filter = l1_zkx_contract.w3_contract.events.LogDeposit.createFilter(
        fromBlock=LATEST_BLOCK_ID
    )
    message_deposit_event=None
    for event in deposit_filter.get_all_entries():
        message_deposit_event=event
        

    msg_hash = message_deposit_event.args["msgHash"]

    # check that msg hash still is available in starknet core waiting to be consumed
    msg_count = postman.mock_starknet_messaging_contract.l1ToL2Messages.call(msg_hash)
    
    assert msg_count > 0
    
    



@pytest.mark.asyncio
async def test_deposit_incorrect_L1_address(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, deployed_address) = adminAuth_factory

    # restore correct L1_ZKX_Contract address in authorised registry on L2
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, int(l1_zkx_contract.address, 16)])
    

    l1_zkx_contract.depositEthToL1.transact(
        deployed_address, transact_args={"value":2*(10**18), "from":eth_test_utils.accounts[1]})
    
   
    
    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    result = await new_account_contract.get_balance(ETH_ID).call()
    assert from64x61(result.result.res)==2

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    nonce=0
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]

    # this should revert since it will call l1_handler on L2 and that function will revert
    await assert_revert(postman.flush())

    result = await new_account_contract.get_balance(ETH_ID).call()
    assert from64x61(result.result.res)==2

    # check that message cancellation should go through since message was not consumed on L2
    l1_zkx_contract.depositCancelRequest.transact(
            deployed_address,
            ETH_ID,
            2*(10**18),
            nonce
        ,transact_args={"from":eth_test_utils.accounts[1]})

    deposit_cancellation_filter = l1_zkx_contract.w3_contract.events.LogDepositCancelRequest.createFilter(
        fromBlock=LATEST_BLOCK_ID
    )
    message_cancel_event=None
    for event in deposit_cancellation_filter.get_all_entries():
        message_cancel_event=event
    
    assert message_cancel_event.args["sender"]==eth_test_utils.accounts[1].address
    assert message_cancel_event.args["l2Recipient"]==deployed_address
    assert message_cancel_event.args["assetId"]==ETH_ID
    assert message_cancel_event.args["amount"]==2*(10**18)
    assert message_cancel_event.args["nonce"]==nonce


