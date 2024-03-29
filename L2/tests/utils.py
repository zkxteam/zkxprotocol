"""Utilities for testing Cairo contracts."""

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.signature import private_to_stark_key, sign
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.definitions.general_config import StarknetChainId
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.gateway.transaction import InvokeFunction
from starkware.starknet.business_logic.transaction.objects import InternalTransaction, TransactionExecutionInfo, InternalDeclare
from math import trunc
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_transaction_hash_common,
    calculate_declare_transaction_hash
)

from starkware.starknet.business_logic.execution.objects import OrderedEvent

MAX_UINT256 = (2**128 - 1, 2**128 - 1)

SCALE = 2**61
PRIME = 3618502788666131213697322783095070105623107215331596699973092056135872020481
PRIME_HALF = PRIME/2
PI = 7244019458077122842
TRANSACTION_VERSION = 1


class ContractIndex:
    AdminAuth = 0
    Asset = 1
    Market = 2
    FeeDiscount = 3
    TradingFees = 4
    Trading = 5
    FeeBalance = 6
    Holding = 7
    EmergencyFund = 8
    LiquidityFund = 9
    InsuranceFund = 10
    Liquidate = 11
    L1_ZKX_Address = 12
    CollateralPrices = 13
    AccountRegistry = 14
    WithdrawalFeeBalance = 15
    WithdrawalRequest = 16
    ABRCalculations = 17
    ABRFund = 18
    ABRPayment = 19
    AccountDeployer = 20
    MarketPrices = 21
    PubkeyWhitelister = 22
    SigRequirementsManager = 23
    Hightide = 24
    TradingStats = 25
    UserStats = 26
    Starkway = 27
    Settings = 28
    ABRCore = 31


class ManagerAction:
    MasterAdmin = 0
    ManageAssets = 1
    ManageMarkets = 2
    ManageAuthRegistry = 3
    ManageFeeDetails = 4
    ManageFunds = 5
    ManageGovernanceToken = 6
    ManageCollateralPrices = 7
    ManageHighTide = 8
    ManageSettings = 9


def from64x61(num: int) -> int:
    res = num
    if num > PRIME_HALF:
        res = res - PRIME
    return res / SCALE


def to64x61(num: int) -> int:
    res = num * SCALE
    if res > 2**125 or res <= -2**125:
        raise Exception("Number is out of valid range")
    return trunc(res)


def convertTo64x61(nums):
    result = []
    for n in nums:
        result.append(to64x61(n))
    return result


def str_to_felt(text: str) -> int:
    b_text = text.encode('utf8', 'strict')
    return int.from_bytes(b_text, "big")


def felt_to_str(felt: int) -> str:
    b_felt = felt.to_bytes(31, "big")
    return b_felt.decode('utf8', 'strict')


def uint(a):
    return (a, 0)


async def assert_revert(fun, reverted_with=None):
    try:
        await fun
        assert False, f"Call didn't revert, expected: {reverted_with}"
    except StarkException as err:
        _, error = err.args
        if reverted_with is not None:
            assert reverted_with in error[
                'message'], f"Error mismatch, expected: {reverted_with}, actual: {error['message']}"


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

        build_calls = []
        for call in calls:
            build_call = list(call)
            build_call[0] = hex(build_call[0])
            build_calls.append(build_call)

        raw_invocation = get_raw_invoke(account, build_calls)
        state = raw_invocation.state

        if nonce is None:
            nonce = await state.state.get_nonce_at(account.contract_address)

        (call_array, calldata, sig_r, sig_s) = self.sign_transaction(
            hex(account.contract_address), build_calls, nonce, max_fee)

        # temp = account.__execute__(call_array, calldata, nonce)
        external_tx = InvokeFunction(
            contract_address=account.contract_address,
            calldata=raw_invocation.calldata,
            entry_point_selector=None,
            signature=[sig_r, sig_s],
            max_fee=max_fee,
            version=TRANSACTION_VERSION,
            nonce=nonce,
        )

        self.current_hash = external_tx.calculate_hash(state.general_config)
        tx = InternalTransaction.from_external(
            external_tx=external_tx, general_config=state.general_config
        )
        execution_info = await state.execute_tx(tx=tx)
        return execution_info
        """self.current_hash = calculate_transaction_hash_common(
            TransactionHashPrefix.INVOKE,
            1,  # version
            account.contract_address,  # to
            get_selector_from_name('__execute__'),  # entry_point
            temp.calldata,  # calldata
            0,  # maxfee
            1536727068981429685321,  # chainid
            [],
        )
        return await account.__execute__(call_array, calldata, nonce).invoke(signature=[sig_r, sig_s])"""

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


def hash_order(order_details):
    return compute_hash_on_elements(order_details)


# following event assertion functions directly from oz test utils


def assert_event_emitted(tx_exec_info, from_address, name, data=[], order=0):
    """Assert one single event is fired with correct data."""
    assert_events_emitted(tx_exec_info, [(order, from_address, name, data)])


def assert_events_emitted(tx_exec_info, events):
    """Assert events are fired with correct data."""
    for event in events:
        order, from_address, name, data = event
        event_obj = OrderedEvent(
            order=order,
            keys=[get_selector_from_name(name)],
            data=data,
        )

        base = tx_exec_info.call_info.internal_calls[0]
        if event_obj in base.events and from_address == base.contract_address:
            return

        try:
            base2 = base.internal_calls[0]
            if event_obj in base2.events and from_address == base2.contract_address:
                return
        except IndexError:
            pass

        raise BaseException("Event not fired or not fired correctly")


def assert_event_with_custom_keys_emitted(tx_exec_info, from_address, keys, data, order=0):
    assert_events_with_custom_keys_emitted(
        tx_exec_info, [(order, from_address, keys, data)])


def assert_events_with_custom_keys_emitted(tx_exec_info, events):
    """Assert events are fired with correct data."""
    for event in events:
        order, from_address, keys, data = event
        event_obj = OrderedEvent(
            order=order,
            keys=keys,
            data=data,
        )

        base = tx_exec_info.call_info.internal_calls[0]
        if event_obj in base.events and from_address == base.contract_address:
            return

        try:
            base2 = base.internal_calls[0]
            if event_obj in base2.events and from_address == base2.contract_address:
                return
        except IndexError:
            pass

        raise BaseException("Event not fired or not fired correctly")


def from_call_to_call_array(calls):
    """Transform from Call to CallArray."""
    call_array = []
    calldata = []
    for _, call in enumerate(calls):
        expected_length = 3
        assert len(
            call) == expected_length, f"Invalid parameters length, expected: {expected_length}, actual: {len(call)}"
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
    ]

    return calculate_transaction_hash_common(
        TransactionHashPrefix.INVOKE,
        TRANSACTION_VERSION,
        account,
        0,
        execute_calldata,
        max_fee,
        StarknetChainId.TESTNET.value,
        [nonce],
    )


def get_raw_invoke(sender, calls):
    """Return raw invoke, remove when test framework supports `invoke`."""
    call_array, calldata = from_call_to_call_array(calls)
    raw_invocation = sender.__execute__(call_array, calldata)
    return raw_invocation


def print_parsed_positions(pos_array):
    for i in range(len(pos_array)):
        print("position #", i)
        print("market_id: ", felt_to_str(pos_array[i].market_id))
        print("direction: ", pos_array[i].direction)
        print("execution price: ", from64x61(pos_array[i].avg_execution_price))
        print("position size: ", from64x61(pos_array[i].position_size))
        print("margin: ", from64x61(pos_array[i].margin_amount))
        print("borrowed: ", from64x61(pos_array[i].borrowed_amount))
        print("leverage: ", from64x61(pos_array[i].leverage))
        print("\n")


def print_parsed_collaterals(coll_array):
    for i in range(len(coll_array)):
        print("collateral #", i)
        print("collateral_id: ", felt_to_str(coll_array[i].assetID))
        print("balance: ", from64x61(coll_array[i].balance))
        print("\n")
