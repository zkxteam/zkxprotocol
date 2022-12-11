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
import random
import string

MAX_UINT256 = (2**128 - 1, 2**128 - 1)

SCALE = 2**61
PRIME = 3618502788666131213697322783095070105623107215331596699973092056135872020481
PRIME_HALF = PRIME/2
PI = 7244019458077122842
TRANSACTION_VERSION = 1


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


def felt_to_str(felt):
    b_felt = felt.to_bytes(31, "big")
    return b_felt.decode()


def uint(a):
    return (a, 0)


async def assert_revert(fun, reverted_with=None):
    try:
        await fun
        assert False
    except StarkException as err:
        _, error = err.args
        if reverted_with is not None:
            assert reverted_with in error['message']


def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


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


async def assert_revert(fun, reverted_with=None):
    try:
        await fun
        assert False
    except StarkException as err:
        _, error = err.args
        if reverted_with is not None:
            assert reverted_with in error['message']

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


def build_default_asset_properties(
    id,
    ticker,
    short_name,
    asset_version=1,
    tradable=0,
    collateral=0,
    token_decimal=18,
    metadata_id=0,
    tick_size=to64x61(0.01),
    step_size=to64x61(0.1),
    minimum_order_size=to64x61(1),
    minimum_leverage=to64x61(1),
    maximum_leverage=to64x61(10),
    currently_allowed_leverage=to64x61(3),
    maintenance_margin_fraction=to64x61(1),
    initial_margin_fraction=to64x61(1),
    incremental_initial_margin_fraction=to64x61(1),
    incremental_position_size=to64x61(100),
    baseline_position_size=to64x61(1000),
    maximum_position_size=to64x61(10000)
):
    return [
        id,
        asset_version,
        ticker,
        short_name,
        tradable,
        collateral,
        token_decimal,
        metadata_id,
        tick_size,
        step_size,
        minimum_order_size,
        minimum_leverage,
        maximum_leverage,
        currently_allowed_leverage,
        maintenance_margin_fraction,
        initial_margin_fraction,
        incremental_initial_margin_fraction,
        incremental_position_size,
        baseline_position_size,
        maximum_position_size
    ]


def build_asset_properties(
    id,
    asset_version,
    ticker,
    short_name,
    tradable,
    collateral,
    token_decimal,
    metadata_id,
    tick_size,
    step_size,
    minimum_order_size,
    minimum_leverage,
    maximum_leverage,
    currently_allowed_leverage,
    maintenance_margin_fraction,
    initial_margin_fraction,
    incremental_initial_margin_fraction,
    incremental_position_size,
    baseline_position_size,
    maximum_position_size
):
    return [
        id,
        asset_version,
        ticker,
        short_name,
        tradable,
        collateral,
        token_decimal,
        metadata_id,
        tick_size,
        step_size,
        minimum_order_size,
        minimum_leverage,
        maximum_leverage,
        currently_allowed_leverage,
        maintenance_margin_fraction,
        initial_margin_fraction,
        incremental_initial_margin_fraction,
        incremental_position_size,
        baseline_position_size,
        maximum_position_size
    ]


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


order_types = {
    "market": 1,
    "limit": 2
}

order_direction = {
    "long": 1,
    "short": 2,
}

order_time_in_force = {
    "good_till_time": 1,
    "fill_or_kill": 2,
    "immediate_or_cancel": 3,
}

order_side = {
    "maker": 1,
    "taker": 2
}

close_order = {
    "open": 1,
    "close": 2
}


class OrderExecutor:
    def __init__(self):
        self.maker_trading_fees = 0.0002 * 0.97
        self.taker_trading_fees = 0.0005 * 0.97

    def execute_batch_new(self, request_list, user_list, quantity_locked=1, market_id=str_to_felt("BTC-USDC"), oracle_price=1000):
        return

    def execute_batch(self, request_list, user_list, quantity_locked=1, market_id=str_to_felt("BTC-USDC"), oracle_price=1000):
        # Store the quantity executed so far
        quantity_executed = 0
        weighted_execution_price = 0

        # For each order iterate
        for i in range(len(request_list)):
            # Portion that'll be executed in the current order
            portion_being_executed = 0
            # Get the portion executed for the current order_id
            current_portion_executed = user_list[i].get_portion_executed(
                request_list[i]["order_id"])

            # Portion that is remaining to be executed
            portion_remaining = request_list[i]["quantity"] - \
                current_portion_executed

            # If the order is fully executed, assert error
            assert portion_remaining >= 0, "Order already executed"

            # Fee rate
            fee_rate = self.maker_trading_fees if request_list[
                i]["side"] == 1 else self.taker_trading_fees
            # If it's a maker order

            # Execution Price
            execution_price = 0
            if request_list[i]["side"] == order_side["maker"]:
                execution_price = request_list[i]["price"]
                portion_that_can_be_executed = quantity_locked - quantity_executed
                portion_being_executed = min(
                    portion_that_can_be_executed, portion_remaining)

                quantity_executed += portion_being_executed
                weighted_execution_price = portion_being_executed * execution_price
            # If it's a taker order
            else:
                execution_price = weighted_execution_price/quantity_locked
                print("Execution Price", execution_price,
                      quantity_locked, weighted_execution_price)
                assert portion_remaining <= quantity_executed, "Invalid batch passed"
                portion_being_executed = quantity_executed

            user_list[i].execute_order(
                request_list[i], execution_price, portion_being_executed, fee_rate)


class User:
    def __init__(self, private_key, user_address):
        self.signer = Signer(private_key)
        self.user_address = user_address
        self.orders = {}
        self.orders_decimal = {}
        self.balance = {}
        self.portion_executed = {}
        self.positions = {}

    def get_portion_executed(self, order_id):
        try:
            return self.portion_executed[order_id]
        except KeyError:
            return 0

    def set_balance(self, new_balance, asset_id=str_to_felt("USDC")):
        self.balance[asset_id] = new_balance

    def get_balance(self, asset_id=str_to_felt("USDC")):
        try:
            return self.balance[asset_id]
        except KeyError:
            return 0

    def charge_user(self, amount, asset_id=str_to_felt("USDC")):
        try:
            self.balance[asset_id] -= amount
        except KeyError:
            return 0

    def execute_order(self, order, execution_price, portion_being_executed, fee_rate):
        # Required direction
        current_direction = order["direction"] if order["close_order"] == 0 else abs(
            order["direction"] - 1)
        # Get the user position
        position = self.get_position(order["market_id"], order["direction"])
        print(position)

        # Values to be populated for position object
        average_execution_price = 0
        current_margin_amount = position["margin_amount"]
        current_position_size = position["position_size"]
        current_borrowed_amount = position["borrowed_amount"]
        current_leverage = 0

        # If it's an open order
        if order["close_order"] == 0:
            # The position size is 0 or
            if position["position_size"] == 0:
                # If the position size is 0, the average execution price is the execution price
                average_execution_price = execution_price
            else:
                # Find the total value of the existing position
                total_position_value = position["position_size"] * \
                    position["avg_execution_price"]
                # Find the value of the incoming order
                incoming_order_value = portion_being_executed*execution_price
                # Find the cumalatice size and value
                cumulative_position_size = position["position_size"] + \
                    portion_being_executed
                cumulative_position_value = total_position_value + incoming_order_value

                # Calculate the new average execution price of the position
                average_execution_price = cumulative_position_value/cumulative_position_size
            # Order value with leverage
            leveraged_position_value = portion_being_executed * execution_price
            # Order value wo leverage
            order_value_wo_leverage = leveraged_position_value / \
                order["leverage"]

            # Amount that needs to be borrowed
            amount_to_be_borrowed = leveraged_position_value - order_value_wo_leverage

            # Update the current margin and borrowed amounts
            current_margin_amount += order_value_wo_leverage
            current_borrowed_amount += amount_to_be_borrowed

            # Calculate the fee for the order
            fees = fee_rate*leveraged_position_value

            # Balance that the user must stake/pay
            balance_to_be_deducted = order_value_wo_leverage + fees

            # Get the new leverage
            current_leverage = (current_margin_amount +
                                current_borrowed_amount)/current_margin_amount

            # Deduct balance from user
            self.charge_user(balance_to_be_deducted)
        # For closing orders
        else:
            assert position["position_size"] >= 0, "The parentPosition size cannot be 0"
            current_margin_amount = position["margin_amount"]
            current_borrowed_amount = position["borrowed_amount"]
            average_execution_price = position["avg_execution_price"]

            # Diff is the difference between average execution price and current price
            diff = 0
            # Using 2*avg_execution_price - execution_price to simplify the calculations
            actual_execution_price = 0
            # Current order is short order
            if order["direction"] == 1:
                # Actual execution price is same as execution price
                actual_execution_price = execution_price
                diff = execution_price - position["avg_execution_price"]
            else:
                diff = position["avg_execution_price"] - execution_price
                # Actual execution price is 2*avg_execution_price - execution_price
                actual_execution_price = position["avg_execution_price"] + diff

            # Calculate the profit and loss for the user
            pnl = portion_being_executed * diff
            # Value of the position after factoring in the pnl
            net_account_value = current_margin_amount + pnl

            # Value of asset at current price w leverage
            leveraged_amount_out = portion_being_executed * actual_execution_price

            # Calculate the amount that needs to be returned to the user
            percent_of_position = portion_being_executed / \
                position["position_size"]
            borrowed_amount_to_be_returned = current_borrowed_amount*percent_of_position
            margin_amount_to_be_reduced = current_margin_amount*percent_of_position

            # If it's a deleveraging_order
            if order["order_type"] == 4:
                current_borrowed_amount -= leveraged_amount_out
            else:
                current_borrowed_amount -= borrowed_amount_to_be_returned
                current_margin_amount -= margin_amount_to_be_reduced

            # Transfer funds
        updated_position = {
            "avg_execution_price": average_execution_price,
            "position_size": (current_position_size + portion_being_executed) if order["close_order"] == 0 else (current_position_size - portion_being_executed),
            "margin_amount": current_margin_amount,
            "borrowed_amount": current_borrowed_amount,
            "leverage": current_leverage
        }

        self.positions[order["market_id"]] = {
            current_direction: updated_position
        }

    def get_position(self, market_id=str_to_felt("BTC-USDC"), direction=order_direction["long"]):
        try:
            return self.positions[market_id][direction]
        except KeyError:
            return {
                "avg_execution_price": 0,
                "position_size": 0,
                "margin_amount": 0,
                "borrowed_amount": 0,
                "leverage": 0
            }

    def get_signed_order(self, order):
        hashed_order = hash_order(list(order.values())[:-1])
        return self.signer.sign(hashed_order)

    def get_multiple_order_representation(self, order, signed_order, liquidator_address, side):
        multiple_order = {
            "user_address": self.user_address,
            "sig_r": signed_order[0],
            "sig_s": signed_order[1],
            "side": side,
            "liquidator_address": liquidator_address,
            "order_id": order["order_id"],
            "market_id": order["market_id"],
            "direction": order["direction"],
            "price": order["price"],
            "quantity": order["quantity"],
            "leverage": order["leverage"],
            "slippage": order["slippage"],
            "order_type": order["order_type"],
            "time_in_force": order["time_in_force"],
            "post_only": order["post_only"],
            "close_order": order["close_order"],
        }

        return multiple_order

    def create_order(
        self,
        market_id=str_to_felt("BTC-USDC"),
        direction=order_direction["long"],
        price=to64x61(1000),
        quantity=to64x61(1),
        leverage=to64x61(1),
        slippage=to64x61(0),
        order_type=order_types["market"],
        time_in_force=order_time_in_force["good_till_time"],
        post_only=0,
        close_order=close_order["open"],
        liquidator_address=0,
        side=order_side["maker"]
    ):
        # Checks for input
        assert price > 0, "Invalid price"
        assert quantity > 0, "Invalid quantity"
        assert slippage >= 0, "Invalid slippage"
        assert direction in order_direction.values(), "Invalid direction"
        assert order_type in order_types.values(), "Invalid order_type"
        assert time_in_force in order_time_in_force.values(), "Invalid time_in_force"
        assert post_only in (0, 1), "Invalid post_only"
        assert close_order in (1, 2), "Invalid close_order"

        new_order = {
            "order_id": str_to_felt(random_string(12)),
            "market_id": market_id,
            "direction": direction,
            "price": price,
            "quantity": quantity,
            "leverage": leverage,
            "slippage": slippage,
            "order_type": order_type,
            "time_in_force": time_in_force,
            "post_only": post_only,
            "close_order": close_order,
            "liquidator_address": liquidator_address
        }

        signed_order = self.get_signed_order(new_order)
        multiple_order_format = self.get_multiple_order_representation(
            new_order, signed_order, liquidator_address, side)

        self.orders[new_order["order_id"]] = multiple_order_format
        return multiple_order_format

    def create_order_decimals(
        self,
        market_id=str_to_felt("BTC-USDC"),
        direction=order_direction["long"],
        price=1000,
        quantity=1,
        leverage=1,
        slippage=0,
        order_type=order_types["market"],
        time_in_force=order_time_in_force["good_till_time"],
        post_only=0,
        close_order=0,
        liquidator_address=0,
        side=order_side["maker"]
    ):
        # Checks for input
        assert price > 0, "Invalid price"
        assert quantity > 0, "Invalid quantity"
        assert slippage >= 0, "Invalid slippage"
        assert direction in order_direction.values(), "Invalid direction"
        assert order_type in order_types.values(), "Invalid order_type"
        assert time_in_force in order_time_in_force.values(), "Invalid time_in_force"
        assert post_only in (0, 1), "Invalid post_only"
        assert close_order in (0, 1), "Invalid close_order"

        new_order = {
            "order_id": str_to_felt(random_string(12)),
            "market_id": market_id,
            "direction": direction,
            "price": price,
            "quantity": quantity,
            "leverage": leverage,
            "slippage": slippage,
            "order_type": order_type,
            "time_in_force": time_in_force,
            "post_only": post_only,
            "close_order": close_order,
            "liquidator_address": liquidator_address
        }

        signed_order = self.get_signed_order(new_order)
        multiple_order_format = self.get_multiple_order_representation(
            new_order, signed_order, liquidator_address, side)

        self.orders_decimal[new_order["order_id"]] = multiple_order_format
        return multiple_order_format


# alice = User(123456, "0x123234324")
# bob = User(73879, "0x1234589402")
# order_long = alice.create_order_decimals(
#     quantity=3, leverage=10)
# order_short = alice.create_order_decimals(
#     quantity=3, direction=order_direction["short"], side=order_side["taker"])

# print("Alice..", order_long)
# print("Bob...", order_short)
# request_list = [order_long, order_short]

# alice.set_balance(100, str_to_felt("USDC"))
# print(alice.get_balance(str_to_felt("USDC")))

# executoor = OrderExecutor()
# executoor.execute_batch(
#     request_list, [alice, bob], 3, str_to_felt("BTC-USDC"), 1000)
# print("/n")
# executoor.execute_batch(
#     request_list, [alice, bob], 3, str_to_felt("BTC-USDC"), 1000)
# position_alice = alice.get_position(
#     str_to_felt("BTC-USDC"), order_direction["long"])
# position_bob = bob.get_position(
#     str_to_felt("BTC-USDC"), order_direction["short"])
# print(position_alice)
# print(position_bob)
# print(to64x61(100))
# # multiple_order_long = MultipleOrder(*order_long)
# multiple_order_short = MultipleOrder(*order_short)
# print(multiple_order_long.get_multiple_order())
# print(multiple_order_short.get_multiple_order())
