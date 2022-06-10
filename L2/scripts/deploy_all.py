from helper import *
from utils import Signer


signer1 = Signer(123456789987654321)
signer2 = Signer(123456789987654322)
signer3 = Signer(123456789987654323)

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

    #Deploy Authorized Registry Contract
    registry = deploy_command("AuthorizedRegistry", [admin_auth], network, "AuthorizedRegistry")

    #Deploy Account Registry Contract
    accountRegistry = deploy_command("AccountRegistry", [registry, 1], network, "AccountRegistry")

    # Deploy the Fee Discount Contract
    feeDiscount = deploy_command("FeeDiscount", [], network, "FeeDiscount")
    
    # Deploy the Trading fees Contract
    fees = deploy_command("TradingFees", [registry, 1], network, "TradingFees")

    # Deploy Asset Contract
    asset = deploy_command("Asset", [registry, 1], network, "Asset")

    # Deploy Market Contract
    market = deploy_command("Markets", [registry, 1], network, "Markets")

    # Deploy FeeBalance Contract
    feeBalance = deploy_command("FeeBalance", [registry, 1], network, "FeeBalance")

    # Deploy Holding Contract
    holding = deploy_command("Holding", [registry, 1], network, "Holding")

    # Deploy Emergency Fund Contract
    emergencyFund = deploy_command("EmergencyFund", [registry, 1], network, "EmergencyFund")
    
    # Deploy Insurance Fund Contract
    insuranceFund = deploy_command("InsuranceFund", [registry, 1], network, "InsuranceFund")

    # Deploy Liquidity Fund Contract
    liquidityFund = deploy_command("LiquidityFund", [registry, 1], network, "LiquidityFund")

    # Deploy Trading Contract
    trading = deploy_command("Trading", [registry, 1], network, "Trading")

    # Deploy Liquidate Contract
    liquidate = deploy_command("Liquidate", [registry, 1], network, "Liquidate")

deploy_all()