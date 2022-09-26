%lang starknet

from contracts.DataTypes import CoreFunction

@contract_interface
namespace ISigRequirementsManager {
    func set_sig_requirement(core_function: CoreFunction, num_req: felt) {
    }

    func deregister_func(core_function: CoreFunction) {
    }

    func assert_func_handled(core_function: CoreFunction) {
    }

    func get_sig_requirement(core_function: CoreFunction) -> (num_req: felt) {
    }
}
