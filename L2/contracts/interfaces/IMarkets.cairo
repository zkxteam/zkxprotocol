%lang starknet

from contracts.DataTypes import Market

@contract_interface
namespace IMarkets {
    ////////////////////////
    // External functions //
    ////////////////////////

    func add_market(new_market_: Market, metadata_link_len: felt, metadata_link: felt*) {
    }

    func remove_market(market_id_: felt) {
    }

    func modify_leverage(market_id_: felt, leverage_: felt) {
    }

    func modify_tradable(market_id_: felt, is_tradable_: felt) {
    }

    func modify_archived_state(market_id_: felt, is_archived_: felt) {
    }

    func modify_trade_settings(
        market_id_: felt,
        tick_size_: felt,
        step_size_: felt,
        minimum_order_size_: felt,
        minimum_leverage_: felt,
        maximum_leverage_: felt,
        currently_allowed_leverage_: felt,
        maintenance_margin_fraction_: felt,
        initial_margin_fraction_: felt,
        incremental_initial_margin_fraction_: felt,
        incremental_position_size_: felt,
        baseline_position_size_: felt,
        maximum_position_size_: felt
    ) {
    }

    func change_max_ttl(new_max_ttl_: felt) {
    }

    func change_max_leverage(new_max_leverage_: felt) {
    }

    func update_metadata_link(market_id_: felt, link_len: felt, link: felt*) {
    }

    ////////////////////
    // View functions //
    ////////////////////

    func get_asset_collateral_from_market(market_id_: felt) -> (
        asset_id: felt, collateral_id: felt
    ) {
    }

    func get_ttl_from_market(market_id_: felt) -> (ttl: felt) {
    }

    func get_market(market_id_: felt) -> (currMarket: Market) {
    }

    func get_market_id_from_assets(asset_id_: felt, collateral_id_: felt) -> (market_id: felt) {
    }

    func get_asset_collateral_from_market(market_id_: felt) -> (
        asset_id: felt, collateral_id: felt
    ) {
    }

    func get_maintenance_margin(market_id_: felt) -> (maintenance_margin: felt) {
    }

    func get_ttl_from_market(market_id_: felt) -> (ttl: felt) {
    }

    func get_all_markets_by_state(is_tradable_: felt, is_archived_: felt) -> (
        array_list_len: felt, array_list: Market*
    ) {
    }
<<<<<<< HEAD
}
=======

    func get_all_markets_by_state(is_tradable_: felt, is_archived_: felt) -> (
        array_list_len: felt, array_list: Market*
    ) {
    }

    func get_maintenance_margin(market_id_: felt) -> (maintenance_margin: felt) {
    }

    func get_metadata_link(market_id_: felt) -> (link_len: felt, link: felt*) {
    }
}
>>>>>>> ZKX-864-Intermediate-Merge-Branch
