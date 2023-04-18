"""Utilities for dealing with markets in tests."""

from utils_links import prepare_starknet_string
from dataclasses import dataclass
from utils import from64x61


@dataclass
class MarketProperties:
    id: int
    asset: int
    asset_collateral: int
    is_tradable: bool
    is_archived: bool
    ttl: int
    tick_size: int
    tick_precision: int
    step_size: int
    step_precision: int
    minimum_order_size: int
    minimum_leverage: int
    maximum_leverage: int
    currently_allowed_leverage: int
    maintenance_margin_fraction: int
    initial_margin_fraction: int
    incremental_initial_margin_fraction: int
    incremental_position_size: int
    baseline_position_size: int
    maximum_position_size: int
    metadata_link: str = ""

    def to_params_list(self):
        return [
            self.id,
            self.asset,
            self.asset_collateral,
            self.is_tradable,
            self.is_archived,
            self.ttl,
            self.tick_size,
            self.tick_precision,
            self.step_size,
            self.step_precision,
            self.minimum_order_size,
            self.minimum_leverage,
            self.maximum_leverage,
            self.currently_allowed_leverage,
            self.maintenance_margin_fraction,
            self.initial_margin_fraction,
            self.incremental_initial_margin_fraction,
            self.incremental_position_size,
            self.baseline_position_size,
            self.maximum_position_size
        ] + prepare_starknet_string(self.metadata_link)

    def to_dict(self):
        return {
            "id": self.id,
            "asset": self.asset,
            "asset_collateral": self.asset_collateral,
            "is_tradable": self.is_tradable,
            "is_archived": self.is_archived,
            "ttl": self.ttl,
            "tick_size": self.tick_size,
            "tick_precision": self.tick_precision,
            "step_size": self.step_size,
            "step_precision": self.step_precision,
            "minimum_order_size": from64x61(self.minimum_order_size),
            "minimum_leverage": from64x61(self.minimum_leverage),
            "maximum_leverage": from64x61(self.maximum_leverage),
            "currently_allowed_leverage": from64x61(self.currently_allowed_leverage),
            "maintenance_margin_fraction": from64x61(self.maintenance_margin_fraction),
            "initial_margin_fraction": self.initial_margin_fraction,
            "incremental_initial_margin_fraction": self.incremental_initial_margin_fraction,
            "incremental_position_size": self.incremental_position_size,
            "baseline_position_size": self.baseline_position_size,
            "maximum_position_size": self.maximum_position_size,
            "metadata_link": self.metadata_link
        }


@dataclass
class MarketTradeSettings:
    id: int
    tick_size: int
    step_size: int
    minimum_order_size: int
    minimum_leverage: int
    maximum_leverage: int
    currently_allowed_leverage: int
    maintenance_margin_fraction: int
    initial_margin_fraction: int
    incremental_initial_margin_fraction: int
    incremental_position_size: int
    baseline_position_size: int
    maximum_position_size: int

    def to_params_list(self):
        return [
            self.id,
            self.tick_size,
            self.step_size,
            self.minimum_order_size,
            self.minimum_leverage,
            self.maximum_leverage,
            self.currently_allowed_leverage,
            self.maintenance_margin_fraction,
            self.initial_margin_fraction,
            self.incremental_initial_margin_fraction,
            self.incremental_position_size,
            self.baseline_position_size,
            self.maximum_position_size
        ]
