%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin

struct Order:
    member price : felt
    member size : felt
end

struct Asset:
    member ticker: felt
    member short_name: felt
    member tradable: felt
    member executedOrders: Order*
end

@storage_var
func asset_mapping(id : felt) -> (asset : Asset):
end

