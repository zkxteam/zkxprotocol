"""Utilities for testing Cairo contracts."""

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.signature import private_to_stark_key, sign
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.public.abi import get_selector_from_name
from math import trunc

MAX_UINT256 = (2**128 - 1, 2**128 - 1)

SCALE = 2**61
PRIME = 3618502788666131213697322783095070105623107215331596699973092056135872020481
PRIME_HALF = PRIME/2
PI = 7244019458077122842

def from64x61(num):
    res = num
    if num > PRIME_HALF:
        res = res - PRIME
    return res / SCALE

def to64x61(num):
    res = num * SCALE
    if res > 2**125 or res <= -2*125:
        raise Exception("Number is out of valid range")
    return trunc(res)


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

    def sign(self, message_hash):
        return sign(msg_hash=message_hash, priv_key=self.private_key)

    async def send_transaction(self, account, to, selector_name, calldata, nonce=None):
        if nonce is None:
            execution_info = await account.get_nonce().call()
            nonce, = execution_info.result

        selector = get_selector_from_name(selector_name)
        message_hash = hash_message(
            account.contract_address, to, selector, calldata, nonce)
        sig_r, sig_s = self.sign(message_hash)

        return await account.execute(to, selector, calldata, nonce).invoke(signature=[sig_r, sig_s])


def hash_message(sender, to, selector, calldata, nonce):
    message = [
        sender,
        to,
        selector,
        compute_hash_on_elements(calldata),
        nonce
    ]
    return compute_hash_on_elements(message)


def hash_order(order_id, ticker, collateral, price, orderType, position, direction, closeOrder, leverage):
    order = [ 
        order_id,
        ticker,
        collateral,
        price,
        orderType,
        position,
        direction,
        closeOrder,
        leverage
    ]
    return compute_hash_on_elements(order)


def convertList(res_list):
    conv_list = list(map(lambda x: from64x61(x), res_list[1:7]))
    conv_list.append(res_list[0])
    conv_list.append(res_list[7])

    return conv_list

to64x61(0)