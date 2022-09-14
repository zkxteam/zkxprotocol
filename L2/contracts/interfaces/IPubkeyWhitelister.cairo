%lang starknet

@contract_interface
namespace IPubkeyWhitelister:

    # external functions
    func whitelist_pubkey(pubkey:felt):
    end

    # view functions
    func is_whitelisted(pubkey: felt) -> (res: felt):
    end
end