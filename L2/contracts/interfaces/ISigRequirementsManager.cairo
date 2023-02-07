%lang starknet

from contracts.DataTypes import CoreFunction

@contract_interface
namespace ISigRequirementsManager {
    // View functions

    func get_sig_requirement(core_function: CoreFunction) -> (num_req: felt) {
    }

    // External functions

    func set_sig_requirement(core_function: CoreFunction, num_req: felt) {
    }

    func deregister_func(core_function: CoreFunction) {
    }

    func assert_func_handled(core_function: CoreFunction) {
    }
}
