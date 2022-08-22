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
const L1_ZKX_Address_INDEX = 12
const LiquidatorAddress_INDEX = 13
const AccountRegistry_INDEX = 14
const WithdrawalFeeBalance_INDEX = 15
const WithdrawalRequest_INDEX = 16
const ABR_INDEX = 17
const ABR_FUNDS_INDEX = 18
const ABR_PAYMENT_INDEX = 19
const AccountDeployer_INDEX = 20
const MarketPrices_INDEX = 21

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
const RelayABR_INDEX = 1700
const RelayABRpayment_INDEX = 1900

const MasterAdmin_ACTION = 0
const ManageAssets_ACTION = 1
const ManageMarkets_ACTION = 2
const ManageAuthRegistry_ACTION = 3
const ManageFeeDetails_ACTION = 4
const ManageFunds_ACTION = 5
const ManageGovernanceToken_ACTION = 6
const ManageCollateralPrices_ACTION = 7

const ORDER_INITIATED = 0
const ORDER_OPENED_PARTIALLY = 1
const ORDER_OPENED = 2
const ORDER_CLOSED_PARTIALLY = 3
const ORDER_CLOSED = 4
const ORDER_TO_BE_DELEVERAGED = 5
const ORDER_TO_BE_LIQUIDATED = 6
const ORDER_LIQUIDATED = 7

const MARKET_ORDER = 0
const LIMIT_ORDER = 1
const STOP_ORDER = 2
const LIQUIDATION_ORDER = 3
const DELEVERAGING_ORDER = 4

const LONG = 1
const SHORT = 0
