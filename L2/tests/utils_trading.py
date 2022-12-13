from utils_asset import AssetID
from utils import str_to_felt, Signer, to64x61, hash_order
import random
import string

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")


def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


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

fund_mapping = {
    "liquidity_fund": 1,
    "fee_balance": 2,
    "holding_fund": 3,
    "insurance_fund": 4
}

fund_mode = {
    "fund": 1,
    "defund": 0
}

market_to_asset_mapping = {
    BTC_USD_ID: AssetID.USDC,
    ETH_USD_ID: AssetID.USDC,
    TSLA_USD_ID: AssetID.USDC
}


class OrderExecutor:
    def __init__(self):
        self.maker_trading_fees = 0.0002 * 0.97
        self.taker_trading_fees = 0.0005 * 0.97
        self.fund_balances = {}

    def set_fund_balance(self, fund, asset_id, new_balance):
        self.fund_balances[fund] = {
            asset_id: new_balance
        }

    def get_fund_balance(self, fund, asset_id):
        try:
            return self.fund_balances[fund][asset_id]
        except KeyError:
            return 0

    def modify_fund_balance(self, fund, mode, asset_id, amount):
        current_balance = self.get_fund_balance(fund, asset_id,)
        new_balance = 0

        if mode == fund_mode["fund"]:
            new_balance = current_balance + amount
        else:
            new_balance = current_balance - amount

        self.set_fund_balance(fund, asset_id, new_balance)

    def process_open_orders(self, user, order, execution_price, order_size, market_id):
        average_execution_price = 0
        margin_amount = 0
        borrowed_amount = 0

        fee_rate = self.get_fee(
            user=user, side=order["side"])

        position = user.get_position(
            market_id=order["market_id"], direction=order["direction"])

        # The position size is 0 or
        if position["position_size"] == 0:
            # If the position size is 0, the average execution price is the execution price
            average_execution_price = execution_price
        else:
            # Find the total value of the existing position
            total_position_value = position["position_size"] * \
                position["avg_execution_price"]
            # Find the value of the incoming order
            incoming_order_value = order_size*execution_price
            # Find the cumalatice size and value
            cumulative_position_size = position["position_size"] + order_size
            cumulative_position_value = total_position_value + incoming_order_value

            # Calculate the new average execution price of the position
            average_execution_price = cumulative_position_value/cumulative_position_size
        # Order value with leverage
        leveraged_position_value = order_size * execution_price
        # Order value wo leverage
        order_value_wo_leverage = leveraged_position_value / \
            order["leverage"]

        # Amount that needs to be borrowed
        amount_to_be_borrowed = leveraged_position_value - order_value_wo_leverage

        # Update the current margin and borrowed amounts
        margin_amount += order_value_wo_leverage
        borrowed_amount += amount_to_be_borrowed

        # Calculate the fee for the order
        fees = fee_rate*leveraged_position_value

        # Balance that the user must stake/pay
        balance_to_be_deducted = order_value_wo_leverage + fees

        # Get position details of the user
        user_balance = user.get_balance(
            asset_id=market_to_asset_mapping[order["market_id"]],
        )

        if user_balance <= balance_to_be_deducted:
            print("Low balance")

        user.modify_balance(
            mode=fund_mode["defund"], asset_id=market_to_asset_mapping[order["market_id"]], amount=balance_to_be_deducted)
        self.modify_fund_balance(fund=fund_mapping["fee_balance"], mode=fund_mode["fund"],
                                 asset_id=market_to_asset_mapping[order["market_id"]], amount=fees)
        self.modify_fund_balance(fund=fund_mapping["holding_fund"], mode=fund_mode["fund"],
                                 asset_id=market_to_asset_mapping[order["market_id"]], amount=leveraged_position_value)

        if order["leverage"] > 1:
            self.modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["defund"],
                                     asset_id=market_to_asset_mapping[order["market_id"]], amount=amount_to_be_borrowed)

        return (average_execution_price, margin_amount, borrowed_amount)

    def process_close_orders(self, user, order, execution_price, order_size, market_id):
        average_execution_price = 0
        margin_amount = 0
        borrowed_amount = 0

        current_direction = order_direction["short"] if order[
            "direction"] == order_direction["long"] else order_direction["long"]

        # Get the user position
        position = user.get_position(order["market_id"], current_direction)
        assert position["position_size"] >= 0, "The parentPosition size cannot be 0"

        # Values to be populated for position object
        margin_amount = position["margin_amount"]
        borrowed_amount = position["borrowed_amount"]
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
        pnl = order_size * diff
        # Value of the position after factoring in the pnl
        net_account_value = margin_amount + pnl

        # Value of asset at current price w leverage
        leveraged_amount_out = order_size * actual_execution_price

        if position["position_size"] == 0:
            return (0, 0, 0)
        # Calculate the amount that needs to be returned to the user
        percent_of_position = order_size / \
            position["position_size"]
        borrowed_amount_to_be_returned = borrowed_amount*percent_of_position
        margin_amount_to_be_reduced = margin_amount*percent_of_position

        self.modify_fund_balance(fund=fund_mapping["holding_fund"], mode=fund_mode["defund"],
                                 asset_id=market_to_asset_mapping[order["market_id"]], amount=leveraged_amount_out)

        if order["order_type"] == 4:
            borrowed_amount = borrowed_amount - leveraged_amount_out
        else:
            borrowed_amount -= borrowed_amount_to_be_returned
            margin_amount -= margin_amount_to_be_reduced

        if order["order_type"] <= 3:
            if position["leverage"] > 1:
                self.modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                         asset_id=market_to_asset_mapping[order["market_id"]], amount=borrowed_amount_to_be_returned)
            if net_account_value <= 0:
                deficit = leveraged_amount_out - borrowed_amount_to_be_returned
                user.modify_balance(
                    mode=fund_mode["defund"], asset_id=market_to_asset_mapping[order["market_id"]], amount=deficit)
            else:
                amount_to_transfer_from = leveraged_amount_out - borrowed_amount_to_be_returned
                user.modify_balance(
                    mode=fund_mode["fund"], asset_id=market_to_asset_mapping[order["market_id"]], amount=amount_to_transfer_from)
        else:
            if order["order_type"] == 4:
                self.modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                         asset_id=market_to_asset_mapping[order["market_id"]], amount=borrowed_amount_to_be_returned)
                if net_account_value <= 0:
                    deficit = min(0, net_account_value)

                    # Get position details of the user
                    user_balance = user.get_balance(
                        asset_id=market_to_asset_mapping[order["market_id"]],
                    )

                    if deficit <= user_balance:
                        user.modify_balance(
                            mode=fund_mode["defund"], asset_id=market_to_asset_mapping[order["market_id"]], amount=deficit)
                    else:
                        user.modify_balance(
                            mode=fund_mode["defund"], asset_id=market_to_asset_mapping[order["market_id"]], amount=user_balance)
                        self.modify_fund_balance(fund=fund_mapping["insurance_fund"], mode=fund_mode["defund"],
                                                 asset_id=market_to_asset_mapping[order["market_id"]], amount=deficit - user_balance)
            else:
                self.modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                         asset_id=market_to_asset_mapping[order["market_id"]], amount=leveraged_amount_out)

        return (average_execution_price, margin_amount, borrowed_amount)

    def get_fee(self, user, side):
        # ToDo change this logic when we add user discounts
        # Fee rate
        return self.maker_trading_fees if side == 1 else self.taker_trading_fees

    def execute_batch(self, request_list, user_list, quantity_locked=1, market_id=str_to_felt("BTC-USDC"), oracle_price=1000):
        # Store the quantity executed so far
        running_weighted_sum = 0
        quantity_executed = 0

        for i in range(len(request_list)):
            quantity_remaining = quantity_locked - quantity_executed
            quantity_to_execute = 0
            execution_price = 0
            margin_amount = 0
            borrowed_amount = 0
            avg_execution_price = 0
            if quantity_remaining == 0:
                if request_list[i]["side"] != order_side["taker"]:
                    print("Taker order must come afer Maker orders")

                if request_list[i]["post_only"] != 0:
                    print("Post Only order cannot be a taker")

                if i != len(request_list) - 1:
                    print("Maker order must be the last order in the list")

                if request_list[i]["time_in_force"] == 2:
                    if request_list[i]["quantity"] != quantity_locked:
                        print("F&K must be executed fully")

                quantity_to_execute = quantity_locked
                execution_price = running_weighted_sum/quantity_locked
            else:
                if request_list[i]["side"] != order_side["maker"]:
                    print("Maker orders must come before Taker order")

                if quantity_remaining < request_list[i]["quantity"]:
                    quantity_to_execute = quantity_remaining

                    if request_list[i]["time_in_force"] == 2:
                        print("F&K should be executed fully")
                else:
                    quantity_to_execute = request_list[i]["quantity"]

                quantity_executed += quantity_to_execute
                execution_price = request_list[i]["price"]

                running_weighted_sum += execution_price*quantity_to_execute

            if request_list[i]["close_order"] == 1:
                (avg_execution_price, margin_amount, borrowed_amount) = self.process_open_orders(
                    user=user_list[i], order=request_list[i], execution_price=execution_price, order_size=quantity_to_execute, market_id=market_id)
            else:
                (avg_execution_price, margin_amount, borrowed_amount) = self.process_close_orders(
                    user=user_list[i], order=request_list[i], execution_price=execution_price, order_size=quantity_to_execute, market_id=market_id)

                if avg_execution_price == 0:
                    return
            user_list[i].execute_order(order=request_list[i], size=quantity_to_execute, price=avg_execution_price,
                                       margin_amount=margin_amount, borrowed_amount=borrowed_amount, market_id=market_id)

        return


class User:
    def __init__(self, private_key, user_address):
        self.signer = Signer(private_key)
        self.user_address = user_address
        self.orders = {}
        self.orders_decimal = {}
        self.balance = {}
        self.portion_executed = {}
        self.positions = {}
        self.market_array = []

    def get_portion_executed(self, order_id):
        try:
            return self.portion_executed[order_id]
        except KeyError:
            return 0

    def set_portion_executed(self, order_id, new_amount):
        self.portion_executed[order_id] = new_amount

    def modify_balance(self, mode, asset_id, amount):
        current_balance = self.get_balance(asset_id=asset_id)
        new_balance = 0

        if mode == fund_mode["fund"]:
            new_balance = current_balance + amount
        else:
            new_balance = current_balance - amount
        self.set_balance(new_balance=new_balance, asset_id=asset_id)

    def set_balance(self, new_balance, asset_id=str_to_felt("USDC")):
        self.balance[asset_id] = new_balance

    def add_to_market_array(self, new_market_id):
        for i in range(len(self.market_array)):
            if self.market_array[i] == new_market_id:
                return
        self.market_array.append(new_market_id)

    def remove_from_market_array(self, market_id):
        if len(self.market_array) == 1:
            self.market_array.pop()
        for i in range(len(self.market_array)):
            if self.market_array[i] == market_id:
                self.market_array[i] = self.market_array[len(
                    self.market_array) - 1]
                self.market_array.pop()
                return

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

    def execute_order(self, order, size, price, margin_amount, borrowed_amount, market_id):

        position = self.get_position(
            market_id=order["market_id"], direction=order["direction"])
        order_portion_executed = self.get_portion_executed(
            order_id=order["order_id"])
        new_portion_executed = order_portion_executed + size

        new_portion_executed <= order["quantity"], "New position size larger than order"

        self.set_portion_executed(
            order_id=order["order_id"], new_amount=new_portion_executed)

        if order["close_order"] == 1:
            if position["position_size"] == 0:
                self.add_to_market_array(new_market_id=order["market_id"])

            new_position_size = position["position_size"] + size

            total_value = margin_amount + borrowed_amount
            new_leverage = total_value/margin_amount

            updated_position = {
                "avg_execution_price": price,
                "position_size": new_position_size,
                "margin_amount": margin_amount,
                "borrowed_amount": borrowed_amount,
                "leverage": new_leverage
            }

            self.positions[order["market_id"]] = {
                order["direction"]: updated_position
            }

        else:
            parent_direction = order_direction["short"] if order[
                "direction"] == order_direction["long"] else order_direction["long"]

            parent_position = self.get_position(
                market_id=order["market_id"], direction=parent_direction)

            new_position_size = parent_position["position_size"] - size

            assert new_position_size >= 0, "Cannot close more thant the positionSize"

            if new_position_size == 0:
                if position["position_size"] == 0:
                    self.remove_from_market_array(market_id=market_id)

            new_leverage = parent_position["leverage"]
            updated_position = {
                "avg_execution_price": price,
                "position_size": new_position_size,
                "margin_amount": margin_amount,
                "borrowed_amount": borrowed_amount,
                "leverage": new_leverage
            }

            self.positions[order["market_id"]] = {
                parent_direction: updated_position
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

    def get_order(self, order_id):
        python_order = self.orders_decimal[order_id]
        starknet_order = self.orders[order_id]
        return (python_order, starknet_order)

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

    def convert_order_to_64x61(self, order):
        modified_order = {
            "order_id": order["order_id"],
            "market_id": order["market_id"],
            "direction": order["direction"],
            "price": to64x61(order["price"]),
            "quantity": to64x61(order["quantity"]),
            "leverage": to64x61(order["leverage"]),
            "slippage": to64x61(order["slippage"]),
            "order_type": order["order_type"],
            "time_in_force": order["time_in_force"],
            "post_only": order["post_only"],
            "close_order": order["close_order"],
            "liquidator_address": order["liquidator_address"]
        }

        return modified_order

    def create_order_starknet(self, order, liquidator_address, side):
        signed_order = self.get_signed_order(order)
        multiple_order_format_64x61 = self.get_multiple_order_representation(
            order, signed_order, liquidator_address, side)

        self.orders[order["order_id"]] = multiple_order_format_64x61

        return multiple_order_format_64x61

    def create_order(
        self,
        market_id=BTC_USD_ID,
        direction=order_direction["long"],
        price=1000,
        quantity=1,
        leverage=1,
        slippage=0,
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
        signed_order = [0, 0]
        multiple_order_format = self.get_multiple_order_representation(
            new_order, signed_order, liquidator_address, side)

        self.orders_decimal[new_order["order_id"]] = multiple_order_format

        # Convert to 64x61 format for starknet
        order_64x61 = self.convert_order_to_64x61(new_order)
        multiple_order_format_64x61 = self.create_order_starknet(
            order_64x61, liquidator_address, side)
        return (multiple_order_format, multiple_order_format_64x61)


alice = User(123456, "0x123234324")
bob = User(73879, "0x1234589402")
alice.set_balance(10000, AssetID.USDC)
bob.set_balance(10000, AssetID.USDC)
executoor = OrderExecutor()
orders = [{
    "quantity": 3
}, {
    "quantity": 3,
    "direction": order_direction["short"],
    "side": order_side["taker"]
}]
# execute_and_compare(executoor, orders, [alice, bob], 1, BTC_USD_ID, 10000)
# # order_long = alice.create_order_decimals(
#     quantity=1, leverage=1)
# order_short = alice.create_order_decimals(
#     quantity=1, direction=order_direction["short"], side=order_side["taker"])

# print("Alice..", order_long)
# print("Bob...", order_short)
# request_list = [order_long, order_short]


# executoor.execute_batch(
#     request_list, [alice, bob], 1, BTC_USD_ID, 1000)
# print("alice_position:", alice.get_position(
#     market_id=BTC_USD_ID, direction=1))
# print("bob_position:", bob.get_position(
#     market_id=BTC_USD_ID, direction=2))
# print(alice.get_balance(AssetID.USDC))
# print(bob.get_balance(AssetID.USDC))
# print(executoor.get_fund_balance(
#     fund_mapping["holding_fund"], asset_id=AssetID.USDC))
# print(executoor.get_fund_balance(
#     fund_mapping["insurance_fund"], asset_id=AssetID.USDC))
# print(executoor.get_fund_balance(
#     fund_mapping["liquidity_fund"], asset_id=AssetID.USDC))

# order_short = alice.create_order_decimals(
#     quantity=1, direction=order_direction["short"], leverage=1, close_order=close_order["close"])
# order_long = alice.create_order_decimals(
#     quantity=1, side=order_side["taker"], close_order=close_order["close"])
# request_list = [order_short, order_long]

# executoor = OrderExecutor()
# executoor.execute_batch(
#     request_list, [alice, bob], 1, AssetID.USDC, 1000)
# print(alice.get_balance(AssetID.USDC))
# print(bob.get_balance(AssetID.USDC))
# multiple_order_long = MultipleOrder(*order_long)
# multiple_order_short = MultipleOrder(*order_short)
# print(multiple_order_long.get_multiple_order())
# print(multiple_order_short.get_multiple_order())
