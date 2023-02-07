%lang starknet

@contract_interface
namespace IPubkeyWhitelister {
    // View functions

    func is_whitelisted(pubkey: felt) -> (res: felt) {
    }

    // External functions

    func whitelist_pubkey(pubkey: felt) {
    }
}
