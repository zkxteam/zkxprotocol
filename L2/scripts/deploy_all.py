from helper import *
from utils import Signer


signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)

long_trading_fees = 12
short_trading_fees = 8
tier1_details = [0, 0, 1]
tier2_details = [100, 100, 3]
tier3_details = [500, 500, 4]
trade1_access = [1, 0, 0]
trade2_access = [1, 1, 0]
trade3_access = [1, 1, 1]

#
network = "goerli"

def deploy_all():
    # deploy Account Contracts
    # admin1 = deploy_command("Account", [str(signer1.public_key)], network, "Account1")
    # admin2 = deploy_command("Account", [str(signer2.public_key)], network, "Account2")
    # user1 = deploy_command("Account", [str(signer3.public_key)], network, "Account3")

    # deploy Admin Auth Contracts
    # admin_auth = deploy_command("AdminAuth", [admin1, admin2], network, "AdminAuth")
    admin_auth = deploy_command("AdminAuth", ["0x0258c7fd9f3b93377616f36aa98dee7662036edcb77b92d95af5ad40be667c5d", "0x018759214450497e7f3f650fa45ec6cec1796c0ad6cc3812ef290bfc50ed6fba"], network, "AdminAuth")

    # Append all the arguments
    argument_list = [long_trading_fees, short_trading_fees, admin_auth] + tier1_details + tier2_details + tier3_details + trade1_access + trade2_access + trade3_access
    arguments_list_str = list(map(str, argument_list))
    
    # Deploy the Trading fees Contract
    fees = deploy_command("TradingFees", arguments_list_str, network, "TradingFees")

    # Deploy Asset Contract
    asset = deploy_command("Asset", [admin_auth, admin_auth], network, "Asset")

    # Deploy Market Contract
    market = deploy_command("Markets", [admin_auth, asset], network, "Markets")

    # Deploy FeeBalance Contract
    feeBalance = deploy_command("FeeBalance", [admin_auth], network, "FeeBalance")

    # Deploy Holding Contract
    holding = deploy_command("Holding", [admin_auth], network, "Holding")

    # Deploy Emergency Fund Contract
    emergencyFund = deploy_command("EmergencyFund", [admin_auth, holding], network, "EmergencyFund")

    # Deploy Liquidity fund Contract
    liquidityFund = deploy_command("LiquidityFund", [admin_auth], network, "LiquidityFund")

    # Deploy Trading Contract
    trading = deploy_command("Trading", [asset, fees, holding, feeBalance, market, liquidityFund], network, "Trading")

    #Deploy Registry Contract
    registry = deploy_command("AuthorizedRegistry", [admin_auth], network, "AuthorizedRegistry")

    #Deploy Liquidate Contract
    liquidate = deploy_command("Liquidate", [registry, asset], network, "Liquidate")

deploy_all()