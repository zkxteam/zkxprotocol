"""Utilities for dealing with assets in tests."""

from utils import str_to_felt
from utils_links import prepare_starknet_string, DEFAULT_LINK_1, DEFAULT_LINK_2

DEFAULT_ASSET_ICON_LINK = DEFAULT_LINK_1
DEFAULT_ASSET_METADATA_LINK = DEFAULT_LINK_2

def encode_asset_id_name(id, name):
  return str_to_felt(id), str_to_felt(name)

def build_default_asset_properties(
    id, 
    name,
    version = 1,
    is_tradable = 0,
    is_collateral = 0,
    decimals = 18,
    icon_link = DEFAULT_ASSET_ICON_LINK,
    metadata_link = DEFAULT_ASSET_METADATA_LINK
):
    return [
        id,
        version,
        name,
        is_tradable,
        is_collateral,
        decimals
    ] + prepare_starknet_string(icon_link) + prepare_starknet_string(metadata_link)

def build_asset_properties(
    id,
    name,
    version,
    is_tradable,
    is_collateral,
    decimals,
    icon_link = "",
    metadata_link = ""
):
    return [
        id, 
        version, 
        name, 
        is_tradable, 
        is_collateral, 
        decimals
    ] + prepare_starknet_string(icon_link) + prepare_starknet_string(metadata_link)