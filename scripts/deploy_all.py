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
    admin1 = deploy_command("Account", [str(signer1.public_key)], network, "Account1")
    admin2 = deploy_command("Account", [str(signer2.public_key)], network, "Account2")
    user1 = deploy_command("Account", [str(signer2.public_key)], network, "Account3")

    # deploy Admin Auth Contracts
    admin_auth = deploy_command("AdminAuth", [admin1, admin2], network, "AdminAuth")

    # Append all the arguments
    argument_list = [long_trading_fees, short_trading_fees, admin_auth] + tier1_details + tier2_details + tier3_details + trade1_access + trade2_access + trade3_access
    arguments_list_str = list(map(str, argument_list))
    
    # deploy the fees Contract
    fees = deploy_command("TradingFees", arguments_list_str, network, "TradingFees")


deploy_all()