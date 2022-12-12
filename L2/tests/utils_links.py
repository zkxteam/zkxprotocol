"""Utilities for dealing with links in tests."""

from utils import str_to_felt;

DEFAULT_LINK_1 = "https://ipfs.io/ipfs/Qme7ss3ARVgxv6rXqVPiikMJ8u2NLgmgszg13pYrDKEoiu"
DEFAULT_LINK_2 = "https://ipfs.io/ipfs/Qme7ss3ARVgxv6rXqVPZkxBrandNewMetadataLinksfaf"

def prepare_starknet_string(string):
    return [len(string)] + encode_characters(string)

def encode_characters(string):
    result = []
    for c in string:
        result.append(str_to_felt(c))
    return result