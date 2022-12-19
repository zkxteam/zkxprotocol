import pytest
import asyncio
import random
import string
from utils_asset import AssetID
from utils import Signer, str_to_felt, assert_revert, hash_order, from64x61, to64x61
from typing import List, Dict, Tuple

BTC_USD_ID = str_to_felt("gecn2j0cm45sz")
BTC_UST_ID = str_to_felt("gecn2j0c12rtzxcmsz")
ETH_USD_ID = str_to_felt("k84azmn47vsj8az")
TSLA_USD_ID = str_to_felt("2jfk20ckwlmzaksc")
UST_USDC_ID = str_to_felt("2jfk20wert12lmzaksc")


def random_string(length):
    return str_to_felt(''.join(random.choices(string.ascii_letters + string.digits, k=length)))


order_types = {
    "market": 1,
    "limit": 2
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


async def set_balance_starknet(admin_signer, admin, user, asset_id, new_balance):
    await admin_signer.send_transaction(admin, user.contract_address, "set_balance", [asset_id, to64x61(new_balance)])
    return


def set_balance_python(user_test, asset_id, new_balance):
    user_test.set_balance(new_balance=new_balance, asset_id=asset_id)
    return


async def set_balance(admin_signer, admin, users, users_test, balance_array, asset_id):
    for i in range(len(users)):
        await set_balance_starknet(admin_signer=admin_signer, admin=admin, user=users[i], asset_id=asset_id, new_balance=balance_array[i])
        set_balance_python(
            user_test=users_test[i], asset_id=asset_id, new_balance=balance_array[i])
    return


async def execute_batch(zkx_node_signer, zkx_node, trading, execute_batch_params):
    # Send execute_batch transaction
    await zkx_node_signer.send_transaction(zkx_node, trading.contract_address, "execute_batch", execute_batch_params)
    return


async def execute_batch_reverted(zkx_node_signer, zkx_node, trading, execute_batch_params, error_message):
    # Send execute_batch transaction
    await assert_revert(
        zkx_node_signer.send_transaction(zkx_node, trading.contract_address, "execute_batch", execute_batch_params), reverted_with=error_message)
    return


async def execute_and_compare(zkx_node_signer, zkx_node, executor, orders, users_test, quantity_locked, market_id, oracle_price, trading, is_reverted, error_message):
    batch_id = random_string(10)
    complete_orders_python = []
    complete_orders_starknet = []
    # Fill the remaining order attributes
    for i in range(len(orders)):
        print("Order id is ", orders[i]["order_id"])
        if "order_id" in orders[i]:
            (multiple_order_format,
             multiple_order_format_64x61) = users_test[i].get_order(orders[i]["order_id"])
            complete_orders_python.append(multiple_order_format)
            complete_orders_starknet += multiple_order_format_64x61.values()
        else:
            (multiple_order_format,
             multiple_order_format_64x61) = users_test[i].create_order(**orders[i])
            complete_orders_python.append(multiple_order_format)
            complete_orders_starknet += multiple_order_format_64x61.values()

    execute_batch_params_starknet = [
        batch_id,
        to64x61(quantity_locked),
        market_id,
        to64x61(oracle_price),
        len(orders),
        *complete_orders_starknet
    ]

    execute_batch_params_python = [
        batch_id,
        complete_orders_python,
        users_test,
        quantity_locked,
        market_id,
        oracle_price
    ]

    if is_reverted:
        await execute_batch_reverted(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, trading=trading, execute_batch_params=execute_batch_params_starknet, error_message=error_message)
    else:
        await execute_batch(zkx_node_signer=zkx_node_signer, zkx_node=zkx_node, trading=trading, execute_batch_params=execute_batch_params_starknet)
        executor.execute_batch(*execute_batch_params_python)
    return (batch_id, complete_orders_python)


async def get_user_position(user, market_id, direction):
    user_starknet_query = await user.get_position_data(market_id_=market_id, direction_=direction).call()
    user_starknet_query_parsed = list(user_starknet_query.result.res)
    user_starknet_position = [from64x61(x)
                              for x in user_starknet_query_parsed]
    return user_starknet_position


def get_user_position_python(user, market_id, direction):
    user_python_query = user.get_position(
        market_id=market_id, direction=direction)
    return list(user_python_query.values())


async def get_fund_balance(fund, asset_id, is_fee_balance):
    result = 0
    if is_fee_balance:
        result = await fund.get_total_fee(assetID_=asset_id).call()
        return from64x61(result.result.fee)
    else:
        result = await fund.balance(asset_id_=asset_id).call()
        return from64x61(result.result.amount)


def get_fund_balance_python(executor, fund, asset_id):
    return executor.get_fund_balance(fund, asset_id)


async def get_user_balance(user, asset_id):
    user_query = await user.get_balance(assetID_=asset_id).call()
    return from64x61(user_query.result.res)


def get_user_balance_python(user, asset_id):
    return user.get_balance(asset_id)


async def compare_user_balances(users, user_tests, asset_id):
    for i in range(len(users)):
        user_balance = await get_user_balance(user=users[i], asset_id=asset_id)
        user_balance_python = get_user_balance_python(
            user=user_tests[i], asset_id=asset_id)

        assert user_balance_python == pytest.approx(
            user_balance, abs=1e-6)
    return


async def compare_user_positions(users, users_test, market_id):
    for i in range(len(users)):
        user_position_python_long = get_user_position_python(
            user=users_test[i], market_id=market_id, direction=order_direction["long"])
        user_position_python_short = get_user_position_python(
            user=users_test[i], market_id=market_id, direction=order_direction["short"])

        user_position_starknet_long = await get_user_position(
            user=users[i], market_id=market_id, direction=order_direction["long"])
        user_position_starknet_short = await get_user_position(
            user=users[i], market_id=market_id, direction=order_direction["short"])

        print("user", i)
        print(user_position_python_long)
        print(user_position_starknet_long)
        print(user_position_python_short)
        print(user_position_starknet_short)

        for element_1, element_2 in zip(user_position_python_long, user_position_starknet_long):
            assert element_1 == pytest.approx(element_2, abs=1e-6)

        for element_1, element_2 in zip(user_position_python_short, user_position_starknet_short):
            assert element_1 == pytest.approx(element_2, abs=1e-6)


async def compare_fund_balances(executor, holding, liquidity, fee_balance, insurance, asset_id):
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
    return


class User:
    def __init__(self, private_key: int, user_address: int, liquidator_private_key=0):
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
            "close_order": order["close_order"],
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
            "close_order": order["close_order"],
        }

        return multiple_order

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

    def get_portion_executed(self, order_id: int) -> int:
        try:
            return self.portion_executed[order_id]
        except KeyError:
            return 0

    def modify_balance(self, mode, asset_id, amount):
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
                isPresent = 1

        if not is_present:
            collaterals.append(asset_id)

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

    def set_deleveragable_or_liquidatable_position(self, updated_position):
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

        self.__set_portion_executed(
            order_id=order["order_id"], new_amount=new_portion_executed)

        if order["close_order"] == 1:
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

            self.positions[order["market_id"]] = {
                order["direction"]: updated_position
            }

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

                if order["order_type"] == order_types["deleveraging_order"]:
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

            self.positions[order["market_id"]] = {
                parent_direction: updated_position
            }

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

    def get_order(self, order_id: int) -> Dict:
        python_order = self.orders_decimal[order_id]
        starknet_order = self.orders[order_id]
        return (python_order, starknet_order)

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
        close_order: int = close_order["open"],
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
        assert close_order in (1, 2), "Invalid close_order"

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
            "close_order": close_order,
            "liquidator_address": liquidator_address
        }
        signed_order = [0, 0]
        multiple_order_format = self.__get_multiple_order_representation(
            new_order, signed_order, liquidator_address)

        self.orders_decimal[new_order["order_id"]] = multiple_order_format

        # Convert to 64x61 format for starknet
        order_64x61 = self.__convert_order_to_64x61(new_order)
        multiple_order_format_64x61 = self.__create_order_starknet(
            order_64x61, liquidator_address)
        return (multiple_order_format, multiple_order_format_64x61)


class OrderExecutor:
    def __init__(self):
        self.maker_trading_fees = 0.0002 * 0.97
        self.taker_trading_fees = 0.0005 * 0.97
        self.fund_balances = {}
        self.batch_id_status = {}

    def set_fund_balance(self, fund: int, asset_id: int, new_balance: float):
        self.fund_balances[fund] = {
            asset_id: new_balance
        }

    def get_fund_balance(self, fund: int, asset_id: int) -> int:
        try:
            return self.fund_balances[fund][asset_id]
        except KeyError:
            return 0

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
            asset_id=market_to_asset_mapping[order["market_id"]],
        )

        if user_balance <= balance_to_be_deducted:
            print("Low balance", balance_to_be_deducted, user_balance)
            return (0, 0, 0)

        user.modify_balance(
            mode=fund_mode["defund"], asset_id=market_to_asset_mapping[order["market_id"]], amount=balance_to_be_deducted)
        self.__modify_fund_balance(fund=fund_mapping["fee_balance"], mode=fund_mode["fund"],
                                   asset_id=market_to_asset_mapping[order["market_id"]], amount=fees)
        self.__modify_fund_balance(fund=fund_mapping["holding_fund"], mode=fund_mode["fund"],
                                   asset_id=market_to_asset_mapping[order["market_id"]], amount=leveraged_position_value)

        if order["leverage"] > 1:
            self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["defund"],
                                       asset_id=market_to_asset_mapping[order["market_id"]], amount=amount_to_be_borrowed)

        return (average_execution_price, margin_amount, borrowed_amount)

    def __process_close_orders(self, user: User, order: Dict, execution_price: float, order_size: float, market_id) -> Tuple[float, float, float]:
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
                                   asset_id=market_to_asset_mapping[order["market_id"]], amount=leveraged_amount_out)

        if order["order_type"] == 4:
            borrowed_amount = borrowed_amount - leveraged_amount_out
        else:
            borrowed_amount -= borrowed_amount_to_be_returned
            margin_amount -= margin_amount_to_be_reduced

        if order["order_type"] <= 3:
            if position["leverage"] > 1:
                self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
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
                self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
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
                        self.__modify_fund_balance(fund=fund_mapping["insurance_fund"], mode=fund_mode["defund"],
                                                   asset_id=market_to_asset_mapping[order["market_id"]], amount=deficit - user_balance)
            else:
                self.__modify_fund_balance(fund=fund_mapping["liquidity_fund"], mode=fund_mode["fund"],
                                           asset_id=market_to_asset_mapping[order["market_id"]], amount=leveraged_amount_out)

        return (average_execution_price, margin_amount, borrowed_amount)

    def __get_fee(self, user: User, side: int):
        # ToDo change this logic when we add user discounts
        # Fee rate
        return self.maker_trading_fees if side == 1 else self.taker_trading_fees

    def get_batch_id_status(self, batch_id: int):
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

                if quantity_remaining < request_list[i]["quantity"]:
                    quantity_to_execute = quantity_remaining
                else:
                    quantity_to_execute = request_list[i]["quantity"]

                quantity_executed += quantity_to_execute
                execution_price = request_list[i]["price"]

                running_weighted_sum += execution_price*quantity_to_execute

                side = order_side["maker"]

            if request_list[i]["close_order"] == 1:
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


class Liquidator:
    def __init__(self):
        self.maintenance_margin = 0.075
        self.maintenance_requirement = 0
        self.total_account_value_collateral = 0

    def __set_debugging_values(self, maintenance_requirement: float, total_account_value_collateral: float):
        self.maintenance_requirement = maintenance_requirement
        self.total_account_value_collateral = total_account_value_collateral

    def get_debugging_values(self) -> Tuple[float, float]:
        return (self.maintenance_requirement, self.total_account_value_collateral)

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

    def check_for_liquidation(self, user: User, prices_array: List[Dict]) -> Tuple[int, Dict]:
        positions = user.get_positions()

        if len(positions) == 0:
            print("Liquidator: Empty positions array")
            return

        if len(prices_array) != len(prices_array):
            print("Liquidator: Invalid prices array")
            return

        least_collateral_ratio = 0
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
                    prices_array["asset_price"]

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
        user_balance = self.__find_collateral_balance(
            prices_array=prices_array[len(positions):],
            collateral_array=collaterals_array
        )
        print("user_balance", user_balance)
        print("total_account_value", total_account_value)

        total_account_value_collateral = total_account_value + user_balance

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


alice = User(123456, 0x123234324)
bob = User(73879, 0x1234589402)

alice.set_balance(5500, AssetID.USDC)
bob.set_balance(6000, AssetID.USDC)

(order_long, order_long_64x61) = alice.create_order(
    quantity=2, order_type=order_types["limit"], price=1000, leverage=2)
(order_short, order_short_64x61) = bob.create_order(
    quantity=2, direction=order_direction["short"], leverage=2)

request_list = [order_long, order_short]

print(request_list)
executoor = OrderExecutor()
executoor.execute_batch(random_string(10),
                        request_list, [alice, bob], 2, BTC_USD_ID, 1000)
# print("alice_position:", alice.get_positions())
# print("bob_position:", bob.get_positions())

# liquidatoor = Liquidator()

# (order_short, order_short_64x61) = bob.create_order(
#     quantity=1, direction=order_direction["short"], side=order_side["taker"])
# print("long order", order_long)
# print("short order", order_short)
# # ORder 1


# executoor.execute_batch(
#     request_list, [alice, bob], 1, BTC_USD_ID, 1000)

# (order_short, order_short_64x61) = bob.create_order(
#     quantity=3, leverage=1, direction=order_direction["short"], side=order_side["taker"])


# request_list = [order_long, order_short]
# executoor.execute_batch(
#     request_list, [alice, bob], 3, BTC_USD_ID, 1020)
# print("alice_position:", alice.get_positions())
# print(alice.get_balance(AssetID.USDC))

# print("alice collaterals:", alice.get_collaterals())

# prices_array = [
#     {"asset_id": 0,
#      "collateral_id": AssetID.USDC,
#      "asset_price": 500,
#      "collateral_price": 0.99
#      }, {
#         "asset_id": 0,
#         "collateral_id": AssetID.USDC,
#         "asset_price": 0,
#         "collateral_price": 0.99
#     }, {
#         "asset_id": 0,
#         "collateral_id": AssetID.UST,
#         "asset_price": 0,
#         "collateral_price": 0.0001
#     }]
# result = liquidatoor.check_for_liquidation(
#     user=alice, prices_array=prices_array)
# print(result)
# liq_position = alice.get_deleveragable_or_liquidatable_position()
# print(liq_position)

# (order_short, order_short_64x61) = bob.create_order(
#     quantity=3, leverage=1, direction=order_direction["short"], side=order_side["taker"])


# request_list = [order_long, order_short]
# executoor.execute_batch(
#     request_list, [alice, bob], 3, BTC_USD_ID, 1020)
# print("alice_position:", alice.get_positions())
# print(alice.get_balance(AssetID.USDC))

# request_list = [order_long, order_short]
# executoor.execute_batch(
#     request_list, [alice, bob], 3, BTC_USD_ID, 1020)
# print("alice_position:", alice.get_positions())
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
