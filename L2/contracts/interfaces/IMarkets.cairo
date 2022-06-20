%lang starknet

from contracts.DataTypes import Market

@contract_interface
namespace IMarkets:

    # external functions
    func addMarket(id : felt, newMarket : Market):
    end

    func removeMarket(id : felt):
    end

    func modifyLeverage(id : felt, leverage : felt):
    end

    func modifyTradable(id : felt, tradable : felt):
    end

    # view functions
    func getMarket(id : felt) -> (currMarket : Market):
    end
end
