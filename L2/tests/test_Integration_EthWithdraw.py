import pytest
import asyncio
import json
import os
from starkware.starknet.testing.starknet import Starknet
from starkware.cairo.common.hash_state import compute_hash_on_elements
from utils import Signer, uint, str_to_felt, MAX_UINT256, assert_revert, assert_event_emitted, from64x61, to64x61
from helpers import StarknetService, ContractType, AccountFactory
from starkware.eth.eth_test_utils import EthTestUtils, eth_reverts
from starkware.starknet.testing.contracts import MockStarknetMessaging
from starkware.starknet.services.api.feeder_gateway.response_objects import LATEST_BLOCK_ID
from starkware.starknet.testing.postman import Postman
from starkware.starknet.testing.contract_utils import get_contract_class
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.public.abi import get_selector_from_name
from dummy_addresses import L1_dummy_address
from dummy_signers import signer1, signer2, signer3
from starkware.starkware_utils.error_handling import StarkException
from web3 import Web3

counter = 0
eth_test_utils = EthTestUtils()
# Generates unique asset params (id, ticker and name) to avoid conflicts

DUMMY_WITHDRAWAL_REQUEST_ADDRESS=12345
ETH_TICKER=4543560

def generate_asset_info():
    global counter
    counter += 1
    id = f"32f0406jz7qj8_${counter}"
    ticker = ETH_TICKER
    name = f"Ethereum_${counter}"
    return str_to_felt(id), ticker, str_to_felt(name)



def build_default_asset_properties(id, ticker, name):
    return [
        id,  # id
        0,  # asset_version
        ETH_TICKER,  # ticker
        name,  # short_name
        0,  # tradable
        1,  # collateral
        18,  # token_decimal
        0,  # metadata_id
        1,  # tick_size
        1,  # step_size
        10,  # minimum_order_size
        1,  # minimum_leverage
        5,  # maximum_leverage
        3,  # currently_allowed_leverage
        1,  # maintenance_margin_fraction
        1,  # initial_margin_fraction
        1,  # incremental_initial_margin_fraction
        100,  # incremental_position_size
        1000,  # baseline_position_size
        10000  # maximum_position_size
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
    pubkey = signer3.public_key

    dec_class = await starknet_service.declare(ContractType.AccountManager)

    global class_hash
    class_hash = dec_class.class_hash

    # Deploy infrustructure
    adminAuth = await starknet_service.deploy(ContractType.AdminAuth, [admin1.contract_address, admin2.contract_address])
    registry = await starknet_service.deploy(ContractType.AuthorizedRegistry, [adminAuth.contract_address])
    asset = await starknet_service.deploy(ContractType.Asset, [registry.contract_address, 1])
    withdrawal_fee_balance = await starknet_service.deploy(ContractType.WithdrawalFeeBalance, [registry.contract_address, 1])
    withdrawal_request = await starknet_service.deploy(ContractType.WithdrawalRequest, [registry.contract_address, 1])
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
    
    await signer1.send_transaction(admin1,
                                   registry.contract_address, 'update_contract_registry', [15, 1, withdrawal_fee_balance.contract_address])
    
    await signer1.send_transaction(admin1,
                                   registry.contract_address, 'update_contract_registry', [16, 1, withdrawal_request.contract_address])

    mock_starknet_messaging_contract = eth_test_utils.accounts[0].deploy(
        MockStarknetMessaging, 0)

    script_dir = os.path.dirname(__file__)
    rel_path = "contract_abi_l1/L1ZKXContract.json"
    f = open(os.path.join(script_dir, rel_path))
    l1_zkx_contract_json = json.load(f)
    l1_zkx_contract = eth_test_utils.accounts[0].deploy(l1_zkx_contract_json,
                                                        mock_starknet_messaging_contract.address, 
                                                        asset.contract_address,
                                                        withdrawal_request.contract_address)

    script_dir = os.path.dirname(__file__)
    rel_path = "contract_abi_l1/ZKXToken.json"
    f = open(os.path.join(script_dir, rel_path))
    token_contract_json = json.load(f)

    token_contract = eth_test_utils.accounts[0].deploy(token_contract_json)
    postman = Postman(mock_starknet_messaging_contract,
                      starknet_service.starknet)

    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, int(l1_zkx_contract.address, 16)])

    # adding asset in setup since it is required by all tests
    asset_id, asset_ticker, asset_name = generate_asset_info()
    asset_properties = build_default_asset_properties(
        asset_id, asset_ticker, asset_name)
    add_asset_tx = await signer1.send_transaction(admin1, asset.contract_address, 'add_asset', asset_properties)
    assert_event_emitted(
        add_asset_tx,
        from_address=asset.contract_address,
        name="asset_added",
        data=[
            asset_id,
            asset_ticker,
            admin1.contract_address
        ]
    )
    await postman.flush()
    l1_zkx_contract.updateAssetListInL1.transact(asset_ticker, asset_id)
    
    tx_exec_info = await signer1.send_transaction(admin1,
                                                  account_deployer.contract_address,
                                                  'set_account_class_hash',
                                                  [class_hash])

    tx_exec_info = await signer1.send_transaction(admin1,
                                                  account_deployer.contract_address, 'deploy_account', [pubkey, int(eth_test_utils.accounts[0].address,16)])

    deployed_address = await account_deployer.get_pubkey_L1_to_address(pubkey, int(eth_test_utils.accounts[0].address,16)).call()
    deployed_address=deployed_address.result.address

    await signer1.send_transaction(admin1, withdrawal_fee_balance.contract_address, 'set_standard_withdraw_fee',[
        to64x61(1), # here fee needs to be in not just 64x61 format but also without decimal part which is inferred from asset_id
        asset_id
    ])

    return (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract,
            token_contract, account_deployer, account_registry, asset_ticker, asset_id, deployed_address, withdrawal_request)


@pytest.mark.asyncio
async def test_withdraw_positive_flow(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, asset_ticker, asset_id, deployed_address, withdrawal_request) = adminAuth_factory
    
    balance_zkx_before = l1_zkx_contract.balance
    
    # deposit Eth
    l1_zkx_contract.depositEthToL1.transact(
        deployed_address, transact_args={"value":6*(10**18)})

    balance_zkx_after = l1_zkx_contract.balance
    assert balance_zkx_after == balance_zkx_before + 6*(10**18)


    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    result = await new_account_contract.get_balance(asset_id).call()
    assert result.result.res==0

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    nonce=0
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]
    await postman.flush()
   
    
    # balance should be updated after message is sent to L2 and L1_handler is called
    result = await new_account_contract.get_balance(asset_id).call()
    assert from64x61(result.result.res)==6

    request_id=1
    collateral_id=asset_id
    amount = to64x61(2) # here amount needs to be not just 64x61 but also without decimal part
    withdrawal_request_msg_hash = compute_hash_on_elements([request_id, collateral_id, amount])

    # sign withdrawal request
    signature = signer3.sign(withdrawal_request_msg_hash)

    await signer1.send_transaction(admin1, deployed_address, 'withdraw', [
        request_id, collateral_id, amount, signature[0], signature[1], admin1.contract_address])

    result = await new_account_contract.get_balance(asset_id).call()
    assert from64x61(result.result.res)==3  # previous balance - withdraw amount - fee (1)

    # should not be able to consume/withdraw message before it reaches L1
    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)
    await postman.flush()


    l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)


    # should not be able to consume/withdraw same message twice
    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)
   
    # verify L1_ZKX balance
    balance_zkx_after = l1_zkx_contract.balance
    assert balance_zkx_after == 4*(10**18)

    result = await new_account_contract.get_withdrawal_history().call()
    
    result=result.result.withdrawal_list[0]
    assert result.request_id == request_id
    assert result.collateral_id == asset_id
    assert result.status == 0

    result = await withdrawal_request.get_withdrawal_request_data(request_id).call()
 
    result=result.result.withdrawal_request

    assert result.user_l2_address == deployed_address
    assert result.ticker == asset_ticker
    assert result.amount == 2*(10**18)

    await postman.flush()

    result = await new_account_contract.get_withdrawal_history().call()
   
    result=result.result.withdrawal_list[0]
    assert result.request_id == request_id
    assert result.collateral_id == asset_id
    assert result.status == 1

    result = await withdrawal_request.get_withdrawal_request_data(request_id).call()
    result=result.result.withdrawal_request

    assert result.user_l2_address == 0
    assert result.ticker == 0
    assert result.amount == 0


@pytest.mark.asyncio
async def test_withdraw_incorrect_payload(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, asset_ticker, asset_id, deployed_address, withdrawal_request) = adminAuth_factory

    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    request_id=2
    collateral_id=asset_id
    amount = to64x61(2)
    withdrawal_request_msg_hash = compute_hash_on_elements([request_id, collateral_id, amount])
    signature = signer3.sign(withdrawal_request_msg_hash)

    await signer1.send_transaction(admin1, deployed_address, 'withdraw', [
        request_id, collateral_id, amount, signature[0], signature[1], admin1.contract_address])

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    nonce=0
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]

    await postman.flush()

    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id+2) # incorrect request id
    
    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[1].address, # incorrect user L1 address
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)
   
    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      3*(10**18), # incorrect amount
                                      request_id)

    # this shows that call cannot go through withdraw method even with ETH_TICKER
    # since there is no token address for ETH
    with eth_reverts("Withdrawal failed: token address not set"):
        l1_zkx_contract.withdraw.transact(eth_test_utils.accounts[0].address,
                                      ETH_TICKER, 
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)  
    # correct payload will result in message consumption - proving that message is there waiting to be consumed

    l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)
    await postman.flush()

    balance_zkx_after = l1_zkx_contract.balance
    assert balance_zkx_after == 2*(10**18)
    

@pytest.mark.asyncio
async def test_withdraw_impersonater_ZKX_L1(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, asset_ticker, asset_id, deployed_address, withdrawal_request) = adminAuth_factory

    balance_zkx_before = l1_zkx_contract.balance
    
    l1_zkx_contract.depositEthToL1.transact(
        deployed_address, transact_args={"value":6*(10**18)})

    balance_zkx_after = l1_zkx_contract.balance
    assert balance_zkx_after == balance_zkx_before + 6*(10**18)

    await postman.flush()
    # setting dummy address as L1_ZKX_contract address on L2
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, 12345])
    # eth_test_utils.accounts[0] is the caller for the L1_ZKX_contract function since that is the account that deployed it
    # hence the following call is with the correct and registered combination of <L1 address, L2 address>
    # except that it is through a contract which has been removed as the registered L1_ZKX_contract in L2 authorised
    # registry - this can effectively be any contract impersonating as L1_ZKX_contract on L1
    
    request_id=3
    collateral_id=asset_id
    amount = to64x61(2)
    withdrawal_request_msg_hash = compute_hash_on_elements([request_id, collateral_id, amount])
    signature = signer3.sign(withdrawal_request_msg_hash)

    await signer1.send_transaction(admin1, deployed_address, 'withdraw', [
        request_id, collateral_id, amount, signature[0], signature[1], admin1.contract_address])

    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    result = await new_account_contract.get_balance(asset_id).call()
    assert from64x61(result.result.res)==3

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    
    nonce=None
    message_event=None
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]
        message_event=event
    
    await postman.flush()


    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        # l1_zkx_address was not the intended recipient of this message since the L1_ZKX_address was changed on L2
        # prior to sending this message to L1
        l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)
    
    # directly calling update_withdrawal_request in Withdraw_Request contract should revert unless from_address is
    # authorised L1_ZKX_address
    await assert_revert(postman.starknet.send_message_to_l2(
        int(eth_test_utils.accounts[0].address, 16), # this is not authorised L1_ZKX_address
        withdrawal_request.contract_address,
        get_selector_from_name('update_withdrawal_request'),
        [3],
        0,
        nonce
    ), "WithdrawalRequest: L1 contract mismatch")

    # restoring L1_ZKX_address on L2
    await signer1.send_transaction(admin1, registry.contract_address, 'update_contract_registry', [12, 1, int(l1_zkx_contract.address, 16)])


    


@pytest.mark.asyncio
async def test_withdraw_positive_flow_sponsored(adminAuth_factory):
    (adminAuth, registry, asset, admin1, admin2, postman, l1_zkx_contract, token_contract, 
    account_deployer, account_registry, asset_ticker, asset_id, deployed_address, withdrawal_request) = adminAuth_factory
    

    balance_zkx_before = l1_zkx_contract.balance
    
    l1_zkx_contract.depositEthToL1.transact(
        deployed_address, transact_args={"value":6*(10**18)})

    balance_zkx_after = l1_zkx_contract.balance
    assert balance_zkx_after == balance_zkx_before + 6*(10**18)
    

    abi = get_contract_class(
        source="tests/testable/TestAccountManager.cairo").abi
    new_account_contract = StarknetContract(state=account_registry.state,
                                            abi=abi,
                                            contract_address=deployed_address,
                                            deploy_call_info=None)

    result = await new_account_contract.get_balance(asset_id).call()
    assert from64x61(result.result.res)==3

    message_to_l2_filter = postman.mock_starknet_messaging_contract.w3_contract.events.LogMessageToL2.createFilter(
            fromBlock=LATEST_BLOCK_ID
        )
    nonce=0
    for event in message_to_l2_filter.get_all_entries():
        nonce=event.args["nonce"]
    await postman.flush()
   
    
    # balance should be updated after message is sent to L2 and L1_handler is called
    result = await new_account_contract.get_balance(asset_id).call()
    assert from64x61(result.result.res)==9
    request_id=4
    collateral_id=asset_id
    amount = to64x61(2) # here amount needs to be not just 64x61 but also without decimal part
    withdrawal_request_msg_hash = compute_hash_on_elements([request_id, collateral_id, amount])
    signature = signer3.sign(withdrawal_request_msg_hash)

    await signer1.send_transaction(admin1, deployed_address, 'withdraw', [
        request_id, collateral_id, amount, signature[0], signature[1], admin1.contract_address])

    result = await new_account_contract.get_balance(asset_id).call()
    assert from64x61(result.result.res)==6  # previous balance - withdraw amount - fee (1)

    await postman.flush()

    balance_user_before = eth_test_utils.accounts[0].balance
    balance_zkx_before = l1_zkx_contract.balance
    # call from a different L1 address should go through as long as correct user_L1 address is given as the argument
    l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id, transact_args={"from":eth_test_utils.accounts[1]})
    # balance should increase by 2 since that is the amount that was withdrawn

    balance_user_after =eth_test_utils.accounts[0].balance
    assert balance_user_after == balance_user_before + 2*(10**18)

    # verify L1_ZKX balance
    balance_zkx_after = l1_zkx_contract.balance
    assert balance_zkx_after == balance_zkx_before - 2*(10**18)
    
    # should not be able to consume/withdraw same message twice
    with eth_reverts("INVALID_MESSAGE_TO_CONSUME"):
        l1_zkx_contract.withdrawEth.transact(eth_test_utils.accounts[0].address,
                                      2*(10**18), # here amount is being given as uint256 not as 64x61 value
                                      request_id)
