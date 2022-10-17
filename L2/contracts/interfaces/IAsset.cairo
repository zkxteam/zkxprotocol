%lang starknet

from contracts.DataTypes import Asset

@contract_interface
namespace IAsset {
    
    //////////////
    // External //
    //////////////

    func set_L1_zkx_address(l1_zkx_address: felt) {
    }

    func add_asset(
        new_asset: Asset, 
        icon_link_len: felt,
        icon_link: felt*,
        metadata_link_len: felt,
        metadata_link: felt*
    ) {
    }

    func remove_asset(id_to_remove: felt) {
    }

    func modify_core_settings(id: felt, short_name: felt, is_tradable: felt, is_collateral: felt) {
    }

    func update_icon_link(asset_id: felt, link_len: felt, link: felt*) {
    }

    func update_metadata_link(asset_id: felt, link_len: felt, link: felt*) {
    }

    //////////
    // View //
    //////////

    func get_L1_zkx_address() -> (res: felt) {
    }

    func get_asset(id: felt) -> (currAsset: Asset) {
    }

    func get_icon_link(id: felt) -> (link_len: felt, link: felt*) {
    }

    func get_metadata_link(id: felt) -> (link_len: felt, link: felt*) {
    }

    func get_version() -> (version: felt) {
    }

    func return_all_assets() -> (array_list_len: felt, array_list: Asset*) {
    }
}
