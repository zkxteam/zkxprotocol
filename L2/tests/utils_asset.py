"""Utilities for dealing with assets in tests."""

from utils import str_to_felt
from utils_links import prepare_starknet_string, DEFAULT_LINK_1, DEFAULT_LINK_2

class AssetID:
    ETH = str_to_felt("32f0406jz7qj8")
    USDC = str_to_felt("32f0406jz7qj7")
    DOT = str_to_felt("32f0406jz7qj6")
    TSLA = str_to_felt("32f0406jz7qj9")
    USDT = str_to_felt("32f0406jz7qj10")
    LINK = str_to_felt("32f0406jz7qj11")
    BTC = str_to_felt("32f0406jz7qj12")
    SUPER = str_to_felt("32f0406jz7qj20")
    DOGE = str_to_felt("32f0406jz7qj21")
    ADA = str_to_felt("32f0406jz7qj22")
    LUNA = str_to_felt("32f0406jz7qj23")
    UST = str_to_felt("yjk45lvmasopq")

DEFAULT_ASSET_ICON_LINK = DEFAULT_LINK_1
DEFAULT_ASSET_METADATA_LINK = DEFAULT_LINK_2

def encode_asset_id_name(id, name):
  return str_to_felt(id), str_to_felt(name)

def build_default_asset_properties(
    id,
    short_name,
    asset_version = 1,
    is_tradable = 0,
    is_collateral = 0,
    token_decimal = 18,
    icon_link = DEFAULT_ASSET_ICON_LINK,
    metadata_link = DEFAULT_ASSET_METADATA_LINK
):
    return build_asset_properties(
        id = id,
        short_name = short_name,
        asset_version = asset_version,
        is_tradable = is_tradable,
        is_collateral = is_collateral,
        token_decimal = token_decimal,
        icon_link = icon_link,
        metadata_link = metadata_link
    )

def build_asset_properties(
    id,
    short_name,
    asset_version,
    is_tradable,
    is_collateral,
    token_decimal,
    icon_link = "",
    metadata_link = ""
):
    return [
        id, 
        asset_version, 
        short_name, 
        is_tradable, 
        is_collateral, 
        token_decimal
    ] + prepare_starknet_string(icon_link) + prepare_starknet_string(metadata_link)