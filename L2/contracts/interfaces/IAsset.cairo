%lang starknet

from contracts.DataTypes import Asset, AssetWID

@contract_interface
namespace IAsset:
    ######################
    # External functions #
    ######################

    func set_L1_zkx_address(l1_zkx_address : felt):
    end

    func addAsset(id : felt, new_asset : Asset):
    end

    func removeAsset(id_to_remove : felt):
    end

    func modify_core_settings(
        id : felt,
        short_name : felt,
        tradable : felt,
        collateral : felt,
        token_decimal : felt,
        metadata_id : felt,
    ):
    end

    func modify_trade_settings(
        id : felt,
        tick_size : felt,
        step_size : felt,
        minimum_order_size : felt,
        minimum_leverage : felt,
        maximum_leverage : felt,
        currently_allowed_leverage : felt,
        maintenance_margin_fraction : felt,
        initial_margin_fraction : felt,
        incremental_initial_margin_fraction : felt,
        incremental_position_size : felt,
        baseline_position_size : felt,
        maximum_position_size : felt,
    ):
    end

    ##################
    # View functions #
    ##################

    func get_L1_zkx_address() -> (res : felt):
    end

    func get_asset(id : felt) -> (currAsset : Asset):
    end

    func get_maintenance_margin(id : felt) -> (maintenance_margin : felt):
    end

    func get_version() -> (version : felt):
    end

    func return_all_assets() -> (array_list_len : felt, array_list : AssetWID*):
    end
end
