import pytest
import copy
import random
import string
from utils_asset import AssetID
from utils import Signer, str_to_felt, assert_revert, hash_order, from64x61, to64x61
from typing import List, Dict, Tuple
from starkware.starknet.testing.contract import StarknetContract

# Market IDs
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")


# To get random order_ids and batch_ids
def random_string(length):
    return str_to_felt(''.join(random.choices(string.ascii_letters + string.digits, k=length)))


# Constants related to trading objects
order_types = {
    "market": 1,
    "limit": 2,
    "stop": 3,
    "liquidation": 4,
    "deleverage": 5
}


order_side = {
    "maker": 1,
    "taker": 2
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


order_life_cycles = {
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


market_to_collateral_mapping = {
    BTC_USD_ID: AssetID.USDC,
    ETH_USD_ID: AssetID.USDC,
    TSLA_USD_ID: AssetID.USDC
}

market_to_asset_mapping = {
    BTC_USD_ID: AssetID.BTC,
    ETH_USD_ID: AssetID.ETH,
    TSLA_USD_ID: AssetID.TSLA
}

#################
#### Classes ####
#################


# Emulates AccountManager Contract in python
class User:
    def __init__(self, private_key: int, user_address: int, liquidator_private_key: int = 0):
        self.signer = Signer(private_key)
        self.user_address = user_address
        self.orders = {}
        self.orders_decimal = {}
        self.balance = {}
        self.portion_executed = {}
        self.positions = {}
        self.market_array = []
        self.collateral_array = []
        self.deleveragable_or_liquidatable_position = {}
        self.liquidator_private_key = liquidator_private_key

    def __convert_order_to_64x61(self, order: Dict):
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
            "life_cycle": order["life_cycle"],
            "liquidator_address": order["liquidator_address"]
        }

        return modified_order

    def __create_order_starknet(self, order: int, liquidator_address: int) -> Dict:
        signed_order = self.__get_signed_order(order, liquidator_address)
        multiple_order_format_64x61 = self.__get_multiple_order_representation(
            order, signed_order, liquidator_address)
        self.orders[order["order_id"]] = multiple_order_format_64x61
        return multiple_order_format_64x61

    def __set_portion_executed(self, order_id: int, new_amount: float):
        self.portion_executed[order_id] = new_amount

    def __add_to_market_array(self, new_market_id: int):
        for i in range(len(self.market_array)):
            if self.market_array[i] == new_market_id:
                return
        self.market_array.append(new_market_id)

    def __remove_from_market_array(self, market_id: int):
        if len(self.market_array) == 1:
            self.market_array.pop()
        for i in range(len(self.market_array)):
            if self.market_array[i] == market_id:
                self.market_array[i] = self.market_array[len(
                    self.market_array) - 1]
                self.market_array.pop()
                return

    def __get_signed_order(self, order: Dict, liquidator_address: int) -> Dict:
        hashed_order = hash_order(list(order.values())[:-1])
        if liquidator_address == 0:
            return self.signer.sign(hashed_order)
        else:
            liquidator = Signer(self.liquidator_private_key)
            return liquidator.sign(hashed_order)

    def __get_multiple_order_representation(self, order: int, signed_order: int, liquidator_address: int) -> Dict:
        multiple_order = {
            "user_address": self.user_address,
            "sig_r": signed_order[0],
            "sig_s": signed_order[1],
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
            "life_cycle": order["life_cycle"],
        }

        return multiple_order

    def __update_position(self, market_id: int, direction: int, updated_dict: Dict, updated_position: Dict):
        try:
            self.positions[market_id].update(updated_dict)
        except KeyError:
            self.positions[market_id] = {
                direction: updated_position
            }

    def get_positions(self) -> List[Dict]:
        markets = self.market_array
        positions = []
        for i in range(len(markets)):
            long_position = self.get_position(
                market_id=markets[i], direction=order_direction["long"])
            short_position = self.get_position(
                market_id=markets[i], direction=order_direction["short"])

            if long_position["position_size"] != 0:
                long_position["market_id"] = markets[i]
                long_position["direction"] = order_direction["long"]
                positions.append(long_position)

            if short_position["position_size"] != 0:
                short_position["market_id"] = markets[i]
                short_position["direction"] = order_direction["short"]
                positions.append(short_position)
        return positions

    def get_collaterals(self) -> List[Dict]:
        collateral_array = self.collateral_array
        collateral_array_with_balances = []
        for i in range(len(collateral_array)):
            current_collateral_balance = self.get_balance(
                asset_id=collateral_array[i])

            collateral_array_with_balances.append({
                "asset_id":  collateral_array[i],
                "balance": current_collateral_balance
            })
        return collateral_array_with_balances

    def get_portion_executed(self, order_id: int) -> float:
        try:
            return self.portion_executed[order_id]
        except KeyError:
            return 0

    def modify_balance(self, mode: int, asset_id: int, amount: float):
        current_balance = self.get_balance(asset_id=asset_id)
        new_balance = 0

        if mode == fund_mode["fund"]:
            new_balance = current_balance + amount
        else:
            new_balance = current_balance - amount
        self.set_balance(new_balance=new_balance, asset_id=asset_id)

    def set_balance(self, new_balance: float, asset_id: int = AssetID.USDC):
        self.balance[asset_id] = new_balance
        collaterals = self.collateral_array

        is_present = 0
        for i in range(len(collaterals)):
            if asset_id == collaterals[i]:
                is_present = 1

        if not is_present:
            self.collateral_array.append(asset_id)

    def get_balance(self, asset_id: int = AssetID.USDC) -> float:
        try:
            return self.balance[asset_id]
        except KeyError:
            return 0

    def get_deleveragable_or_liquidatable_position(self) -> Dict:
        if self.deleveragable_or_liquidatable_position != {}:
            return self.deleveragable_or_liquidatable_position
        else:
            return {
                "market_id": 0,
                "direction": 0,
                "amount_to_be_sold": 0,
                "liquidatable": 0
            }

    def set_deleveragable_or_liquidatable_position(self, updated_position: Dict):
        self.deleveragable_or_liquidatable_position = updated_position

    def liquidate_position(self, position: Dict, amount_to_be_sold: float):
        amount = 0
        liquidatable = 0
        if amount_to_be_sold == 0:
            amount = position["position_size"]
            liquidatable = 1
        else:
            amount = amount_to_be_sold
            liquidatable = 0
        liquidatable_position = {
            "market_id": position["market_id"],
            "direction": position["direction"],
            "amount_to_be_sold": amount,
            "liquidatable": liquidatable
        }
        self.deleveragable_or_liquidatable_position = liquidatable_position

    def execute_order(self, order: Dict, size: float, price: float, margin_amount: float, borrowed_amount: float, market_id: int):

        position = self.get_position(
            market_id=order["market_id"], direction=order["direction"])
        order_portion_executed = self.get_portion_executed(
            order_id=order["order_id"])
        new_portion_executed = order_portion_executed + size
        if new_portion_executed > order["quantity"]:
            print("New position size larger than order")
            return

        if order["time_in_force"] == order_time_in_force["immediate_or_cancel"]:
            new_portion_executed = order["quantity"]

        self.__set_portion_executed(
            order_id=order["order_id"], new_amount=new_portion_executed)

        if order["life_cycle"] == 1:
            if position["position_size"] == 0:
                self.__add_to_market_array(new_market_id=order["market_id"])

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

            updated_dict = {
                order["direction"]: updated_position,
            }

            self.__update_position(
                market_id=order["market_id"], direction=order["direction"], updated_dict=updated_dict, updated_position=updated_position)

        else:
            parent_direction = order_direction["short"] if order[
                "direction"] == order_direction["long"] else order_direction["long"]

            parent_position = self.get_position(
                market_id=order["market_id"], direction=parent_direction)

            new_position_size = parent_position["position_size"] - size

            if new_position_size < 0:
                print("Cannot close more thant the positionSize")
                return

            if new_position_size == 0:
                if position["position_size"] == 0:
                    self.__remove_from_market_array(market_id=market_id)

            new_leverage = 0

            if order["order_type"] > 3:
                liq_position = self.get_deleveragable_or_liquidatable_position()

                if liq_position["market_id"] != market_id:
                    print("Position not marked as liquidatable/deleveragable")
                    return ()

                if size > liq_position["amount_to_be_sold"]:
                    print("Order size larger than marked one")
                    return ()

                updated_amount = liq_position["amount_to_be_sold"] - size

                liq_position["amount_to_be_sold"] = updated_amount
                self.set_deleveragable_or_liquidatable_position(
                    updated_position=liq_position)

                if order["order_type"] == order_types["deleverage"]:
                    if liq_position["liquidatable"] == 1:
                        print("AccountManager: Position not marked as deleveragable")
                        return ()
                    total_value = margin_amount + borrowed_amount
                    leverage = total_value/margin_amount
                    new_leverage = leverage
                else:
                    if liq_position["liquidatable"] == 0:
                        print("AccountManager: Position not marked as deleveragable")
                        return ()
                    new_leverage = parent_position["leverage"]
            else:
                new_leverage = parent_position["leverage"]

            updated_position = {
                "avg_execution_price": price,
                "position_size": new_position_size,
                "margin_amount": margin_amount,
                "borrowed_amount": borrowed_amount,
                "leverage": new_leverage
            }

            updated_dict = {
                parent_direction: updated_position,
            }

            self.__update_position(
                market_id=order["market_id"], direction=parent_direction, updated_dict=updated_dict, updated_position=updated_position)

    def get_position(self, market_id: int = BTC_USD_ID, direction: int = order_direction["long"]) -> Dict:
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

    # Get orders stored in python and starknet formats
    def get_order(self, order_id: int) -> Tuple[Dict, Dict]:
        try:
            python_order = self.orders_decimal[order_id]
            starknet_order = self.orders[order_id]
            return (python_order, starknet_order)
        except KeyError:
            return ({}, {})

    def create_order(
        self,
        order_id: int = 0,
        market_id: int = BTC_USD_ID,
        direction: int = order_direction["long"],
        price: float = 1000,
        quantity: float = 1,
        leverage: float = 1,
        slippage: float = 5,
        order_type: int = order_types["market"],
        time_in_force: int = order_time_in_force["good_till_time"],
        post_only: int = 0,
        life_cycle: int = order_life_cycles["open"],
        liquidator_address: int = 0,
    ) -> Tuple[Dict, Dict]:
        # Checks for input
        assert price > 0, "Invalid price"
        assert quantity > 0, "Invalid quantity"
        assert slippage >= 0, "Invalid slippage"
        assert direction in order_direction.values(), "Invalid direction"
        assert order_type in order_types.values(), "Invalid order_type"
        assert time_in_force in order_time_in_force.values(), "Invalid time_in_force"
        assert post_only in (0, 1), "Invalid post_only"
        assert life_cycle in (1, 2), "Invalid life_cycle"

        new_order = {
            "order_id": order_id if order_id else random_string(12),
            "market_id": market_id,
            "direction": direction,
            "price": price,
            "quantity": quantity,
            "leverage": leverage,
            "slippage": slippage,
            "order_type": order_type,
            "time_in_force": time_in_force,
            "post_only": post_only,
            "life_cycle": life_cycle,
            "liquidator_address": liquidator_address
        }
        # Signed order for python implementation
        signed_order = [0, 0]
        # Convert the order to multiple order format
        multiple_order_format = self.__get_multiple_order_representation(
            new_order, signed_order, liquidator_address)
        # Store the multiple order format to orders_decimal list
        self.orders_decimal[new_order["order_id"]] = multiple_order_format

        # Convert to 64x61 format for starknet
        order_64x61 = self.__convert_order_to_64x61(new_order)
        # Convert the order to multiple order format
        multiple_order_format_64x61 = self.__create_order_starknet(
            order_64x61, liquidator_address)
        return (multiple_order_format, multiple_order_format_64x61)


# Emulates Trading Contract in python
class OrderExecutor:
    def __init__(self):
        self.maker_trading_fees = 0.0002 * 0.97
        self.taker_trading_fees = 0.0005 * 0.97
        self.fund_balances = {}
        self.batch_id_status = {}

    def __modify_fund_balance(self, fund: int, mode: int, asset_id: int, amount: float):
        current_balance = self.get_fund_balance(fund, asset_id,)
        new_balance = 0

        if mode == fund_mode["fund"]:
            new_balance = current_balance + amount
        else:
            new_balance = current_balance - amount

        self.set_fund_balance(fund, asset_id, new_balance)

    def __process_open_orders(self, user: User, order: Dict, execution_price: float, order_size: float, side: int, market_id: int) -> Tuple[float, float, float]:
        position = user.get_position(
            market_id=order["market_id"], direction=order["direction"])

        average_execution_price = 0
        margin_amount = position["margin_amount"]
        borrowed_amount = position["borrowed_amount"]

        fee_rate = self.__get_fee(
            user=user, side=side)

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
            asset_id=market_to_collateral_mapping[order["market_id"]],
        )

        if user_balance <= balance_to_be_deducted:
            print("Low balance", balance_to_be_deducted, user_balance)
            return (0, 0, 0)

        user.modify_balance(
            mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=balance_to_be_deducted)
        self.__modify_fund_balance(fund=fund_mapping["fee_balance"], mode=fund_mode["fund"],
                                   asset_id=market_to_collateral_mapping[order["market_id"]], amount=fees)
        self.__modify_fund_balance(fund=fund_mapping["holding_fund"], mode=fund_mode["fund"],
                                   asset_id=market_to_collateral_mapping[order["market_id"]], amount=leveraged_position_value)

        if order["leverage"] > 1:
            self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["defund"],
                                       asset_id=market_to_collateral_mapping[order["market_id"]], amount=amount_to_be_borrowed)

        return (average_execution_price, margin_amount, borrowed_amount)

    def __process_close_orders(self, user: User, order: Dict, execution_price: float, order_size: float, market_id) -> Tuple[float, float, float]:
        current_direction = order_direction["short"] if order[
            "direction"] == order_direction["long"] else order_direction["long"]

        # Get the user position
        position = user.get_position(order["market_id"], current_direction)
        if position["position_size"] == 0:
            print("The parentPosition size cannot be 0")
            return (0, 0, 0)

        # Values to be populated for position object
        margin_amount = position["margin_amount"]
        borrowed_amount = position["borrowed_amount"]
        average_execution_price = position["avg_execution_price"]

        # Diff is the difference between average execution price and current price
        diff = 0
        # Using 2*avg_execution_price - execution_price to simplify the calculations
        actual_execution_price = 0
        # Current order is short order
        if order["direction"] == order_direction["short"]:
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

        self.__modify_fund_balance(fund=fund_mapping["holding_fund"], mode=fund_mode["defund"],
                                   asset_id=market_to_collateral_mapping[order["market_id"]], amount=leveraged_amount_out)

        if order["order_type"] == 5:
            borrowed_amount -= leveraged_amount_out
        else:
            borrowed_amount -= borrowed_amount_to_be_returned
            margin_amount -= margin_amount_to_be_reduced

        if order["order_type"] <= 3:
            if position["leverage"] > 1:
                self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                           asset_id=market_to_collateral_mapping[order["market_id"]], amount=borrowed_amount_to_be_returned)
            if net_account_value <= 0:
                deficit = leveraged_amount_out - borrowed_amount_to_be_returned
                user.modify_balance(
                    mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=deficit)
            else:
                amount_to_transfer_from = leveraged_amount_out - borrowed_amount_to_be_returned
                user.modify_balance(
                    mode=fund_mode["fund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=amount_to_transfer_from)
        else:
            if order["order_type"] == order_types["liquidation"]:
                self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                           asset_id=market_to_collateral_mapping[order["market_id"]], amount=borrowed_amount_to_be_returned)
                if net_account_value <= 0:
                    deficit = abs(net_account_value)

                    # Get position details of the user
                    user_balance = user.get_balance(
                        asset_id=market_to_collateral_mapping[order["market_id"]],
                    )

                    if deficit <= user_balance:
                        user.modify_balance(
                            mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=deficit)
                    else:
                        user.modify_balance(
                            mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=user_balance)
                        self.__modify_fund_balance(fund=fund_mapping["insurance_fund"], mode=fund_mode["defund"],
                                                   asset_id=market_to_collateral_mapping[order["market_id"]], amount=deficit - user_balance)
                else:
                    self.__modify_fund_balance(fund=fund_mapping["insurance_fund"], mode=fund_mode["fund"],
                                               asset_id=market_to_collateral_mapping[order["market_id"]], amount=net_account_value)
            else:
                self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                           asset_id=market_to_collateral_mapping[order["market_id"]], amount=leveraged_amount_out)
        print("From close order", average_execution_price,
              margin_amount, borrowed_amount)
        return (average_execution_price, margin_amount, borrowed_amount)

    def __get_fee(self, user: User, side: int) -> float:
        # ToDo change this logic when we add user discounts
        # Fee rate
        return self.maker_trading_fees if side == 1 else self.taker_trading_fees

    def set_fund_balance(self, fund: int, asset_id: int, new_balance: float):
        self.fund_balances[fund] = {
            asset_id: new_balance
        }

    def get_fund_balance(self, fund: int, asset_id: int) -> int:
        try:
            return self.fund_balances[fund][asset_id]
        except KeyError:
            return 0

    def get_batch_id_status(self, batch_id: int) -> int:
        try:
            return self.batch_id_status[batch_id]
        except KeyError:
            return 0

    def execute_batch(self, batch_id: int, request_list: List[Dict], user_list: List, quantity_locked: float = 1, market_id: int = BTC_USD_ID, oracle_price: float = 1000):
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
            side = 0
            if quantity_remaining == 0:
                if i != len(request_list) - 1:
                    print("Taker order must be the last order in the list")
                    return

                if request_list[i]["post_only"] != 0:
                    print("Post Only order cannot be a taker")
                    return

                if request_list[i]["time_in_force"] == 2:
                    if request_list[i]["quantity"] != quantity_locked:
                        print("F&K must be executed fully")
                    return

                if request_list[i]["order_type"] == 1:
                    if request_list[i]["slippage"] < 0:
                        print("Slippage cannot be negative")
                        return

                if request_list[i]["slippage"] > 15:
                    print("Slippage cannot be > 15")
                    return

                quantity_to_execute = quantity_locked
                execution_price = running_weighted_sum/quantity_locked

                if request_list[i]["order_type"] == order_types["market"]:
                    threshold = (
                        request_list[i]["slippage"]/100.0)*request_list[i]["price"]

                    if not ((request_list[i]["price"]-threshold) < execution_price < (request_list[i]["price"] + threshold)):
                        print("High slippage for taker order")
                        return
                else:
                    if request_list[i]["direction"] == order_direction["long"]:
                        if execution_price > request_list[i]["price"]:
                            print("Bad long limit order")
                            return
                    else:
                        if execution_price < request_list[i]["price"]:
                            print("Bad short limit order")
                            return
                side = order_side["taker"]
            else:
                if i == (len(request_list) - 1):
                    print("Taker order must be the last order in the list")
                    return

                order_portion_executed = user_list[i].get_portion_executed(
                    order_id=request_list[i]["order_id"])
                executable_quantity = request_list[i]["quantity"] - \
                    order_portion_executed

                if quantity_remaining < executable_quantity:
                    quantity_to_execute = quantity_remaining
                else:
                    quantity_to_execute = executable_quantity

                quantity_executed += quantity_to_execute
                execution_price = request_list[i]["price"]

                running_weighted_sum += execution_price*quantity_to_execute

                side = order_side["maker"]

            if request_list[i]["life_cycle"] == order_life_cycles["open"]:
                (avg_execution_price, margin_amount, borrowed_amount) = self.__process_open_orders(
                    user=user_list[i], order=request_list[i], execution_price=execution_price, order_size=quantity_to_execute, market_id=market_id, side=side)
            else:
                (avg_execution_price, margin_amount, borrowed_amount) = self.__process_close_orders(
                    user=user_list[i], order=request_list[i], execution_price=execution_price, order_size=quantity_to_execute, market_id=market_id)

                if avg_execution_price == 0:
                    return
            user_list[i].execute_order(order=request_list[i], size=quantity_to_execute, price=avg_execution_price,
                                       margin_amount=margin_amount, borrowed_amount=borrowed_amount, market_id=market_id)

        self.batch_id_status[batch_id] = 1
        return


# Emulates Liquidate Contract in python
class Liquidator:
    def __init__(self):
        self.maintenance_margin = 0.075
        self.maintenance_requirement = 0
        self.total_account_value_collateral = 0

    def __set_debugging_values(self, maintenance_requirement: float, total_account_value_collateral: float):
        self.maintenance_requirement = maintenance_requirement
        self.total_account_value_collateral = total_account_value_collateral

    def __find_collateral_balance(self, prices_array: List[Dict], collateral_array: List) -> int:

        total_collateral_value = 0
        for i in range(len(collateral_array)):
            total_collateral_value += collateral_array[i]["balance"] * \
                prices_array[i]["collateral_price"]
        return total_collateral_value

    def __check_for_deleveraging(self, position: Dict, collateral_price: float, asset_price: float) -> int:
        price_diff = (asset_price - position["avg_execution_price"]) if position["direction"] == order_direction["long"] else (
            position["avg_execution_price"] - asset_price)

        # calculate the amoutn to be sold for deleveraging
        # amount = (0.075 * P - D)(S - X)
        amount_to_be_sold = position["position_size"] - position["margin_amount"] * \
            collateral_price / (self.maintenance_margin *
                                asset_price - price_diff)

        # Calculate the new leverage
        position_value_usd = (
            position["margin_amount"] + position["borrowed_amount"]) * collateral_price
        amount_to_be_sold_usd = amount_to_be_sold * asset_price
        remaining_position_value_usd = position_value_usd - amount_to_be_sold_usd

        leverage_after_deleveraging = remaining_position_value_usd / \
            (position["margin_amount"] * collateral_price)
        if leverage_after_deleveraging <= 2:
            return 0
        else:
            return amount_to_be_sold

    def get_debugging_values(self) -> Tuple[float, float]:
        return (self.maintenance_requirement, self.total_account_value_collateral)

    def check_for_liquidation(self, user: User, prices_array: List[Dict]) -> Tuple[int, Dict]:
        positions = user.get_positions()
        print("User positions: ", positions)

        if len(positions) == 0:
            print("Liquidator: Empty positions array")
            return

        if len(prices_array) != len(prices_array):
            print("Liquidator: Invalid prices array")
            return

        least_collateral_ratio = 1
        least_collateral_ratio_position = 0
        least_collateral_ratio_position_collateral_price = 0
        least_collateral_ratio_position_asset_price = 0
        total_account_value = 0
        total_maintenance_requirement = 0

        for i in range(len(positions)):
            maintenance_position = positions[i]["avg_execution_price"] * \
                positions[i]["position_size"]
            maintenance_requirement = self.maintenance_margin * maintenance_position
            maintenance_requirement_usd = maintenance_requirement * \
                prices_array[i]["collateral_price"]

            # Calculate pnl to check if it is the least collateralized position
            price_diff = 0
            if positions[i]["direction"] == 1:
                price_diff = prices_array[i]["asset_price"] - \
                    positions[i]["avg_execution_price"]
            else:
                price_diff = positions[i]["avg_execution_price"] - \
                    prices_array[i]["asset_price"]

            pnl = price_diff*positions[i]["position_size"]
            print("Alice pnl:", pnl)
            # Calculate the value of the current account margin in usd
            position_value = maintenance_position - \
                positions[i]["borrowed_amount"] + pnl
            print("position value", position_value)
            net_position_value_usd = position_value * \
                prices_array[i]["collateral_price"]
            print("net_position_value_usd", net_position_value_usd)

            # Margin ratio calculation
            collateral_ratio = (positions[i]["margin_amount"] + pnl)/(
                positions[i]["position_size"] * prices_array[i]["asset_price"])
            print("Collateral ratio", collateral_ratio)

            if collateral_ratio < least_collateral_ratio:
                least_collateral_ratio = collateral_ratio
                least_collateral_ratio_position = positions[i]
                least_collateral_ratio_position_collateral_price = prices_array[
                    i]["collateral_price"]
                least_collateral_ratio_position_asset_price = prices_array[i]["asset_price"]

            total_maintenance_requirement += maintenance_requirement_usd
            total_account_value += net_position_value_usd

        collaterals_array = user.get_collaterals()
        print("User collaterals: ", collaterals_array)
        user_balance = self.__find_collateral_balance(
            prices_array=prices_array[len(positions):],
            collateral_array=collaterals_array
        )
        print("user_balance", user_balance)
        print("total_account_value", total_account_value)

        total_account_value_collateral = total_account_value + user_balance
        print("total account value w collateral",
              total_account_value_collateral)
        self.__set_debugging_values(maintenance_requirement=total_maintenance_requirement,
                                    total_account_value_collateral=total_account_value_collateral)
        liq_result = total_account_value_collateral < total_maintenance_requirement

        if liq_result:
            amount_to_be_sold = self.__check_for_deleveraging(
                position=least_collateral_ratio_position, collateral_price=least_collateral_ratio_position_collateral_price, asset_price=least_collateral_ratio_position_asset_price)
            print("Amount to be sold", amount_to_be_sold)
            user.liquidate_position(
                position=least_collateral_ratio_position,
                amount_to_be_sold=amount_to_be_sold
            )
        return (liq_result, least_collateral_ratio_position)

##################################
#### Helper Function Starknet ####
##################################


# Get the fund balance in decimals
async def get_fund_balance(fund: StarknetContract, asset_id: int, is_fee_balance: int) -> int:
    if is_fee_balance:
        result = await fund.get_total_fee(assetID_=asset_id).call()
        return from64x61(result.result.fee)
    else:
        result = await fund.balance(asset_id_=asset_id).call()
        return from64x61(result.result.amount)


# Get the balance of the required user in decimals
async def get_user_balance(user: StarknetContract, asset_id: int) -> int:
    user_query = await user.get_balance(assetID_=asset_id).call()
    return from64x61(user_query.result.res)


# Convert a 64x61 array to decimals
def convert_list_from_64x61(fixed_point_list: List[int]) -> List[float]:
    return [from64x61(x) for x in fixed_point_list]


# Liquidation check on starknet
async def check_liquidation_starknet(zkx_node_signer: Signer, zkx_node: StarknetContract, liquidate: StarknetContract, liquidate_params: List[int]) -> Tuple[int, List[float]]:
    liquidation_result_object = await zkx_node_signer.send_transaction(zkx_node, liquidate.contract_address, "check_liquidation", liquidate_params)
    liquidation_return_data = liquidation_result_object.call_info.retdata
    # Convert the quantity to decimals
    least_collateral_ratio_position = [
        from64x61(x) for x in liquidation_return_data[4:]]

    # return the boolean liquidation result and the position
    return (liquidation_return_data[1], least_collateral_ratio_position)


# Function to get the liquidatable position from starknet
async def get_liquidatable_position_starknet(user: User) -> List[float]:
    liquidatable_position_query = await user.get_deleveragable_or_liquidatable_position().call()
    liquidatable_position = list(liquidatable_position_query.result.position)
    # Convert amount to decimals rep
    liquidatable_position[2] = from64x61(liquidatable_position[2])
    return liquidatable_position


# Get the required user position in decimal rep
async def get_user_position(user: StarknetContract, market_id: int, direction: int) -> List[float]:
    user_starknet_query = await user.get_position_data(market_id_=market_id, direction_=direction).call()
    user_starknet_query_parsed = list(user_starknet_query.result.res)
    user_starknet_position = [from64x61(x)
                              for x in user_starknet_query_parsed]
    return user_starknet_position


# Convert price data dict to liquidation params format
def convert_to_64x61_liquidation_format(price_data_dict: Dict) -> List[int]:
    new_dict = copy.deepcopy(price_data_dict)
    new_dict["asset_price"] = to64x61(new_dict["asset_price"])
    new_dict["collateral_price"] = to64x61(
        new_dict["collateral_price"])

    return list(new_dict.values())


# Set the balance of a user in starknet
async def set_balance_starknet(admin_signer: Signer, admin: StarknetContract, user: StarknetContract, asset_id: int, new_balance: int):
    await admin_signer.send_transaction(admin, user.contract_address, "set_balance", [asset_id, to64x61(new_balance)])
    return


# Get the status of trading batch
async def get_batch_status(batch_id: int, trading: StarknetContract) -> int:
    batch_status_query = await trading.get_batch_id_status(batch_id_=batch_id).call()
    return batch_status_query.result.status


# Execute the orders in python and starkent
async def execute_batch(zkx_node_signer: Signer, zkx_node: StarknetContract, trading: StarknetContract, execute_batch_params: List[int]):
    # Send execute_batch transaction
    await zkx_node_signer.send_transaction(zkx_node, trading.contract_address, "execute_batch", execute_batch_params)
    return
################################
#### Helper Function Python ####
################################


# Function to get the liquidatable position from the python implementation
def get_liquidatable_position_python(user_test: User) -> List[float]:
    return list(user_test.get_deleveragable_or_liquidatable_position().values())


# Function to get the balance of a user from the python implementation
def get_user_balance_python(user: User, asset_id: int) -> float:
    return user.get_balance(asset_id)


# Function to get the balance of a fund from the python implementation
def get_fund_balance_python(executor: OrderExecutor, fund: int, asset_id: int) -> int:
    return executor.get_fund_balance(fund, asset_id)


# Function to get the required user position from the python implementation
def get_user_position_python(user: User, market_id: int, direction: int) -> List[float]:
    user_python_query = user.get_position(
        market_id=market_id, direction=direction)
    return list(user_python_query.values())


# Function to set the balance of the requried user in the python implementation
def set_balance_python(user_test: User, asset_id: int, new_balance: float):
    user_test.set_balance(new_balance=new_balance, asset_id=asset_id)
    return


# Liquidation check on the python implementation
def check_liquidation_python(user_test: User, liquidator: Liquidator, liquidate_params: List[Dict]) -> Tuple[int, List]:
    result = liquidator.check_for_liquidation(
        user=user_test, prices_array=liquidate_params)
    return (result[0], list(result[1].values())[:-2])


####################################
#### Execute on Starknet/Python ####
####################################


# Function to check for liquidation on starknet + python and to compare the results
async def check_liquidation(zkx_node_signer: Signer, zkx_node: StarknetContract, liquidator: Liquidator, user: StarknetContract, user_test: User, market_prices: List[Dict], collateral_prices: List[Dict], liquidate: StarknetContract):
    # Length of the final price data list
    total_length = len(market_prices) + len(collateral_prices)
    # intialize params list for starknet and python
    liquidation_params_starknet = [user.contract_address, total_length]
    liquidation_params_python = []

    # Process each market_prices dict
    for i in range(len(market_prices)):
        price_data_dict = {
            "asset_id": market_to_asset_mapping[market_prices[i]["market_id"]],
            "collateral_id": market_to_collateral_mapping[market_prices[i]["market_id"]],
            "asset_price": market_prices[i]["asset_price"],
            "collateral_price": market_prices[i]["collateral_price"]
        }

        # For python, we just append the formatted price_data_dict
        liquidation_params_python.append(price_data_dict)

        # For starknet, we need to convert asset_price and collateral price to 64x61
        liquidation_format_starknet = convert_to_64x61_liquidation_format(
            price_data_dict)

        liquidation_params_starknet.extend(liquidation_format_starknet)

    for i in range(len(collateral_prices)):
        price_data_dict = {
            "asset_id": 0,
            "collateral_id": collateral_prices[i]["collateral_id"],
            "asset_price": 0,
            "collateral_price": collateral_prices[i]["collateral_price"]
        }

        # For python, we just append the formatted price_data_dict
        liquidation_params_python.append(price_data_dict)

        # For starknet, we need to convert asset_price and collateral price to 64x61
        liquidation_format_starknet = convert_to_64x61_liquidation_format(
            price_data_dict)

        liquidation_params_starknet.extend(liquidation_format_starknet)

    # Get the liquidation result from starknet
    starknet_result = await check_liquidation_starknet(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, liquidate=liquidate, liquidate_params=liquidation_params_starknet)

    # Get the liquidation result from the python implmentation
    python_result = check_liquidation_python(
        user_test=user_test, liquidator=liquidator, liquidate_params=liquidation_params_python)

    # Compare the results of python and starkent
    compare_result_liquidation(
        starknet_result=starknet_result, python_result=python_result)


# Set balance for a list of users in python and starkent
async def set_balance(admin_signer: Signer, admin: StarknetContract, users: List[StarknetContract], users_test: List[User], balance_array: List[float], asset_id: int):
    for i in range(len(users)):
        await set_balance_starknet(admin_signer=admin_signer, admin=admin, user=users[i], asset_id=asset_id, new_balance=balance_array[i])
        set_balance_python(
            user_test=users_test[i], asset_id=asset_id, new_balance=balance_array[i])
    return


# Function to assert that the reverted tx has the required error_message
async def execute_batch_reverted(zkx_node_signer: Signer, zkx_node: StarknetContract, trading: StarknetContract, execute_batch_params: List[int], error_message: str):
    # Send execute_batch transaction
    await assert_revert(
        zkx_node_signer.send_transaction(zkx_node, trading.contract_address, "execute_batch", execute_batch_params), reverted_with=error_message)
    return


async def execute_and_compare(zkx_node_signer: Signer, zkx_node: StarknetContract, executor: OrderExecutor, orders: List[Dict], users_test: List[User], quantity_locked: float, market_id: int, oracle_price: float, trading: StarknetContract, is_reverted: int = 0, error_code: str = "", error_at_index: int = 0, param_2: str = "", error_message: str = "") -> Tuple[int, List]:
    # Generate a random batch id
    batch_id = random_string(10)

    # Intialize python and starknet params
    complete_orders_python = []
    complete_orders_starknet = []
    # Fill the remaining order attributes
    for i in range(len(orders)):
        # If an order_id is passed (for partial orders), fetch the order
        if "order_id" in orders[i]:
            (multiple_order_format,
             multiple_order_format_64x61) = users_test[i].get_order(orders[i]["order_id"])
            complete_orders_python.append(multiple_order_format)
            complete_orders_starknet += multiple_order_format_64x61.values()
        # If not, create the entire order
        else:
            (multiple_order_format,
             multiple_order_format_64x61) = users_test[i].create_order(**orders[i])
            complete_orders_python.append(multiple_order_format)
            complete_orders_starknet += multiple_order_format_64x61.values()

    # Format the values for starknet params
    execute_batch_params_starknet = [
        batch_id,
        to64x61(quantity_locked),
        market_id,
        to64x61(oracle_price),
        len(orders),
        *complete_orders_starknet
    ]

    # Format the values for python params
    execute_batch_params_python = [
        batch_id,
        complete_orders_python,
        users_test,
        quantity_locked,
        market_id,
        oracle_price
    ]

    # If the batch is to be reverted, generate the error_message
    if is_reverted:
        actual_error_message = ""
        # If the error code is passed
        if error_code:
            error_at_order_id = complete_orders_python[error_at_index]["order_id"]
            actual_error_message = f"{error_code} {error_at_order_id} {param_2}"
        # If an error message is passed
        elif error_message:
            actual_error_message = error_message
        await execute_batch_reverted(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, trading=trading, execute_batch_params=execute_batch_params_starknet, error_message=actual_error_message)
    else:
        await execute_batch(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, trading=trading, execute_batch_params=execute_batch_params_starknet)
        executor.execute_batch(*execute_batch_params_python)
    return (batch_id, complete_orders_python)


###################################
#### Compare Python & Starknet ####
###################################


# Function to check if the debuggin values set in Liquidation contract are correct
async def compare_debugging_values(liquidate: StarknetContract, liquidator: Liquidator):
    # Get the maintenance requirement of the last liquidation call of starknet
    maintenance_requirement_query = await liquidate.return_maintenance().call()
    maintenance_requirement = from64x61(
        maintenance_requirement_query.result.res)

    # Get the Account Value of the last liquidation call of starknet
    account_value_query = await liquidate.return_acc_value().call()
    account_value = from64x61(account_value_query.result.res)
    print("account_value starknet", account_value)

    # Get the maintenance requirement and account value of the python implmentation
    (maintenance_requirement_python,
     account_value_python) = liquidator.get_debugging_values()

    # Assert that both of them are appoximately equal
    assert maintenance_requirement_python == pytest.approx(
        maintenance_requirement, abs=1e-3)
    assert account_value_python == pytest.approx(account_value, abs=1e-3)


# Function to check the result of a liquidation call
def compare_result_liquidation(python_result: Tuple[int, List], starknet_result: Tuple[int, List]):
    assert python_result[0] == starknet_result[0]

    for element_1, element_2 in zip(python_result[1], starknet_result[1]):
        assert element_1 == pytest.approx(element_2, abs=1e-6)


# Function to check if the batch status on starknet is as expected
async def check_batch_status(batch_id: int, trading: StarknetContract, is_executed: int):
    batch_status = await get_batch_status(batch_id=batch_id, trading=trading)
    assert batch_status == is_executed


# Compare user balance in starknet and python
async def compare_user_balances(users: List[StarknetContract], user_tests: List[User], asset_id: int):
    for i in range(len(users)):
        user_balance = await get_user_balance(user=users[i], asset_id=asset_id)

        user_balance_python = get_user_balance_python(
            user=user_tests[i], asset_id=asset_id)

        assert user_balance_python == pytest.approx(
            user_balance, abs=1e-6)


# Compare user positions on starknet and python
async def compare_user_positions(users: List[StarknetContract], users_test: List[User], market_id: int):
    for i in range(len(users)):
        user_position_python_long = get_user_position_python(
            user=users_test[i], market_id=market_id, direction=order_direction["long"])
        user_position_python_short = get_user_position_python(
            user=users_test[i], market_id=market_id, direction=order_direction["short"])

        user_position_starknet_long = await get_user_position(
            user=users[i], market_id=market_id, direction=order_direction["long"])
        user_position_starknet_short = await get_user_position(
            user=users[i], market_id=market_id, direction=order_direction["short"])

        for element_1, element_2 in zip(user_position_python_long, user_position_starknet_long):
            assert element_1 == pytest.approx(element_2, abs=1e-6)

        for element_1, element_2 in zip(user_position_python_short, user_position_starknet_short):
            assert element_1 == pytest.approx(element_2, abs=1e-6)


# Compare fund balances of starknet and python
async def compare_fund_balances(executor: OrderExecutor, holding: StarknetContract, liquidity: StarknetContract, fee_balance: StarknetContract, insurance: StarknetContract, asset_id: int):
    holding_fund_balance = await get_fund_balance(fund=holding, asset_id=asset_id, is_fee_balance=0)
    holding_fund_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["holding_fund"], asset_id=asset_id)
    assert holding_fund_balance_python == pytest.approx(
        holding_fund_balance, abs=1e-6)

    liquidity_fund_balance = await get_fund_balance(fund=liquidity, asset_id=asset_id, is_fee_balance=0)
    liquidity_fund_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["liquidity_fund"], asset_id=asset_id)
    assert liquidity_fund_balance_python == pytest.approx(
        liquidity_fund_balance, abs=1e-6)

    fee_balance_balance = await get_fund_balance(fund=fee_balance, asset_id=asset_id, is_fee_balance=1)
    fee_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["fee_balance"], asset_id=asset_id)
    assert fee_balance_python == pytest.approx(
        fee_balance_balance, abs=1e-6)

    insurance_balance = await get_fund_balance(fund=insurance, asset_id=asset_id, is_fee_balance=0)
    insurance_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["insurance_fund"], asset_id=asset_id)
    assert insurance_balance_python == pytest.approx(
        insurance_balance, abs=1e-6)


# Assert that the liquidatable position on starknet and python class are the same
async def compare_liquidatable_position(user: StarknetContract, user_test: User):
    liquidatable_position_starknet = await get_liquidatable_position_starknet(user)
    liquidatable_position_python = get_liquidatable_position_python(user_test)

    print("liquidatable_position_starknet", liquidatable_position_starknet)
    print("liquidatable_position_python", liquidatable_position_python)
    for i in range(len(liquidatable_position_python)):
        assert liquidatable_position_python[i] == pytest.approx(
            liquidatable_position_starknet[i], abs=1e-3)
