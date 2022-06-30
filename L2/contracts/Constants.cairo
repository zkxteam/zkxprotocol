%lang starknet

const AdminAuth_INDEX = 0
const Asset_INDEX = 1
const Market_INDEX = 2
const FeeDiscount_INDEX = 3
const TradingFees_INDEX = 4
const Trading_INDEX = 5
const FeeBalance_INDEX = 6
const Holding_INDEX = 7
const EmergencyFund_INDEX = 8
const LiquidityFund_INDEX = 9
const InsuranceFund_INDEX = 10
const Liquidate_INDEX = 11
const RiskManagement_INDEX = 12
const LiquidatorAddress_INDEX = 13
const AccountRegistry_INDEX = 14
const WithdrawalFeeBalance_INDEX = 15
const WithdrawalRequest_INDEX = 16
const ABR_INDEX = 17
const ABR_FUNDS_INDEX = 18
const ABR_PAYMENT_INDEX = 19

# Indices for Relay,  Relay_Index = (Underlying contract index) x 100

const RelayAsset_INDEX = 100
const RelayMarket_INDEX = 200
const RelayFeeDiscount_INDEX = 300
const RelayTradingFees_INDEX = 400
const RelayTrading_INDEX = 500
const RelayFeeBalance_INDEX = 600
const RelayHolding_INDEX = 700
const RelayEmergencyFund_INDEX = 800
const RelayLiquidityFund_INDEX = 900
const RelayInsuranceFund_INDEX = 1000
const RelayLiquidate_INDEX = 1100
const RelayAccountRegistry_INDEX = 1400

const MasterAdmin_ACTION = 0
const ManageAssets_ACTION = 1
const ManageMarkets_ACTION = 2
const ManageAuthRegistry_ACTION = 3
const ManageFeeDetails_ACTION = 4
const ManageFunds_ACTION = 5
