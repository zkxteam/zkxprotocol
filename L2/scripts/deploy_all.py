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
    admin_auth = deploy_command("AdminAuth", ["0xd687a698b6c39372fc0ef753a03a71843d8399b673fe31aa9e56549f91a49d", "0x4f0650b2db56943974ab0b412a02448a40fe2287c5c2f4115b851cdc435fef4"], network, "AdminAuth")

    # Append all the arguments
    argument_list = [long_trading_fees, short_trading_fees, admin_auth] + tier1_details + tier2_details + tier3_details + trade1_access + trade2_access + trade3_access
    arguments_list_str = list(map(str, argument_list))
    
    # Deploy the Trading fees Contract
    fees = deploy_command("TradingFees", arguments_list_str, network, "TradingFees")

    # Deploy Asset Contract
    asset = deploy_command("Asset", [admin_auth], network, "Asset")

    # Deploy FeeBalance Contract
    feeBalance = deploy_command("FeeBalance", [admin_auth], network, "FeeBalance")

    # Deploy Holding Contract
    holding = deploy_command("Holding", [admin_auth], network, "Holding")

    # Deploy Emergency Fund Contract
    emergencyFund = deploy_command("EmergencyFund", [admin_auth, holding], network, "EmergencyFund")

    # Deploy Trading Contract
    trading = deploy_command("Trading", [asset, fees, holding, feeBalance], network, "Trading")

deploy_all()