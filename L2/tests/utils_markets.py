"""Utilities for dealing with markets in tests."""

from utils_links import prepare_starknet_string
from dataclasses import dataclass

@dataclass
class MarketProperties:
  id: int
  asset: int
  asset_collateral: int
  leverage: int
  is_tradable: bool
  is_archived: bool
  ttl: int
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
  metadata_link: str = ""

  def to_params_list(self):
    return [
      self.id, 
      self.asset, 
      self.asset_collateral, 
      self.leverage, 
      self.is_tradable, 
      self.is_archived, 
      self.ttl,
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
    ] + prepare_starknet_string(self.metadata_link)

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
