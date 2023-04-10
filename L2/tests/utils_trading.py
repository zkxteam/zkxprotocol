import pytest
import copy
import random
import string
import calculate_abr
from math import isclose
from utils_asset import AssetID
from utils import Signer, str_to_felt, assert_revert, hash_order, from64x61, to64x61, felt_to_str
from typing import List, Dict, Tuple
from calculate_abr import calculate_abr
from starkware.starknet.testing.contract import StarknetContract

# Market IDs
BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_DAI_ID = str_to_felt("nxczijewihrewi")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
ETH_DAI_ID = str_to_felt("dsfjlkj3249jfkdl")
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


side = {
    "buy": 1,
    "sell": 2
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
    BTC_UST_ID: AssetID.UST,
    BTC_DAI_ID: AssetID.DAI,
    ETH_USD_ID: AssetID.USDC,
    ETH_DAI_ID: AssetID.DAI,
    TSLA_USD_ID: AssetID.USDC
}

market_to_asset_mapping = {
    BTC_USD_ID: AssetID.BTC,
    BTC_DAI_ID: AssetID.BTC,
    BTC_UST_ID: AssetID.BTC,
    ETH_USD_ID: AssetID.ETH,
    ETH_DAI_ID: AssetID.ETH,
    TSLA_USD_ID: AssetID.TSLA
}

#################
#### Classes ####
#################


# class Liquidator:
#     pass


# class OrderExecutor:
#     pass


# Emulates AccountManager Contract in python


class User:
    def __init__(self, private_key: int, user_address: int, liquidator_private_key: int = 0):
        self.signer = Signer(private_key)
        self.user_address = user_address
        self.orders = {}
        self.orders_decimal = {}
        self.balance = {7788: 23058430092136939520000}
        self.locked_margin = {}
        self.portion_executed = {}
        self.positions = {}
        self.collateral_to_market_array = {}
        self.market_array = []
        self.collateral_array = [7788]
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
            "side": order["side"],
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

    def __add_to_market_array(self, collateral_id: int, new_market_id: int):
        try:
            for i in range(len(self.collateral_to_market_array[collateral_id])):
                if self.collateral_to_market_array[collateral_id] == new_market_id:
                    return
            self.collateral_to_market_array[collateral_id].append(
                new_market_id)
        except:
            self.collateral_to_market_array.update({
                collateral_id: [new_market_id]
            })

    def __remove_from_market_array(self, collateral_id: int, market_id: int):
        try:
            if len(self.collateral_to_market_array[collateral_id]) == 1:
                self.collateral_to_market_array[collateral_id].pop()
            else:
                for i in range(len(self.collateral_to_market_array[collateral_id])):
                    if self.collateral_to_market_array[collateral_id][i] == market_id:
                        self.collateral_to_market_array[collateral_id][i] = self.collateral_to_market_array[collateral_id][len(
                            self.collateral_to_market_array[collateral_id]) - 1]
                        self.collateral_to_market_array[collateral_id].pop()
            print("new coll array",
                  self.collateral_to_market_array[collateral_id])
        except:
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
            "side": order["side"],
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
        collaterals = self.collateral_array
        positions = []

        for collateral in collaterals:
            try:
                for market in self.collateral_to_market_array[collateral]:
                    long_position = self.get_position(
                        market_id=market, direction=order_direction["long"])
                    short_position = self.get_position(
                        market_id=market, direction=order_direction["short"])

                    if long_position["position_size"] != 0:
                        long_position["market_id"] = market
                        long_position["direction"] = order_direction["long"]
                        positions.append(long_position)

                    if short_position["position_size"] != 0:
                        short_position["market_id"] = market
                        short_position["direction"] = order_direction["short"]
                        positions.append(short_position)
            except KeyError:
                continue
        return positions

    def get_collateral_to_markets_array(self, collateral_id: int) -> List[int]:
        try:
            return self.collateral_to_market_array[collateral_id]
        except KeyError:
            return []

    def get_positions_risk_management(self, collateral_id: int) -> List[Dict]:
        collaterals = self.collateral_array
        positions = []

        for collateral in collaterals:
            if collateral == collateral_id:
                try:
                    for market in self.collateral_to_market_array[collateral]:
                        long_position = self.get_position(
                            market_id=market, direction=order_direction["long"])
                        short_position = self.get_position(
                            market_id=market, direction=order_direction["short"])

                        if long_position["position_size"] != 0:
                            long_position["market_id"] = market
                            long_position["direction"] = order_direction["long"]
                            positions.append(long_position)

                        if short_position["position_size"] != 0:
                            short_position["market_id"] = market
                            short_position["direction"] = order_direction["short"]
                            positions.append(short_position)
                except KeyError:
                    continue
            else:
                continue
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

    def transfer_abr(self, market_id: int, direction: int, amount: float, timestamp: int):
        asset_id = market_to_collateral_mapping[market_id]

        self.modify_balance(
            mode=fund_mode["fund"], asset_id=asset_id, amount=amount)

        position = self.get_position(market_id=market_id, direction=direction)
        new_realized_pnl = position["realized_pnl"] + amount

        updated_position = {
            "avg_execution_price": position["avg_execution_price"],
            "position_size": position["position_size"],
            "margin_amount": position["margin_amount"],
            "borrowed_amount": position["borrowed_amount"],
            "leverage": position["leverage"],
            "created_timestamp": position["created_timestamp"],
            "modified_timestamp": timestamp,
            "realized_pnl": new_realized_pnl,
        }

        updated_dict = {
            direction: updated_position,
        }

        self.__update_position(
            market_id=market_id, direction=direction, updated_dict=updated_dict, updated_position=updated_position)

    def transfer_from_abr(self, market_id: int, direction: int, amount: float, timestamp: int):
        asset_id = market_to_collateral_mapping[market_id]
        self.modify_balance(
            mode=fund_mode["defund"], asset_id=asset_id, amount=amount)

        position = self.get_position(market_id=market_id, direction=direction)
        new_realized_pnl = position["realized_pnl"] - amount

        updated_position = {
            "avg_execution_price": position["avg_execution_price"],
            "position_size": position["position_size"],
            "margin_amount": position["margin_amount"],
            "borrowed_amount": position["borrowed_amount"],
            "leverage": position["leverage"],
            "created_timestamp": position["created_timestamp"],
            "modified_timestamp": timestamp,
            "realized_pnl": new_realized_pnl,
        }

        updated_dict = {
            direction: updated_position,
        }

        self.__update_position(
            market_id=market_id, direction=direction, updated_dict=updated_dict, updated_position=updated_position)

    def modify_balance(self, mode: int, asset_id: int, amount: float):
        current_balance = self.get_balance(asset_id=asset_id)
        new_balance = 0

        if mode == fund_mode["fund"]:
            new_balance = current_balance + amount
        else:
            new_balance = current_balance - amount
        self.set_balance(new_balance=new_balance, asset_id=asset_id)

    def modify_locked_margin(self, mode: int, asset_id: int, amount: float):
        current_locked_margin = self.get_locked_margin(asset_id=asset_id)
        new_locked_margin = 0

        if mode == fund_mode["fund"]:
            new_locked_margin = current_locked_margin + amount
        else:
            new_locked_margin = current_locked_margin - amount

        self.set_locked_balance(
            new_locked_margin=new_locked_margin, asset_id=asset_id)

    def set_balance(self, new_balance: float, asset_id: int = AssetID.USDC):
        self.balance[asset_id] = new_balance
        collaterals = self.collateral_array

        is_present = 0
        for i in range(len(collaterals)):
            if asset_id == collaterals[i]:
                is_present = 1

        if not is_present:
            self.collateral_array.append(asset_id)

    def set_locked_margin(self, new_locked_margin: float, asset_id: int = AssetID.USDC):
        self.locked_margin[asset_id] = new_locked_margin

    def get_balance(self, asset_id: int = AssetID.USDC) -> float:
        try:
            return self.balance[asset_id]
        except KeyError:
            print("key error here")
            return 0

    def get_locked_margin(self, asset_id: int = AssetID.USDC) -> float:
        try:
            return self.locked_margin[asset_id]
        except KeyError:
            return 0

    def get_deleveragable_or_liquidatable_position(self, collateral_id: int) -> Dict:
        try:
            if self.deleveragable_or_liquidatable_position[collateral_id] != {}:
                return self.deleveragable_or_liquidatable_position[collateral_id]
        except:
            pass

        return {
            "market_id": 0,
            "direction": 0,
            "amount_to_be_sold": 0,
            "liquidatable": 0
        }

    def set_deleveragable_or_liquidatable_position(self, collateral_id: int, updated_position: Dict):
        self.deleveragable_or_liquidatable_position.update({
            collateral_id: updated_position
        })

    def liquidate_position(self, position: Dict, collateral_id: int, amount_to_be_sold: float):
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
        self.deleveragable_or_liquidatable_position.update({
            collateral_id: liquidatable_position
        })

    def execute_order(self, order: Dict, size: float, price: float, margin_amount: float, borrowed_amount: float, market_id: int, timestamp: int, pnl: float, margin_update: float):
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

        if order["side"] == side["buy"]:
            current_pnl = 0
            created_timestamp = 0

            if position["position_size"] == 0:
                opposite_position = self.get_position(
                    market_id=order["market_id"], direction=order_direction["long"] if order["direction"] == order_direction["short"] else order_direction["short"])

                if opposite_position["position_size"] == 0:
                    self.__add_to_market_array(
                        new_market_id=order["market_id"], collateral_id=market_to_collateral_mapping[market_id])
                created_timestamp = timestamp
                current_pnl = pnl
            else:
                created_timestamp = position["created_timestamp"]
                current_pnl = position["realized_pnl"] + pnl

            new_position_size = position["position_size"] + size
            modified_timestamp = timestamp

            total_value = margin_amount + borrowed_amount
            new_leverage = total_value/margin_amount

            updated_position = {
                "avg_execution_price": price,
                "position_size": new_position_size,
                "margin_amount": margin_amount,
                "borrowed_amount": borrowed_amount,
                "leverage": new_leverage,
                "created_timestamp": created_timestamp,
                "modified_timestamp": modified_timestamp,
                "realized_pnl": current_pnl,
            }

            updated_dict = {
                order["direction"]: updated_position,
            }

            self.__update_position(
                market_id=order["market_id"], direction=order["direction"], updated_dict=updated_dict, updated_position=updated_position)
            current_locked_margin = self.get_locked_margin(
                asset_id=market_to_collateral_mapping[market_id])
            self.set_locked_margin(new_locked_margin=current_locked_margin +
                                   margin_update, asset_id=market_to_collateral_mapping[market_id])
            print("Lock margin update ", current_locked_margin, current_locked_margin +
                  margin_update)
        else:
            new_leverage = 0

            new_position_size = position["position_size"] - size

            if new_position_size < 0:
                print("Cannot close more thant the positionSize")
                return

            if order["order_type"] > 3:
                liq_position = self.get_deleveragable_or_liquidatable_position(
                    collateral_id=market_to_collateral_mapping[market_id])

                if liq_position["market_id"] != market_id:
                    print("Position not marked as liquidatable/deleveragable")
                    return ()

                if size > liq_position["amount_to_be_sold"]:
                    print("Order size larger than marked one")
                    return ()

                updated_amount = liq_position["amount_to_be_sold"] - size

                if isclose(updated_amount, 0, abs_tol=1e-6):
                    new_liq_position = {key: 0 for key in liq_position}
                    print("new liq position", new_liq_position)

                    self.set_deleveragable_or_liquidatable_position(
                        collateral_id=market_to_collateral_mapping[market_id],
                        updated_position=new_liq_position)
                else:
                    liq_position["amount_to_be_sold"] = updated_amount
                    print("old liq position", liq_position)

                    self.set_deleveragable_or_liquidatable_position(
                        collateral_id=market_to_collateral_mapping[market_id],
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
                    new_leverage = position["leverage"]

                    current_locked_margin = self.get_locked_margin(
                        asset_id=market_to_collateral_mapping[market_id])
                    self.set_locked_margin(new_locked_margin=current_locked_margin -
                                           margin_update, asset_id=market_to_collateral_mapping[market_id])
                    print("Lock margin update ", current_locked_margin, current_locked_margin +
                          margin_update)
            else:
                new_leverage = position["leverage"]

                current_locked_margin = self.get_locked_margin(
                    asset_id=market_to_collateral_mapping[market_id])
                self.set_locked_margin(new_locked_margin=current_locked_margin -
                                       margin_update, asset_id=market_to_collateral_mapping[market_id])

                print("Lock margin update ", current_locked_margin, current_locked_margin +
                      margin_update)

            updated_position = {}
            if new_position_size == 0:
                print("\n\nnew position size is 0")
                opposite_position = self.get_position(
                    market_id=order["market_id"], direction=order_direction["long"] if order["direction"] == order_direction["short"] else order_direction["short"])
                print("\n\nopposite_position size is: ",
                      opposite_position["position_size"])
                if opposite_position["position_size"] == 0:
                    print("\n\nopposite position size is 0")
                    self.__remove_from_market_array(
                        market_id=market_id, collateral_id=market_to_collateral_mapping[market_id])

                updated_position = {
                    "avg_execution_price": 0,
                    "position_size": 0,
                    "margin_amount": 0,
                    "borrowed_amount": 0,
                    "leverage": 0,
                    "created_timestamp": 0,
                    "modified_timestamp": 0,
                    "realized_pnl": 0,
                }
            else:
                current_pnl = position["realized_pnl"] + pnl
                updated_position = {
                    "avg_execution_price": price,
                    "position_size": new_position_size,
                    "margin_amount": margin_amount,
                    "borrowed_amount": borrowed_amount,
                    "leverage": new_leverage,
                    "created_timestamp": position["created_timestamp"],
                    "modified_timestamp": timestamp,
                    "realized_pnl": current_pnl,
                }

            updated_dict = {
                order["direction"]: updated_position,
            }

            self.__update_position(
                market_id=order["market_id"], direction=order["direction"], updated_dict=updated_dict, updated_position=updated_position)

    def get_position(self, market_id: int = BTC_USD_ID, direction: int = order_direction["long"]) -> Dict:
        try:
            return self.positions[market_id][direction]
        except KeyError:
            return {
                "avg_execution_price": 0,
                "position_size": 0,
                "margin_amount": 0,
                "borrowed_amount": 0,
                "leverage": 0,
                "created_timestamp": 0,
                "modified_timestamp": 0,
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
        side: int = side["buy"],
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
        assert side in (1, 2), "Invalid side"

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
            "side": side,
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

    def get_amount_to_withdraw(self, order_executor: 'OrderExecutor', liquidator: 'Liquidator', tav: float, tmr: float, position: Dict, collateral_id: int, timestamp: int):
        current_balance = self.get_balance(collateral_id)
        price = order_executor.get_market_price(
            position["market_id"], timestamp)
        new_size = (2.5 * position["margin_amount"])/price

        # Calculate AV and MR of least collateral position before selling
        av_position = (position["position_size"] *
                       price) - position["borrowed_amount"]
        mr_position = liquidator.maintenance_margin * \
            position["position_size"] * position["avg_execution_price"]

        # Calculate AV and MR of least collateral position after selling
        amount_to_be_sold_value = price * \
            (position["position_size"] - new_size)
        new_borrowed_amount = position["borrowed_amount"] - \
            amount_to_be_sold_value
        av_after = (new_size * price) - new_borrowed_amount
        mr_after = new_size * \
            position["avg_execution_price"] * liquidator.maintenance_margin

        new_tav = tav - av_position + av_after
        new_tmr = tmr - mr_position + mr_after

        if new_tav - new_tmr <= 0:
            return 0
        if current_balance <= new_tav - new_tmr:
            return (current_balance)
        else:
            return (new_tav - new_tmr)

    def get_safe_amount_to_withdraw(self, liquidator: 'Liquidator', order_executor: 'OrderExecutor', collateral_id: int, timestamp: int) -> Tuple[float, float]:
        current_balance = self.get_balance(collateral_id)
        print("collateral balance:", current_balance)
        if current_balance <= 0:
            return (0, 0)

        (liq_res, total_account_value, _, _, total_maintenance_requirement, _, least_collateral_ratio_position,
         _) = self.get_margin_info(order_executor=order_executor, asset_id=collateral_id, timestamp=timestamp)

        if total_maintenance_requirement == 0:
            return (current_balance, current_balance)

        if total_account_value <= 0:
            return (0, 0)

        safe_withdrawal_amount = 0
        if liq_res == 0:
            safe_amount = total_account_value - total_maintenance_requirement
            min_amount = min(safe_amount, current_balance)
            if min_amount == current_balance:
                return (current_balance, current_balance)
            safe_withdrawal_amount = min_amount

        withdrawal_amount = self.get_amount_to_withdraw(
            order_executor=order_executor, liquidator=liquidator, tav=total_account_value, tmr=total_maintenance_requirement, position=least_collateral_ratio_position, collateral_id=collateral_id, timestamp=timestamp)
        return (safe_withdrawal_amount, withdrawal_amount)

    def get_margin_info(self, order_executor: 'OrderExecutor', timestamp: int, asset_id: int, new_position_maintanence_requirement: float = 0, new_position_margin: float = 0) -> Tuple[int, float, float, float, float, float, Dict, float]:
        user_balance = self.get_balance(asset_id=asset_id)
        initial_margin_sum = self.get_locked_margin(asset_id=asset_id)
        unrealized_pnl_sum = 0
        total_maintenance_margin_requirement = new_position_maintanence_requirement
        least_collateral_ratio = float('inf')
        least_collateral_ratio_position = {"market_id": 0, "direction": 0, "avg_execution_price": 0,
                                           "position_size": 0, "margin_amount": 0, "borrowed_amount": 0, "leverage": 0}
        least_collateral_ratio_asset_price = 0
        print("user balance:", user_balance)
        total_margin = user_balance
        available_margin = 0

        markets_list = []

        try:
            markets_list = self.collateral_to_market_array[asset_id]
            print("markets list", markets_list)
        except KeyError:
            return (0, user_balance, user_balance, 0, 0, 0, {"market_id": 0, "direction": 0, "avg_execution_price": 0,
                                                             "position_size": 0, "margin_amount": 0, "borrowed_amount": 0, "leverage": 0}, 0)

        if len(markets_list) == 0:
            return (0, user_balance, user_balance, 0, 0, 0, {"market_id": 0, "direction": 0, "avg_execution_price": 0,
                                                             "position_size": 0, "margin_amount": 0, "borrowed_amount": 0, "leverage": 0}, 0)

        for market in markets_list:
            market_price = order_executor.get_market_price(
                market_id=market, timestamp=timestamp)
            print("market price in get_margin_info, ", market, market_price)

            if market_price == 0:
                return (0, user_balance, user_balance - initial_margin_sum, 0, 0, 0, {"market_id": 0, "direction": 0, "avg_execution_price": 0,
                                                                                      "position_size": 0, "margin_amount": 0, "borrowed_amount": 0, "leverage": 0}, 0)
            long_position = self.get_position(
                market_id=market, direction=order_direction["long"])
            short_position = self.get_position(
                market_id=market, direction=order_direction["short"])

            long_collateral_ratio = float('inf')
            short_collateral_ratio = float('inf')
            if long_position["position_size"] != 0:
                total_maintenance_margin_requirement += long_position["avg_execution_price"] * \
                    long_position["position_size"] * 0.075
                pnl = (
                    market_price - long_position["avg_execution_price"]) * long_position["position_size"]
                unrealized_pnl_sum += pnl
                long_collateral_ratio = (
                    long_position["margin_amount"] + pnl) / (long_position["position_size"] * market_price)
                print("long_collateral_ratio:", long_collateral_ratio,
                      pnl, long_position["margin_amount"])

            if short_position["position_size"] != 0:
                total_maintenance_margin_requirement += short_position["avg_execution_price"] * \
                    short_position["position_size"] * 0.075
                pnl = (
                    short_position["avg_execution_price"] - market_price) * short_position["position_size"]
                unrealized_pnl_sum += pnl
                short_collateral_ratio = (
                    short_position["margin_amount"] + pnl) / (short_position["position_size"] * market_price)
                print("short_collateral_ratio:", short_collateral_ratio,
                      pnl, short_position["margin_amount"])

            updated_long_position = {
                "market_id": market,
                "direction": order_direction["long"],
                "avg_execution_price": long_position["avg_execution_price"],
                "position_size": long_position["position_size"],
                "margin_amount": long_position["margin_amount"],
                "borrowed_amount": long_position["borrowed_amount"],
                "leverage": long_position["leverage"],
            }

            updated_short_position = {
                "market_id": market,
                "direction": order_direction["short"],
                "avg_execution_price": short_position["avg_execution_price"],
                "position_size": short_position["position_size"],
                "margin_amount": short_position["margin_amount"],
                "borrowed_amount": short_position["borrowed_amount"],
                "leverage": short_position["leverage"],
            }

            if least_collateral_ratio > long_collateral_ratio or least_collateral_ratio > short_collateral_ratio:
                print("checking collateral ratios", least_collateral_ratio,
                      short_collateral_ratio, long_collateral_ratio)
                least_collateral_ratio_asset_price = market_price
                if long_collateral_ratio <= short_collateral_ratio:
                    least_collateral_ratio = long_collateral_ratio
                    least_collateral_ratio_position = updated_long_position
                else:
                    least_collateral_ratio = short_collateral_ratio
                    least_collateral_ratio_position = updated_short_position

        total_margin += unrealized_pnl_sum
        print("tm", total_margin)
        print("ups", unrealized_pnl_sum)
        print("ims", initial_margin_sum)
        print("npm", new_position_margin)
        available_margin = total_margin - initial_margin_sum - new_position_margin
        print("available margin", available_margin)
        print("least collateral ratio", least_collateral_ratio)
        print("least collateral position", least_collateral_ratio_position)
        is_liquidation = 0

        if total_margin <= total_maintenance_margin_requirement:
            if least_collateral_ratio_position["direction"] == order_direction["long"]:
                if least_collateral_ratio_position["leverage"] != 1:
                    is_liquidation = 1
            else:
                is_liquidation = 1

        return (
            is_liquidation,
            total_margin,
            available_margin,
            unrealized_pnl_sum,
            total_maintenance_margin_requirement,
            least_collateral_ratio,
            least_collateral_ratio_position,
            least_collateral_ratio_asset_price
        )

# Emulates Trading Contract in python


class OrderExecutor:
    def __init__(self, maker_fees=0.0002 * 0.97, taker_fees=0.0005 * 0.97):
        self.maker_trading_fees = maker_fees
        self.taker_trading_fees = taker_fees
        self.fund_balances = {}
        self.batch_id_status = {}
        self.market_prices = {}
        self.ttl = 60

    def set_market_price(self, market_id: int, price: float, current_timestamp: int):
        current_price = self.get_market_price(market_id, current_timestamp)

        if current_price == 0:
            self.market_prices.update({
                market_id: {
                    "price": price,
                    "timestamp": current_timestamp
                }
            })
        else:
            return

    def __modify_fund_balance(self, fund: int, mode: int, asset_id: int, amount: float):
        current_balance = self.get_fund_balance(fund, asset_id,)
        new_balance = 0

        if mode == fund_mode["fund"]:
            new_balance = current_balance + amount
        else:
            new_balance = current_balance - amount

        self.set_fund_balance(fund, asset_id, new_balance)

    def __process_open_orders(self, user: User, order: Dict, execution_price: float, order_size: float, side: int, timestamp: int) -> Tuple[float, float, float, float, float]:
        position = user.get_position(
            market_id=order["market_id"], direction=order["direction"])

        average_execution_price = 0
        margin_amount = position["margin_amount"]
        borrowed_amount = position["borrowed_amount"]

        fee_rate = self.__get_fee(user=user, side=side)

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
        trading_fees = fees * -1

        # Balance that the user must stake/pay
        balance_to_be_deducted = fees

        (_, _, available_margin, _, _, _, _, _) = user.get_margin_info(
            order_executor=self, timestamp=timestamp, asset_id=market_to_collateral_mapping[
                order["market_id"]])

        if available_margin < balance_to_be_deducted:
            print("Low balance", balance_to_be_deducted, available_margin)
            return (0, 0, 0, 0, 0)

        if fees > 0:
            self.__modify_fund_balance(fund=fund_mapping["fee_balance"], mode=fund_mode["fund"],
                                       asset_id=market_to_collateral_mapping[order["market_id"]], amount=fees)

            user.modify_balance(
                mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=fees)

        # if available_margin < order_value_wo_leverage:
        #     print("Low balance", order_value_wo_leverage, available_margin)
        #     return (0, 0, 0, 0)

        self.__modify_fund_balance(fund=fund_mapping["holding_fund"], mode=fund_mode["fund"],
                                   asset_id=market_to_collateral_mapping[order["market_id"]], amount=leveraged_position_value)

        if order["leverage"] > 1:
            self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["defund"],
                                       asset_id=market_to_collateral_mapping[order["market_id"]], amount=amount_to_be_borrowed)
        print(margin_amount)
        return (average_execution_price, margin_amount, borrowed_amount, trading_fees, order_value_wo_leverage)

    def __get_quantity_to_execute(self, request: Dict, user: User, quantity_remaining: float, side: int) -> float:
        quantity_to_execute = 0
        quantity_to_execute_final = 0

        order_portion_executed = user.get_portion_executed(
            order_id=request["order_id"])
        executable_quantity = request["quantity"] - \
            order_portion_executed

        if quantity_remaining < executable_quantity:
            quantity_to_execute = quantity_remaining
        else:
            quantity_to_execute = executable_quantity

        if request['side'] == 2:
            position = user.get_position(
                market_id=request["market_id"], direction=request["direction"])

            if quantity_to_execute <= position["position_size"]:
                quantity_to_execute_final = quantity_to_execute
            else:
                quantity_to_execute_final = position["position_size"]
        else:
            quantity_to_execute_final = quantity_to_execute

        return quantity_to_execute_final

    def __adjust_quantity_locked(self, request_list: List[Dict], users_list: List[User], quantity_locked: float) -> Tuple[List[float]]:
        taker_quantity_to_execute = self.__get_quantity_to_execute(
            request=request_list[-1:][0], user=users_list[-1:][0], quantity_remaining=quantity_locked, side=order_side["taker"])
        print("taker_quantity_to_execute",
              taker_quantity_to_execute, quantity_locked)
        maker_execution_sizes = []
        quantity_executed = 0
        for i in range(len(request_list) - 1):
            quantity_to_execute = self.__get_quantity_to_execute(
                request=request_list[i], user=users_list[i], quantity_remaining=taker_quantity_to_execute - quantity_executed, side=order_side["maker"])
            maker_execution_sizes.append(quantity_to_execute)

            quantity_executed += quantity_to_execute
        maker_execution_sizes.append(quantity_executed)

        return (maker_execution_sizes)

    def __process_close_orders(self, user: User, order: Dict, execution_price: float, order_size: float, timestamp: int) -> Tuple[float, float, float, float, float]:

        # Get the user position
        position = user.get_position(order["market_id"], order["direction"])

        # Values to be populated for position object
        margin_amount = position["margin_amount"]
        borrowed_amount = position["borrowed_amount"]
        average_execution_price = position["avg_execution_price"]

        margin_amount_close = 0
        borrowed_amount_close = 0

        # Diff is the difference between average execution price and current price
        diff = 0
        # Using 2*avg_execution_price - execution_price to simplify the calculations
        actual_execution_price = 0
        # Current order is long order
        if order["direction"] == order_direction["long"]:
            # Actual execution price is same as execution price
            actual_execution_price = execution_price
            diff = execution_price - position["avg_execution_price"]
        else:
            diff = position["avg_execution_price"] - execution_price
            # Actual execution price is 2*avg_execution_price - execution_price
            actual_execution_price = position["avg_execution_price"] + diff

        # Calculate the profit and loss for the user
        pnl = order_size * diff
        realized_pnl = 0
        # Value of the position after factoring in the pnl
        net_account_value = margin_amount + pnl

        # Value of asset at current price w leverage
        leveraged_amount_out = order_size * actual_execution_price

        # Calculate the amount that needs to be returned to the user
        percent_of_position = order_size / \
            position["position_size"]
        borrowed_amount_to_be_returned = borrowed_amount*percent_of_position
        margin_amount_to_be_reduced = margin_amount*percent_of_position
        margin_unlock_amount = 0

        if order["order_type"] == order_types["deleverage"]:
            borrowed_amount_close = borrowed_amount - leveraged_amount_out
            margin_amount_close = margin_amount
        else:
            borrowed_amount_close = borrowed_amount - borrowed_amount_to_be_returned
            margin_amount_close = margin_amount - margin_amount_to_be_reduced
            margin_unlock_amount = margin_amount_to_be_reduced

        self.__modify_fund_balance(fund=fund_mapping["holding_fund"], mode=fund_mode["defund"],
                                   asset_id=market_to_collateral_mapping[order["market_id"]], amount=leveraged_amount_out)

        if position["leverage"] > 1:
            print("deposited {} in liquidity fund",
                  borrowed_amount_to_be_returned)
            self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                       asset_id=market_to_collateral_mapping[order["market_id"]], amount=borrowed_amount_to_be_returned)

        if net_account_value <= 0:
            print("Deficit", net_account_value)
            deficit = abs(net_account_value)

            # Get position details of the user
            (_, _, available_margin, _, _, _, _, _) = user.get_margin_info(
                order_executor=self, timestamp=timestamp, asset_id=market_to_collateral_mapping[
                    order["market_id"]]
            )
            print("available margin is ", available_margin)

            if deficit > available_margin:
                if available_margin < 0:
                    self.__modify_fund_balance(fund=fund_mapping["insurance_fund"], mode=fund_mode["defund"],
                                               asset_id=market_to_collateral_mapping[order["market_id"]], amount=deficit)
                    print("reaches available_margin < 0")
                else:
                    self.__modify_fund_balance(fund=fund_mapping["insurance_fund"], mode=fund_mode["defund"],
                                               asset_id=market_to_collateral_mapping[order["market_id"]], amount=deficit - available_margin)
                    print("reaches available_margin > 0")
            else:
                print("defict <= available margin")
            user.modify_balance(
                mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=deficit+margin_unlock_amount)
            realized_pnl = deficit*-1
        else:
            if order["order_type"] <= 3:
                if pnl > 0:
                    (_, total_margin, available_margin, _, _, _, _, _) = user.get_margin_info(
                        order_executor=self, timestamp=timestamp, asset_id=market_to_collateral_mapping[
                            order["market_id"]])
                    print("available margin is ",
                          available_margin, total_margin)
                    print("User profit of:", pnl,
                          "\nposition value:", net_account_value)
                    user.modify_balance(
                        mode=fund_mode["fund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=pnl)
                else:
                    print("User loss of:", pnl,
                          "\nposition value:", net_account_value)
                    user.modify_balance(
                        mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=abs(pnl))
                realized_pnl = pnl
            elif order["order_type"] == order_types["liquidation"]:
                self.__modify_fund_balance(fund=fund_mapping["insurance_fund"], mode=fund_mode["fund"],
                                           asset_id=market_to_collateral_mapping[order["market_id"]], amount=net_account_value)
                user.modify_balance(
                    mode=fund_mode["defund"], asset_id=market_to_collateral_mapping[order["market_id"]], amount=margin_unlock_amount)
                realized_pnl = margin_unlock_amount*-1
            else:
                realized_pnl = 0

        return (average_execution_price, margin_amount_close, borrowed_amount_close, realized_pnl, margin_unlock_amount)

    def __get_fee(self, user: User, side: int) -> float:
        # ToDo change this logic when we add user discounts
        # Fee rate
        return self.maker_trading_fees if side == 1 else self.taker_trading_fees

    def set_fund_balance(self, fund: int, asset_id: int, new_balance: float):
        try:
            self.fund_balances[fund].update({
                asset_id: new_balance
            })
        except KeyError:
            self.fund_balances.update({
                fund: {
                    asset_id: new_balance
                }
            })

    def get_market_price(self, market_id: int, timestamp: int) -> float:
        try:
            if timestamp - self.market_prices[market_id]["timestamp"] <= self.ttl:
                print("Market price:", self.market_prices[market_id]["price"])
                return self.market_prices[market_id]["price"]
            else:
                print("Market price out of ttl", 0)
                return 0

        except:
            print("Error while getting market price")
            return 0

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

    def execute_batch(self, batch_id: int, request_list: List[Dict], user_list: List, quantity_locked: float = 1, market_id: int = BTC_USD_ID, oracle_price: float = 1000, timestamp: int = 0):
        # Store the quantity executed so far
        running_weighted_sum = 0

        self.set_market_price(
            market_id=market_id, price=oracle_price, current_timestamp=timestamp)

        (maker_execution_sizes) = self.__adjust_quantity_locked(
            request_list=request_list, users_list=user_list, quantity_locked=quantity_locked)
        print("adjusted size", maker_execution_sizes[-1:])
        print("maker_execution_sizes", maker_execution_sizes)

        for i in range(len(request_list)):
            print("order id:", i)
            quantity_to_execute = 0
            execution_price = 0
            margin_amount = 0
            borrowed_amount = 0
            avg_execution_price = 0
            trade_side = 0

            # Taker Order
            if i == len(request_list) - 1:
                if request_list[i]["post_only"] != 0:
                    print("Post Only order cannot be a taker")
                    return

                if request_list[i]["time_in_force"] == order_time_in_force["fill_or_kill"]:
                    if request_list[i]["quantity"] != maker_execution_sizes[i]:
                        print("F&K must be executed fully")
                    return

                if request_list[i]["order_type"] == order_types["market"]:
                    if request_list[i]["slippage"] < 0:
                        print("Slippage cannot be negative")
                        return

                if request_list[i]["slippage"] > 15:
                    print("Slippage cannot be > 15")
                    return

                execution_price = running_weighted_sum/maker_execution_sizes[i]

                if request_list[i]["order_type"] == order_types["market"]:
                    threshold = (
                        request_list[i]["slippage"]/100.0)*oracle_price

                    if request_list[i]["direction"] == request_list[i]["side"]:
                        if execution_price > oracle_price + threshold:
                            print("High slippage for taker order")
                            return
                    else:
                        if oracle_price - threshold > execution_price:
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
                trade_side = order_side["taker"]
                quantity_to_execute = maker_execution_sizes[i]
            else:
                quantity_to_execute = maker_execution_sizes[i]

                if quantity_to_execute == 0:
                    print("skipping 0 size order: ", i)
                    continue
                execution_price = request_list[i]["price"]

                running_weighted_sum += execution_price*quantity_to_execute

                trade_side = order_side["maker"]

            pnl = 0
            margin_update = 0

            if request_list[i]["side"] == side["buy"]:
                (avg_execution_price, margin_amount, borrowed_amount, trading_fees, margin_lock_update) = self.__process_open_orders(
                    user=user_list[i], order=request_list[i], execution_price=execution_price, order_size=quantity_to_execute, side=trade_side, timestamp=timestamp)
                pnl = trading_fees
                margin_update = margin_lock_update
                if avg_execution_price == 0:
                    print("Cannot execute batch; returning")
                    return
            else:
                (avg_execution_price, margin_amount, borrowed_amount, realized_pnl, margin_unlock_amount) = self.__process_close_orders(
                    user=user_list[i], order=request_list[i], execution_price=execution_price, order_size=quantity_to_execute, timestamp=timestamp)
                pnl = realized_pnl
                print('realized pnl for close order',
                      pnl, margin_unlock_amount)
                margin_update = margin_unlock_amount
                if avg_execution_price == 0:
                    return
            user_list[i].execute_order(order=request_list[i], size=quantity_to_execute, price=avg_execution_price,
                                       margin_amount=margin_amount, borrowed_amount=borrowed_amount, market_id=market_id, timestamp=timestamp, pnl=pnl, margin_update=margin_update)
            print("\n\n")

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

    def __check_for_deleveraging(self, position: Dict, asset_price: float) -> int:
        price_diff = (asset_price - position["avg_execution_price"]) if position["direction"] == order_direction["long"] else (
            position["avg_execution_price"] - asset_price)

        # calculate the amoutn to be sold for deleveraging
        # amount = (0.075 * P - D)(S - X)
        amount_to_be_sold = position["position_size"] - position["margin_amount"] / (
            self.maintenance_margin * asset_price - price_diff)
        print("\nAmount to be sold:", amount_to_be_sold, "\n")

        # Calculate the new leverage
        position_value = (
            position["margin_amount"] + position["borrowed_amount"])
        amount_to_be_sold_value = amount_to_be_sold * \
            position["avg_execution_price"]
        print("\nAmount to be sold:", amount_to_be_sold, "\n")
        remaining_position_value = position_value - amount_to_be_sold_value

        leverage_after_deleveraging = remaining_position_value / \
            (position["margin_amount"])

        print("leverage_after_deleveraging", leverage_after_deleveraging)
        if leverage_after_deleveraging <= 2:
            return 0
        else:
            return amount_to_be_sold

    def get_debugging_values(self) -> Tuple[float, float]:
        return (self.maintenance_requirement, self.total_account_value_collateral)

    def mark_under_collateralized_position(self, user: User, order_executor: OrderExecutor, collateral_id: int, timestamp: int) -> Tuple[int, Dict, float, float]:
        liquidatable_position = user.get_deleveragable_or_liquidatable_position(
            collateral_id=collateral_id)

        if liquidatable_position["amount_to_be_sold"] != 0:
            print("Position already marked")
            return (1, {
                    "market_id": 0,
                    "direction": 0,
                    "avg_execution_price": 0,
                    "position_size": 0,
                    "margin_amount": 0,
                    "borrowed_amount": 0,
                    "leverage": 0,
                    }, 0, 0)

        (liq_result, total_margin, _, _, maintenance_margin_requirement, least_collateral_ratio, least_collateral_ratio_position,
         least_collateral_ratio_position_asset_price) = user.get_margin_info(order_executor=order_executor, asset_id=collateral_id, timestamp=timestamp)

        print("least_collateral_ratio_position_asset_price",
              least_collateral_ratio_position_asset_price)
        if least_collateral_ratio_position_asset_price == 0:
            return (0, {
                "market_id": 0,
                "direction": 0,
                "avg_execution_price": 0,
                "position_size": 0,
                "margin_amount": 0,
                "borrowed_amount": 0,
                "leverage": 0,
            }, 0, 0)

        if liq_result:
            if least_collateral_ratio > 0:
                amount_to_be_sold = self.__check_for_deleveraging(
                    position=least_collateral_ratio_position, asset_price=least_collateral_ratio_position_asset_price)
                user.liquidate_position(
                    position=least_collateral_ratio_position,
                    amount_to_be_sold=amount_to_be_sold,
                    collateral_id=collateral_id
                )
            else:
                user.liquidate_position(
                    position=least_collateral_ratio_position,
                    amount_to_be_sold=0,
                    collateral_id=collateral_id
                )
        self.__set_debugging_values(maintenance_requirement=maintenance_margin_requirement,
                                    total_account_value_collateral=total_margin)
        return (liq_result, least_collateral_ratio_position, total_margin, maintenance_margin_requirement)


class ABR:
    def __init__(self):
        self.abr_values = {}
        self.abr_last_price = {}
        self.abr_fund = {}
        self.abr_timestamp = 0

    def get_abr(self, market_id: int) -> Tuple[float, float]:
        try:
            return (self.abr_values[market_id], self.abr_last_price[market_id])
        except KeyError:
            return (0, 0)

    def fund_abr(self, market_id: int, amount: float):
        asset_id = market_to_collateral_mapping[market_id]
        try:
            self.abr_fund[asset_id] += amount
        except KeyError:
            self.abr_fund[asset_id] = amount

    def defund_abr(self, market_id: int, amount: float):
        asset_id = market_to_collateral_mapping[market_id]
        try:
            self.abr_fund[asset_id] -= amount
        except KeyError:
            self.abr_fund[asset_id] = 0

    def find_abr(self, market_id: int, price: float, perp_spot: List[float], perp: List[float], base_rate: float, boll_width: float) -> float:
        abr_rate = calculate_abr(
            perp_spot=perp_spot, perp=perp, base_rate=base_rate, boll_width=boll_width)
        self.abr_last_price[market_id] = price

        return abr_rate

    def set_abr(self, market_id: int, new_abr: float, timestamp: int):
        self.abr_values[market_id] = new_abr
        self.abr_timestamp = timestamp

    def user_pays(self, user: User, market_id: int, direction: int, amount: float, timestamp: int):
        user.transfer_from_abr(market_id=market_id, direction=direction,
                               amount=amount, timestamp=timestamp)
        self.fund_abr(market_id=market_id, amount=amount)

    def user_receives(self, user: User, market_id: int, direction: int, amount: float, timestamp: int):
        user.transfer_abr(market_id=market_id, direction=direction,
                          amount=amount, timestamp=timestamp)
        self.defund_abr(market_id=market_id, amount=amount)

    def pay_abr(self, users_list: List[User], timestamp: int):
        for user in users_list:
            user_positions = user.get_positions()

            for position in user_positions:
                market_id = position["market_id"]
                direction = position["direction"]
                abr_value = self.abr_values[market_id]
                payment_amount = abs(self.abr_last_price[market_id] *
                                     position["position_size"] * abr_value)
                if position["created_timestamp"] > self.abr_timestamp:
                    continue

                print("ABR value:", abr_value)
                print("Payment amount:", payment_amount)
                if abr_value < 0:
                    if direction == order_direction["short"]:
                        self.user_pays(
                            user=user, market_id=market_id,  direction=direction, amount=payment_amount, timestamp=timestamp)
                    else:
                        self.user_receives(
                            user=user, market_id=market_id,  direction=direction, amount=payment_amount, timestamp=timestamp)

                else:
                    if direction == order_direction["short"]:
                        self. user_receives(
                            user=user, market_id=market_id,  direction=direction, amount=payment_amount, timestamp=timestamp)
                    else:
                        self.user_pays(
                            user=user, market_id=market_id,  direction=direction, amount=payment_amount, timestamp=timestamp)


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

# Get the locked balance of the required user in decimals


async def get_user_locked_margin(user: StarknetContract, asset_id: int) -> int:
    user_query = await user.get_locked_margin(assetID_=asset_id).call()
    return from64x61(user_query.result.res)


# Convert a 64x61 array to decimals
def convert_list_from_64x61(fixed_point_list: List[int]) -> List[float]:
    return [from64x61(x) for x in fixed_point_list]


# Liquidation check on starknet
async def mark_under_collateralized_position_starknet(zkx_node_signer: Signer, zkx_node: StarknetContract, liquidate: StarknetContract, liquidate_params: List[int]) -> Tuple[int, List[float]]:
    liquidation_result_object = await zkx_node_signer.send_transaction(zkx_node, liquidate.contract_address, "mark_under_collateralized_position", liquidate_params)
    liquidation_return_data = liquidation_result_object.call_info.retdata
    print("liquidation return data:", liquidation_return_data)
    # Convert the quantity to decimals
    least_collateral_ratio_position = [
        from64x61(x) for x in liquidation_return_data[4:9]]
    least_collateral_ratio_position.insert(0, liquidation_return_data[2])
    least_collateral_ratio_position.insert(1, liquidation_return_data[3])

    # return the boolean liquidation result and the position
    return (liquidation_return_data[1], least_collateral_ratio_position, from64x61(liquidation_return_data[9]), from64x61(liquidation_return_data[10]))


# Function to get the liquidatable position from starknet
async def get_liquidatable_position_starknet(user: User, collateral_id: int) -> List[float]:
    liquidatable_position_query = await user.get_deleveragable_or_liquidatable_position(collateral_id).call()
    liquidatable_position = list(liquidatable_position_query.result.position)
    # Convert amount to decimals rep
    liquidatable_position[2] = from64x61(liquidatable_position[2])
    return liquidatable_position


# Get the required user position in decimal rep
async def get_user_position(user: StarknetContract, market_id: int, direction: int) -> List[float]:
    user_starknet_query = await user.get_position_data(market_id_=market_id, direction_=direction).call()
    user_starknet_query_parsed = list(user_starknet_query.result.res)
    user_starknet_position = [from64x61(x)
                              for x in user_starknet_query_parsed[:5]] + user_starknet_query_parsed[5:7] + [from64x61(x)
                                                                                                            for x in user_starknet_query_parsed[7:]]
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
    execution_info = await zkx_node_signer.send_transaction(zkx_node, trading.contract_address, "execute_batch", execute_batch_params)
    return execution_info
################################
#### Helper Function Python ####
################################


# Function to get the liquidatable position from the python implementation
def get_liquidatable_position_python(user_test: User, collateral_id: int) -> List[float]:
    return list(user_test.get_deleveragable_or_liquidatable_position(collateral_id=collateral_id).values())


# Function to get the balance of a user from the python implementation
def get_user_balance_python(user: User, asset_id: int) -> float:
    return user.get_balance(asset_id)

# Function to get the balance of a user from the python implementation


def get_user_locked_margin_python(user: User, asset_id: int) -> float:
    return user.get_locked_margin(asset_id)


# Function to get the balance of a fund from the python implementation
def get_fund_balance_python(executor: OrderExecutor, fund: int, asset_id: int) -> int:
    return executor.get_fund_balance(fund, asset_id)


# Function to get the required user position from the python implementation
def get_user_position_python(user: User, market_id: int, direction: int) -> List[float]:
    user_python_query = user.get_position(
        market_id=market_id, direction=direction)
    # print(user_python_query)
    return list(user_python_query.values())


# Function to set the balance of the requried user in the python implementation
def set_balance_python(user_test: User, asset_id: int, new_balance: float):
    user_test.set_balance(new_balance=new_balance, asset_id=asset_id)
    return


# Liquidation check on the python implementation
def mark_under_collateralized_position_python(user_test: User, liquidator: Liquidator, order_executor: OrderExecutor, collateral_id: int, timestamp: int) -> Tuple[int, List, int, int]:
    result = liquidator.mark_under_collateralized_position(
        user=user_test, order_executor=order_executor, collateral_id=collateral_id, timestamp=timestamp)
    return (result[0], list(result[1].values())[:7], result[2], result[3])

# Get safe withdrawal amount for python implementation


def get_safe_amount_to_withdraw_python(user_test: User, liquidator: Liquidator, order_executor: OrderExecutor, collateral_id: int, timestamp: int) -> Tuple[float, float]:
    result = user_test.get_safe_amount_to_withdraw(
        liquidator, order_executor, collateral_id, timestamp)
    return (result[0], result[1])


####################################
#### Execute on Starknet/Python ####
####################################


# Function to check for liquidation on starknet + python and to compare the results
async def mark_under_collateralized_position(zkx_node_signer: Signer, zkx_node: StarknetContract, liquidator: Liquidator, user: StarknetContract, user_test: User, liquidate: StarknetContract, collateral_id: int, order_executor: OrderExecutor, timestamp):
    liquidate_params = [user.contract_address, collateral_id]
    # Get the liquidation result from starknet
    starknet_result = await mark_under_collateralized_position_starknet(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, liquidate=liquidate, liquidate_params=liquidate_params)

    # Get the liquidation result from the python implmentation
    python_result = mark_under_collateralized_position_python(
        user_test=user_test, liquidator=liquidator, collateral_id=collateral_id, order_executor=order_executor, timestamp=timestamp)

    # Compare the results of python and starkent
    compare_result_liquidation(
        starknet_result=starknet_result, python_result=python_result)


async def make_abr_payments(admin_signer: Signer, admin: StarknetContract, abr_core: StarknetContract, abr_executor: ABR, users_test: List[User], timestamp: int):
    abr_executor.pay_abr(users_list=users_test, timestamp=timestamp)
    abr_tx = await admin_signer.send_transaction(admin, abr_core.contract_address, "make_abr_payments", [])
    return abr_tx

# Set balance for a list of users in python and starkent


async def set_balance(admin_signer: Signer, admin: StarknetContract, users: List[StarknetContract], users_test: List[User], balance_array: List[float], asset_id: int):
    for i in range(len(users)):
        await set_balance_starknet(admin_signer=admin_signer, admin=admin, user=users[i], asset_id=asset_id, new_balance=balance_array[i])
        set_balance_python(
            user_test=users_test[i], asset_id=asset_id, new_balance=balance_array[i])
    return


async def set_abr_value(market_id: int, node_signer: Signer, node: StarknetContract, abr_core: StarknetContract, abr_executor: StarknetContract, timestamp: int, spot: List[float], perp: List[float], spot_64x61: List[int], perp_64x61: List[int], epoch: int, base_rate: float, boll_width: float):
    arguments_64x61 = [market_id, 480, *spot_64x61, 480, *perp_64x61]
    set_abr_value_tx = await node_signer.send_transaction(node, abr_core.contract_address, 'set_abr_value', arguments_64x61)

    python_abr = abr_executor.find_abr(
        market_id, price=perp[479], perp_spot=spot, perp=perp, base_rate=base_rate, boll_width=boll_width)

    (abr_value, abr_last_price) = await compare_abr_values(
        market_id=market_id, abr_executor=abr_executor, abr_core=abr_core, timestamp=timestamp, python_abr=python_abr, epoch=epoch)

    return (set_abr_value_tx, abr_value, abr_last_price)

# Function to assert that the reverted tx has the required error_message


async def execute_batch_reverted(zkx_node_signer: Signer, zkx_node: StarknetContract, trading: StarknetContract, execute_batch_params: List[int], error_message: str):
    # Send execute_batch transaction
    await assert_revert(
        zkx_node_signer.send_transaction(zkx_node, trading.contract_address, "execute_batch", execute_batch_params), reverted_with=error_message)
    return 1


async def execute_and_compare(zkx_node_signer: Signer, zkx_node: StarknetContract, executor: OrderExecutor, orders: List[Dict], users_test: List[User], quantity_locked: float, market_id: int, oracle_price: float, trading: StarknetContract, timestamp: int = 0, is_reverted: int = 0, error_code: str = "", error_at_index: int = -1, param_2: str = "", error_message: str = "") -> Tuple[int, List]:
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
        oracle_price,
        timestamp
    ]

    global execution_info
    # If the batch is to be reverted, generate the error_message
    if is_reverted:
        actual_error_message = ""
        # If the error code is passed
        if error_code:
            if error_at_index == -1:
                actual_error_message = f"{error_code} {param_2}"
            else:
                error_at_order_id = complete_orders_python[error_at_index]["order_id"]
                actual_error_message = f"{error_code} {error_at_order_id} {param_2}"
        # If an error message is passed
        elif error_message:
            actual_error_message = error_message
        execution_info = await execute_batch_reverted(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, trading=trading, execute_batch_params=execute_batch_params_starknet, error_message=actual_error_message)
    else:
        execution_info = await execute_batch(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, trading=trading, execute_batch_params=execute_batch_params_starknet)
        # executor.execute_batch(*execute_batch_params_python)
    return (batch_id, complete_orders_python, execution_info)


###################################
#### Compare Python & Starknet ####
###################################

async def compare_markets_array(user: StarknetContract, user_test: User, collatera_id: int):
    # python_markets_array = user_test.get_collateral_to_markets_array(
    # collatera_id)
    starknet_markets_array_query = await user.get_collateral_to_markets_array(collatera_id).call()
    starknet_markets_array = starknet_markets_array_query.result.markets_array

    print("Markets array: ", starknet_markets_array)
    # for element_1, element_2 in zip(starknet_markets_array, python_markets_array):
    #     assert element_1 == element_2


# Function to check if the debuggin values set in Liquidation contract are correct
async def compare_debugging_values(liquidate: StarknetContract, liquidator: Liquidator):
    # Get the maintenance requirement of the last liquidation call of starknet
    maintenance_requirement_query = await liquidate.return_maintenance().call()
    maintenance_requirement = from64x61(
        maintenance_requirement_query.result.res)

    # Get the Account Value of the last liquidation call of starknet
    account_value_query = await liquidate.return_acc_value().call()
    account_value = from64x61(account_value_query.result.res)

    # Get the maintenance requirement and account value of the python implmentation
    (maintenance_requirement_python,
     account_value_python) = liquidator.get_debugging_values()

    print("maintenance_requirement", maintenance_requirement)
    print("account_value", account_value)
    print("maintenance_requirement_python", maintenance_requirement_python)
    print("account_value_python", account_value_python)

    # Assert that both of them are appoximately equal
    assert maintenance_requirement_python == pytest.approx(
        maintenance_requirement, abs=1e-3)
    assert account_value_python == pytest.approx(account_value, abs=1e-3)


async def get_user_margin_info_starknet(user: StarknetContract, collateral_id: int) -> Tuple[int, float, float, float, float, float, List, float]:
    # Get the margin_info from starknet
    margin_result_query = await user.get_margin_info(collateral_id, 0, 0).call()
    margin_result = margin_result_query.result
    (is_liquidation, total_margin, available_margin, unrealized_pnl_sum, maintenance_margin_requirement, least_collateral_ratio, least_collateral_ratio_position, least_collateral_ratio_position_asset_price) = (
        margin_result.is_liquidation, from64x61(margin_result.total_margin), from64x61(margin_result.available_margin), from64x61(
            margin_result.unrealized_pnl_sum), from64x61(margin_result.maintenance_margin_requirement),
        from64x61(margin_result.least_collateral_ratio), margin_result.least_collateral_ratio_position, from64x61(
            margin_result.least_collateral_ratio_position_asset_price)
    )

    starknet_position = list(least_collateral_ratio_position)
    formatted_starknet_position = starknet_position[:2] + [
        from64x61(x) for x in starknet_position[2:]]
    return (is_liquidation, total_margin, available_margin, unrealized_pnl_sum, maintenance_margin_requirement, least_collateral_ratio, formatted_starknet_position, least_collateral_ratio_position_asset_price)


def get_user_margin_info_python(user_test: User, order_executor: OrderExecutor, collateral_id: int, timestamp: int) -> Tuple[int, float, float, float, float, float, List, float]:
    (is_liquidation, total_margin, available_margin, unrealized_pnl_sum, maintenance_margin_requirement, least_collateral_ratio, least_collateral_ratio_position, least_collateral_ratio_position_asset_price) = user_test.get_margin_info(
        order_executor=order_executor, timestamp=timestamp, asset_id=collateral_id)
    formatted_python_position = list(
        least_collateral_ratio_position.values())
    return (is_liquidation, total_margin, available_margin, unrealized_pnl_sum, maintenance_margin_requirement, least_collateral_ratio, formatted_python_position, least_collateral_ratio_position_asset_price)


async def compare_margin_info(user: StarknetContract, user_test: User, order_executor: OrderExecutor, collateral_id: int, timestamp: int) -> None:

    (s_is_liquidation, s_total_margin, s_available_margin, s_unrealized_pnl_sum, s_maintenance_margin_requirement, s_least_collateral_ratio,
     s_least_collateral_ratio_position, s_least_collateral_ratio_position_asset_price) = await get_user_margin_info_starknet(user=user, collateral_id=collateral_id)

    (p_is_liquidation, p_total_margin, p_available_margin, p_unrealized_pnl_sum, p_maintenance_margin_requirement, p_least_collateral_ratio,
     p_least_collateral_ratio_position, p_least_collateral_ratio_position_asset_price) = get_user_margin_info_python(user_test=user_test, order_executor=order_executor, collateral_id=collateral_id, timestamp=timestamp)

    print("formatted starknet margin result", s_is_liquidation, s_total_margin, s_available_margin, s_unrealized_pnl_sum, s_maintenance_margin_requirement, s_least_collateral_ratio,
          s_least_collateral_ratio_position, s_least_collateral_ratio_position_asset_price)
    print("formatted python margin result", p_is_liquidation, p_total_margin, p_available_margin, p_unrealized_pnl_sum, p_maintenance_margin_requirement, p_least_collateral_ratio,
          p_least_collateral_ratio_position, p_least_collateral_ratio_position_asset_price)

    for element_1, element_2 in zip(p_least_collateral_ratio_position, s_least_collateral_ratio_position):
        assert element_1 == pytest.approx(element_2, abs=1e-4)

    # Compare starknet and python results
    assert s_is_liquidation == p_is_liquidation
    assert s_total_margin == pytest.approx(p_total_margin, abs=1e-3)
    assert s_available_margin == pytest.approx(p_available_margin, abs=1e-3)
    assert s_unrealized_pnl_sum == pytest.approx(
        p_unrealized_pnl_sum, abs=1e-3)
    assert s_maintenance_margin_requirement == pytest.approx(
        p_maintenance_margin_requirement, abs=1e-3)
    print("s_least_collateral_ratio", s_least_collateral_ratio)
    print("p_least_collateral_ratio", p_least_collateral_ratio)
    assert s_least_collateral_ratio == pytest.approx(
        p_least_collateral_ratio, abs=1e-3)
    assert s_least_collateral_ratio_position_asset_price == pytest.approx(
        p_least_collateral_ratio_position_asset_price, abs=1e-3)


# Function to check the result of a liquidation call


def compare_result_liquidation(python_result: Tuple[int, List, int, int], starknet_result: Tuple[int, List, int, int]):
    print("python_result", python_result)
    print("starknet_result", starknet_result)
    assert python_result[0] == starknet_result[0]

    for element_1, element_2 in zip(python_result[1], starknet_result[1]):
        print(element_1, element_2)
        assert element_1 == pytest.approx(element_2, abs=1e-3)


# Function to check if the batch status on starknet is as expected
async def check_batch_status(batch_id: int, trading: StarknetContract, is_executed: int):
    batch_status = await get_batch_status(batch_id=batch_id, trading=trading)
    assert batch_status == is_executed


# Compare user balance in starknet and python
async def compare_user_balances(users: List[StarknetContract], user_tests: List[User], asset_id: int):
    for i in range(len(users)):
        print("\n\nuser:", i)
        user_balance = await get_user_balance(user=users[i], asset_id=asset_id)
        # user_balance_python = get_user_balance_python(
        #     user=user_tests[i], asset_id=asset_id)

        user_locked_margin = await get_user_locked_margin(user=users[i], asset_id=asset_id)
        # user_locked_margin_python = get_user_locked_margin_python(
        #     user=user_tests[i], asset_id=asset_id)

        print("user_balance", user_balance)
        # print("user_balance_python", user_balance_python)
        print("user locked balance", user_locked_margin)
        # print("user locked balance python", user_locked_margin_python)
        # assert user_balance_python == pytest.approx(
        #     user_balance, abs=1e-6)

        # assert user_locked_margin_python == pytest.approx(
        #     user_locked_margin, abs=1e-6)


# Compare user positions on starknet and python
async def compare_user_positions(users: List[StarknetContract], users_test: List[User], market_id: int):
    for i in range(len(users)):
        print("\n\nuser:", i)
        # user_position_python_long = get_user_position_python(
        #     user=users_test[i], market_id=market_id, direction=order_direction["long"])
        # user_position_python_short = get_user_position_python(
        #     user=users_test[i], market_id=market_id, direction=order_direction["short"])

        user_position_starknet_long = await get_user_position(
            user=users[i], market_id=market_id, direction=order_direction["long"])
        user_position_starknet_short = await get_user_position(
            user=users[i], market_id=market_id, direction=order_direction["short"])

        # print("user_position_python_long", user_position_python_long)
        print("user_position_starknet_long", user_position_starknet_long)

        # print("user_position_python_short", user_position_python_short)
        print("user_position_starknet_short", user_position_starknet_short)

        # for element_1, element_2 in zip(user_position_python_long, user_position_starknet_long):
        #     assert element_1 == pytest.approx(element_2, abs=1e-4)

        # for element_1, element_2 in zip(user_position_python_short, user_position_starknet_short):
        #     assert element_1 == pytest.approx(element_2, abs=1e-4)


# Compare fund balances of starknet and python
async def compare_fund_balances(executor: OrderExecutor, holding: StarknetContract, liquidity: StarknetContract, fee_balance: StarknetContract, insurance: StarknetContract, asset_id: int):
    holding_fund_balance = await get_fund_balance(fund=holding, asset_id=asset_id, is_fee_balance=0)
    holding_fund_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["holding_fund"], asset_id=asset_id)
    print("holding_fund_balance", holding_fund_balance)
    print("holding_fund_balance_python", holding_fund_balance_python)
    assert holding_fund_balance_python == pytest.approx(
        holding_fund_balance, abs=1e-6)

    liquidity_fund_balance = await get_fund_balance(fund=liquidity, asset_id=asset_id, is_fee_balance=0)
    liquidity_fund_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["liquidity_fund"], asset_id=asset_id)
    print("liquidity_fund_balance", liquidity_fund_balance)
    print("liquidity_fund_balance_python", liquidity_fund_balance_python)
    assert liquidity_fund_balance_python == pytest.approx(
        liquidity_fund_balance, abs=1e-6)

    fee_balance_balance = await get_fund_balance(fund=fee_balance, asset_id=asset_id, is_fee_balance=1)
    fee_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["fee_balance"], asset_id=asset_id)
    print("fee_balance_balance", fee_balance_balance)
    print("fee_balance_python", fee_balance_python)
    assert fee_balance_python == pytest.approx(
        fee_balance_balance, abs=1e-6)

    insurance_balance = await get_fund_balance(fund=insurance, asset_id=asset_id, is_fee_balance=0)
    insurance_balance_python = get_fund_balance_python(
        executor=executor, fund=fund_mapping["insurance_fund"], asset_id=asset_id)

    print("insurance_balance", insurance_balance)
    print("insurance_balance_python", insurance_balance_python)
    assert insurance_balance_python == pytest.approx(
        insurance_balance, abs=1e-6)


# Assert that the liquidatable position on starknet and python class are the same
async def compare_liquidatable_position(user: StarknetContract, user_test: User, collateral_id: int):
    liquidatable_position_starknet = await get_liquidatable_position_starknet(user=user, collateral_id=collateral_id)
    liquidatable_position_python = get_liquidatable_position_python(
        user_test=user_test, collateral_id=collateral_id)

    print("liquidatable_position_starknet", liquidatable_position_starknet)
    print("liquidatable_position_python", liquidatable_position_python)

    for i in range(len(liquidatable_position_starknet)):
        assert liquidatable_position_python[i] == pytest.approx(
            liquidatable_position_starknet[i], abs=1e-3)


async def compare_abr_values(market_id: int, abr_core: StarknetContract, abr_executor: ABR, timestamp: int, python_abr: float, epoch: int):
    abr_query = await abr_core.get_abr_details(epoch, market_id).call()

    abr_executor.set_abr(market_id=market_id, new_abr=from64x61(
        abr_query.result.abr_value), timestamp=timestamp)

    (_, price) = abr_executor.get_abr(market_id)
    assert python_abr == pytest.approx(
        from64x61(abr_query.result.abr_value), abs=1e-4)
    assert price == from64x61(abr_query.result.abr_last_price)

    return (abr_query.result.abr_value, abr_query.result.abr_last_price)


# initialize users
# python_executor = OrderExecutor()
# alice_test = User(123456789987654323, 2)
# bob_test = User(123456789987654324, 1)

# # Set balances
# alice_test.set_balance(
#     new_balance=203, asset_id=market_to_collateral_mapping[BTC_USD_ID])
# bob_test.set_balance(
#     new_balance=203, asset_id=market_to_collateral_mapping[BTC_USD_ID])

# # Test open long-short positions
# (alice_long, _) = alice_test.create_order(leverage=5)
# print(alice_long)

# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], leverage=5)
# print(bob_short)

# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1,
#     BTC_USD_ID,
#     1000,
#     100
# )

# print("Alice positions:", alice_test.get_positions(),
#       alice_test.get_locked_margin())

# print("Bob positions:", bob_test.get_positions(),
#       bob_test.get_locked_margin())

# print("Alice balance before close", alice_test.get_balance())
# print("Bob balance before close", bob_test.get_balance())

################################################
# close open/short - 1) short position underwater
# deficit > available_margin
# available_margin < 0
# bob_test.set_balance(
#     new_balance=-1, asset_id=market_to_collateral_mapping[BTC_USD_ID])
# (alice_long, _) = alice_test.create_order(side=side["sell"], price=1500)
# print(alice_long)
# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], side=side["sell"], price=1500)
# print(bob_short)

# python_executor.set_market_price(
#     market_id=BTC_USD_ID, price=1500, current_timestamp=200)


# print("return values", alice_test.get_margin_info(
#     order_executor=python_executor, timestamp=100, asset_id=AssetID.USDC))
# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1,
#     BTC_USD_ID,
#     1500,
#     10
# )

# print("Alice balances:",
#       alice_test.get_locked_margin(), alice_test.get_balance())

# print("Bob balances:",
#       bob_test.get_locked_margin(), bob_test.get_balance())

################################################
# close open/short - 2) short position underwater
# deficit < available_margin
# reaches available_margin > 0
# (alice_long, _) = alice_test.create_order(side=side["sell"], price=1500)
# print(alice_long)
# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], side=side["sell"], price=1500)
# print(bob_short)
# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1,
#     BTC_USD_ID,
#     1500,
#     10
# )

# print("Alice balances:",
#       alice_test.get_locked_margin(), alice_test.get_balance())

# print("Bob balances:",
#       bob_test.get_locked_margin(), bob_test.get_balance())


################################################
# close open/short - 3) short position underwater
# defict <= available margin
# (alice_long, _) = alice_test.create_order(side=side["sell"], price=1500)
# print(alice_long)
# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], side=side["sell"], price=1500)
# print(bob_short)
# bob_test.set_balance(
#     new_balance=500, asset_id=market_to_collateral_mapping[BTC_USD_ID])
# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1,
#     BTC_USD_ID,
#     1500,
#     10
# )

# print("Alice balances:",
#       alice_test.get_locked_margin(), alice_test.get_balance())

# print("Bob balances:",
#       bob_test.get_locked_margin(), bob_test.get_balance())


################################################
# close open/short - 4) short position - 0 pnl
# net_account_value >= 0

# (alice_long, _) = alice_test.create_order(side=side["sell"], price=1000)
# print(alice_long)
# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], side=side["sell"], price=1000)
# print(bob_short)

# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1,
#     BTC_USD_ID,
#     1000,
#     10
# )

# print("Alice balances:",
#       alice_test.get_locked_margin(), alice_test.get_balance())

# print("Bob balances:",
#       bob_test.get_locked_margin(), bob_test.get_balance())

################################################
# close open/short - 5) short position - profit
# net_account_value >= 0

# (alice_long, _) = alice_test.create_order(side=side["sell"], price=900)
# print(alice_long)
# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], side=side["sell"], price=900)
# print(bob_short)

# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1,
#     BTC_USD_ID,
#     900,
#     10
# )

# print("Alice balances:",
#       alice_test.get_locked_margin(), alice_test.get_balance())

# print("Bob balances:",
#       bob_test.get_locked_margin(), bob_test.get_balance())


##########################################
### Testing for adjust quantity locked ###
##########################################

# # initialize users
# python_executor = OrderExecutor()
# alice_test = User(123456789987654323, 2)
# bob_test = User(123456789987654324, 1)
# charlie_test = User(123456789987654325, 3)
# dave_test = User(123456789987654326, 4)

# # Set balances
# alice_test.set_balance(
#     new_balance=100000, asset_id=market_to_collateral_mapping[BTC_USD_ID])
# bob_test.set_balance(
#     new_balance=100000, asset_id=market_to_collateral_mapping[BTC_USD_ID])
# charlie_test.set_balance(
#     new_balance=100000, asset_id=market_to_collateral_mapping[BTC_USD_ID])

# # Test open long-short positions
# (alice_long, _) = alice_test.create_order(leverage=5, quantity=1.5)
# print(alice_long)

# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], leverage=5, quantity=1.5)
# print(bob_short)

# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1.5,
#     BTC_USD_ID,
#     1000,
#     100
# )

# # Test open long-short positions
# (alice_long, _) = alice_test.create_order(
#     leverage=5, quantity=1.5)
# print(alice_long)

# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], leverage=5, quantity=1.5)
# print(bob_short)

# python_executor.execute_batch(
#     1,
#     [alice_long, bob_short],
#     [alice_test, bob_test],
#     1.6,
#     BTC_USD_ID,
#     1000,
#     100
# )


# # Test close long-short positions
# (alice_long, _) = alice_test.create_order(
#     leverage=5, quantity=1.8, side=side["sell"]
# )

# (charlie_short, _) = charlie_test.create_order(
#     leverage=5, quantity=2, direction=order_direction["short"]
# )

# (dave_short, _) = charlie_test.create_order(
#     leverage=5, quantity=2, direction=order_direction["short"]
# )

# (bob_short, _) = bob_test.create_order(
#     direction=order_direction["short"], leverage=5, quantity=4, side=side["sell"]
# )
# print(bob_short)

# python_executor.execute_batch(
#     1,
#     [alice_long, charlie_short, dave_short, bob_short],
#     [alice_test, charlie_test, dave_test, bob_test],
#     4,
#     BTC_USD_ID,
#     1000,
#     100
# )
