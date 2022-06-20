%lang starknet

@contract_interface
namespace IAdminAuth:
    func get_admin_mapping(address : felt, action : felt) -> (allowed : felt):
    end
end