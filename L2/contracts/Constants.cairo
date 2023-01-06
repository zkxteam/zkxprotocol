%lang starknet

const AdminAuth_INDEX = 0;
const Asset_INDEX = 1;
const Market_INDEX = 2;
const FeeDiscount_INDEX = 3;
const TradingFees_INDEX = 4;
const Trading_INDEX = 5;
const FeeBalance_INDEX = 6;
const Holding_INDEX = 7;
const EmergencyFund_INDEX = 8;
const LiquidityFund_INDEX = 9;
const InsuranceFund_INDEX = 10;
const Liquidate_INDEX = 11;
const L1_ZKX_Address_INDEX = 12;
const CollateralPrices_INDEX = 13;
const AccountRegistry_INDEX = 14;
const WithdrawalFeeBalance_INDEX = 15;
const WithdrawalRequest_INDEX = 16;
const ABR_INDEX = 17;
const ABR_FUNDS_INDEX = 18;
const ABR_PAYMENT_INDEX = 19;
const AccountDeployer_INDEX = 20;
const MarketPrices_INDEX = 21;
const PubkeyWhitelister_INDEX = 22;
const SigRequirementsManager_INDEX = 23;
const Hightide_INDEX = 24;
const TradingStats_INDEX = 25;
const UserStats_INDEX = 26;
const Starkway_INDEX = 27;
const Settings_INDEX = 28;
const RewardsCalculation_INDEX = 29;
const HighTideCalc_INDEX = 30;

// Indices for Relay,  Relay_Index = (Underlying contract index) x 100

const RelayAsset_INDEX = 100;
const RelayMarket_INDEX = 200;
const RelayFeeDiscount_INDEX = 300;
const RelayTradingFees_INDEX = 400;
const RelayTrading_INDEX = 500;
const RelayFeeBalance_INDEX = 600;
const RelayHolding_INDEX = 700;
const RelayEmergencyFund_INDEX = 800;
const RelayLiquidityFund_INDEX = 900;
const RelayInsuranceFund_INDEX = 1000;
const RelayLiquidate_INDEX = 1100;
const RelayAccountRegistry_INDEX = 1400;
const RelayABR_INDEX = 1700;
const RelayABRPayment_INDEX = 1900;

const MasterAdmin_ACTION = 0;
const ManageAssets_ACTION = 1;
const ManageMarkets_ACTION = 2;
const ManageAuthRegistry_ACTION = 3;
const ManageFeeDetails_ACTION = 4;
const ManageFunds_ACTION = 5;
const ManageGovernanceToken_ACTION = 6;
const ManageCollateralPrices_ACTION = 7;
const ManageHighTide_ACTION = 8;
const ManageSettings_ACTION = 9;
const TokenLister_ACTION = 10;

const POSITION_OPENED = 1;
const POSITION_TO_BE_DELEVERAGED = 2;
const POSITION_TO_BE_LIQUIDATED = 3;
const POSITION_LIQUIDATED = 4;

const MARKET_ORDER = 1;
const LIMIT_ORDER = 2;
const STOP_ORDER = 3;
const LIQUIDATION_ORDER = 4;
const DELEVERAGING_ORDER = 5;

const LONG = 1;
const SHORT = 2;

const MAKER = 1;
const TAKER = 2;

const WITHDRAWAL_INITIATED = 0;
const WITHDRAWAL_SUCCEEDED = 1;

const HIGHTIDE_INITIATED = 1;
const HIGHTIDE_ACTIVE = 2;

const FoK = 2;
const IoC = 3;

const OPEN = 1;
const CLOSE = 2;

const SEASON_CREATED = 1;
const SEASON_STARTED = 2;
const SEASON_ENDED = 3;
