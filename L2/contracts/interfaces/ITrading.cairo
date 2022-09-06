%lang starknet

from contracts.DataTypes import MultipleOrder

@contract_interface
namespace ITrading:
    # external functions

    func execute_batch(
        size : felt,
        execution_price : felt,
        marketID : felt,
        request_list_len : felt,
        request_list : MultipleOrder*,
    ) -> ():
    end
end
