"""Utilities for testing Cairo contracts."""

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.signature import private_to_stark_key, sign
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.definitions.general_config import StarknetChainId
from starkware.starknet.public.abi import get_selector_from_name
from math import trunc
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_transaction_hash_common,
)
from starkware.starknet.business_logic.execution.objects import Event

MAX_UINT256 = (2**128 - 1, 2**128 - 1)

SCALE = 2**61
PRIME = 3618502788666131213697322783095070105623107215331596699973092056135872020481
PRIME_HALF = PRIME/2
PI = 7244019458077122842
TRANSACTION_VERSION=0

def from64x61(num):
    res = num
    if num > PRIME_HALF:
        res = res - PRIME
    return res / SCALE


def to64x61(num):
    res = num * SCALE
    if res > 2**125 or res <= -2**125:
        raise Exception("Number is out of valid range")
    return trunc(res)

def convertTo64x61(nums):
    result = []
    for n in nums:
        result.append(to64x61(n))
    return result

def str_to_felt(text):
    b_text = bytes(text, 'UTF-8')
    return int.from_bytes(b_text, "big")


def uint(a):
    return(a, 0)


async def assert_revert(fun):
    try:
        await fun
        assert False
    except StarkException as err:
        _, error = err.args
        assert error['code'] == StarknetErrorCode.TRANSACTION_FAILED


class Signer():
    """
    Utility for sending signed transactions to an Account on Starknet.

    Parameters
    ----------

    private_key : int

    Examples
    ---------
    Constructing a Singer object

    >>> signer = Signer(1234)

    Sending a transaction

    >>> await signer.send_transaction(account, 
                                      account.contract_address, 
                                      'set_public_key', 
                                      [other.public_key]
                                     )

    """

    def __init__(self, private_key):
        self.private_key = private_key
        self.public_key = private_to_stark_key(private_key)
        self.current_hash = 0

    def sign(self, message_hash):
        return sign(msg_hash=message_hash, priv_key=self.private_key)


    async def send_transactions(self, account, calls, nonce=None, max_fee=0):
        if nonce is None:
            execution_info = await account.get_nonce().call()
            nonce, = execution_info.result

        build_calls = []
        for call in calls:
            build_call = list(call)
            build_call[0] = hex(build_call[0])
            build_calls.append(build_call)

        (call_array, calldata, sig_r, sig_s) = self.sign_transaction(
            hex(account.contract_address), build_calls, nonce, max_fee)

        temp = account.__execute__(call_array, calldata, nonce)
        self.current_hash = calculate_transaction_hash_common(
            TransactionHashPrefix.INVOKE,
            0,  # version
            account.contract_address,  # to
            get_selector_from_name('__execute__'),  # entry_point
            temp.calldata,  # calldata
            0,  # maxfee
            1536727068981429685321,  # chainid
            [],
        )
        return await account.__execute__(call_array, calldata, nonce).invoke(signature=[sig_r, sig_s])

    async def send_transaction(self, account, to, selector_name, calldata, nonce=None, max_fee=0):
        return await self.send_transactions(account, [(to, selector_name, calldata)], nonce, max_fee)
        
    def sign_transaction(self, sender, calls, nonce, max_fee):
        """Sign a transaction for an Account."""
        (call_array, calldata) = from_call_to_call_array(calls)
        message_hash = get_transaction_hash(
            int(sender, 16), call_array, calldata, nonce, int(max_fee)
        )
        sig_r, sig_s = self.sign(message_hash)
        return (call_array, calldata, sig_r, sig_s)

def hash_message(sender, to, selector, calldata, nonce):
    message = [
        sender,
        to,
        selector,
        compute_hash_on_elements(calldata),
        nonce
    ]
    return compute_hash_on_elements(message)


def hash_order(order_id, ticker, collateral, price, stopPrice, orderType, position, direction, closeOrder, leverage):
    order = [
        order_id,
        ticker,
        collateral,
        price,
        stopPrice,
        orderType,
        position,
        direction,
        closeOrder,
        leverage
    ]
    return compute_hash_on_elements(order)


async def assert_revert(fun, reverted_with=None):
    try:
        await fun
        assert False
    except StarkException as err:
        _, error = err.args
        if reverted_with is not None:
            assert reverted_with in error['message']

def assert_event_emitted(tx_exec_info, from_address, name, data):
    assert Event(
        from_address=from_address,
        keys=[get_selector_from_name(name)],
        data=data,
    ) in tx_exec_info.raw_events


def from_call_to_call_array(calls):
    """Transform from Call to CallArray."""
    call_array = []
    calldata = []
    for _, call in enumerate(calls):
        assert len(call) == 3, "Invalid call parameters"
        entry = (
            int(call[0], 16),
            get_selector_from_name(call[1]),
            len(calldata),
            len(call[2]),
        )
        call_array.append(entry)
        calldata.extend(call[2])
    return (call_array, calldata)


def get_transaction_hash(account, call_array, calldata, nonce, max_fee):
    """Calculate the transaction hash."""
    execute_calldata = [
        len(call_array),
        *[x for t in call_array for x in t],
        len(calldata),
        *calldata,
        nonce,
    ]

    return calculate_transaction_hash_common(
        TransactionHashPrefix.INVOKE,
        TRANSACTION_VERSION,
        account,
        get_selector_from_name("__execute__"),
        execute_calldata,
        max_fee,
        StarknetChainId.TESTNET.value,
        [],
    )

def print_position_array(position_array):
    """Helper function to print out the positions"""
    for position in position_array:
        print("Market: ", position[0])
        print("Direction: ", "long" if position[1] == 1 else "short")
        print("Avg Execution Price: ", from64x61(position[2]))
        print("Position Size: ", from64x61(position[3]))
        print("Margin Amount: ", from64x61(position[4]))
        print("Borrowed Amount: ", from64x61(position[5]))
        print("\n")

def print_collaterals_array(collateral_array):
    """Helper function to print out the collaterals"""
    for collateral in collateral_array:
        print("Asset: ", collateral[0])
        print("Balance: ", from64x61(collateral[1]))
        print("\n")

def felt_to_str(felt):
    b_felt = felt.to_bytes(31, "big")
    return b_felt.decode()

