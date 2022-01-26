%lang starknet

%builtins pedersen range_check ecdsa

from starkware.cairo.common.cairo_builtins import HashBuiltin, SignatureBuiltin

struct Asset:
    member ticker: felt
    member short_name: felt
    member tradable: felt
end

@storage_var
func asset_mapping(id : felt) -> (asset : Asset):
end


@view
func get_asset{
    syscall_ptr : felt*, 
    pedersen_ptr : HashBuiltin*,
    range_check_ptr
}(id: felt) -> (asset : Asset):
    let (asset) = asset_mapping.read(id=id)
    return (asset)
end

@external
func addAsset{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr} (assets_len: felt, assets: Asset*) -> () :
    if assets_len == 0:
        return ()
    end

    let tempAsset: Asset = Asset(ticker=[assets].ticker, short_name=[assets].short_name, tradable=[assets].tradable)
    asset_mapping.write(assets_len-1, tempAsset)
    addAsset(assets_len=assets_len-1, assets=assets+Asset.SIZE)
    return ()
end