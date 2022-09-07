%lang starknet

from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_zero

from contracts.Constants import MasterAdmin_ACTION
from contracts.libraries.Utils import verify_caller_authority

###########
# Events  #
###########

# this event is emitted whenever contract version is changed by the admin
@event
func contract_version_changed(new_version : felt):
end

# this event is emitted whenever authorized registry contract address is changed by the admin
@event
func registry_address_changed(new_address : felt):
end

###########
# Storage #
###########

# Stores the contract version
@storage_var
func CommonLib_contract_version() -> (version : felt):
end

# Stores the address of Authorized Registry contract
@storage_var
func CommonLib_registry_address() -> (contract_address : felt):
end

namespace CommonLib:

    # @notice function to initialize registry address and contract version
    # @param resgitry_address_ Address of the AuthorizedRegistry contract
    # @param contract_version_ Version of this contract
    func initialize{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        registry_address_ : felt, contract_version_ : felt
    ):
        with_attr error_message("Registry address and version cannot be 0"):
            assert_not_zero(registry_address_)
            assert_not_zero(contract_version_)
        end

        CommonLib_registry_address.write(value=registry_address_)
        CommonLib_contract_version.write(value=contract_version_)
        return ()
    end

    ##################
    # View Functions #
    ##################

    # @notice view function to get current contract version
    # @return contract_version - version of the contract
    @view
    func get_contract_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ) -> (contract_version : felt):
        let (current_contract_version) = CommonLib_contract_version.read()
        return (current_contract_version)
    end

    # @notice view function to get the address of Authorized registry contract
    # @return registry_address - Address of Authorized registry contract
    @view
    func get_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
        ) -> (registry_address : felt):
        let (current_registry_address) = CommonLib_registry_address.read()
        return (current_registry_address)
    end

    ######################
    # External Functions #
    ######################

    # @notice external function to set contract version
    # @param new_version_ - new version of the contract
    @external
    func set_contract_version{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    new_version_ : felt
    ):
        let (current_registry_address) = CommonLib_registry_address.read()
        let (current_contract_version) = CommonLib_contract_version.read()

        verify_caller_authority(current_registry_address, current_contract_version, MasterAdmin_ACTION)

        with_attr error_message("contract version cannot be 0"):
            assert_not_zero(new_version_)
        end

        CommonLib_contract_version.write(value=new_version_)
        contract_version_changed.emit(new_version=new_version_)
        return ()
    end

    # @notice external function to set authorized registry contract address
    # @param resgitry_address_ Address of the AuthorizedRegistry contract
    @external
    func set_registry_address{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
    registry_address_ : felt
    ):
        let (current_registry_address) = CommonLib_registry_address.read()
        let (current_contract_version) = CommonLib_contract_version.read()

        verify_caller_authority(current_registry_address, current_contract_version, MasterAdmin_ACTION)

        with_attr error_message("Registry address cannot be 0"):
            assert_not_zero(registry_address_)
        end

        CommonLib_registry_address.write(value=registry_address_)
        registry_address_changed.emit(new_address=registry_address_)
        return ()
    end
end