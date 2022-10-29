from enum import Enum
from cachetools import LRUCache
from starkware.starknet.core.os.class_hash import set_class_hash_cache
from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.starknet import Starknet
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.state import StarknetState
from starkware.starknet.services.api.contract_class import ContractClass

class ContractType(Enum):
    Account = "tests/contracts/Account.cairo"
    AccountManager = "tests/testable/TestAccountManager.cairo"
    AccountDeployer = "contracts/AccountDeployer.cairo"
    AdminAuth = "contracts/AdminAuth.cairo"
    AuthorizedRegistry = "contracts/AuthorizedRegistry.cairo"
    Trading = "contracts/Trading.cairo"
    FeeDiscount = "contracts/FeeDiscount.cairo"
    TradingFees = "contracts/TradingFees.cairo"
    Asset = "contracts/Asset.cairo"
    Math_64x61 = "contracts/Math_64x61.cairo"
    Holding = "contracts/Holding.cairo"
    FeeBalance = "contracts/FeeBalance.cairo"
    Markets = "contracts/Markets.cairo"
    LiquidityFund = "contracts/LiquidityFund.cairo"
    InsuranceFund = "contracts/InsuranceFund.cairo"
    EmergencyFund = "contracts/EmergencyFund.cairo"
    AccountRegistry = "contracts/AccountRegistry.cairo"
    ABR = "contracts/ABR.cairo"
    ABRFund = "contracts/ABRFund.cairo"
    ABRPayment = "contracts/ABRPayment.cairo"
    MarketPrices = "contracts/MarketPrices.cairo"
    Liquidate = "tests/testable/TestLiquidate.cairo"
    DepositDataManager = "contracts/DepositDataManager.cairo"
    WithdrawalFeeBalance = "contracts/WithdrawalFeeBalance.cairo"
    CollateralPrices = "contracts/CollateralPrices.cairo"
    ValidatorRouter = "contracts/signature_infra/ValidatorRouter.cairo"
    SigRequirementsManager = "contracts/signature_infra/SigRequirementsManager.cairo"
    PubkeyWhitelister = "contracts/signature_infra/PubkeyWhitelister.cairo"
    HighTide = "contracts/hightide/HighTide.cairo"
    HighTideCalc = "contracts/hightide/HighTideCalc.cairo"
    TradingStats = "contracts/hightide/TradingStats.cairo"
    LiquidityPool = "contracts/hightide/LiquidityPool.cairo"

    # Relay contracts
    RelayABR = "contracts/relay_contracts/RelayABR.cairo"
    RelayABRPayment = "contracts/relay_contracts/RelayABRPayment.cairo"
    RelayTrading = "contracts/relay_contracts/RelayTrading.cairo"
    RelayAsset = "contracts/relay_contracts/RelayAsset.cairo"
    RelayHolding = "contracts/relay_contracts/RelayHolding.cairo"
    RelayFeeBalance = "contracts/relay_contracts/RelayFeeBalance.cairo"
    RelayTradingFees = "contracts/relay_contracts/RelayTradingFees.cairo"
    RelayAccountRegistry = "contracts/relay_contracts/RelayAccountRegistry.cairo"
    RelayEmergencyFund = "contracts/relay_contracts/RelayEmergencyFund.cairo"
    RelayLiquidate = "contracts/relay_contracts/RelayLiquidate.cairo"
    RelayMarkets = "contracts/relay_contracts/RelayMarkets.cairo"
    RelayFeeDiscount = "contracts/relay_contracts/RelayFeeDiscount.cairo"
    WithdrawalRequest = "contracts/WithdrawalRequest.cairo"
    # Test-helping contracts
    ArrayTesting = "tests/testable/TestArrayTesting.cairo"
    CallFeeBalance = "tests/testable/CallFeeBalance.cairo"
    TestAsset = "tests/contracts/Asset.cairo"

class OptimizedStarknetState(StarknetState):

    def copy(self) -> "OptimizedStarknetState":
        ### StarknetState's copy operation is the most expesive part of send tx call
        ### We don't use StarknetState, so no problem in skipping copy operation
        return self

class ContractsHolder:

    def __init__(self):
        self.contract_classes = {}

    def prepare(self):
        for type in ContractType:
            compiled_class = compile_starknet_files(files=[type.value])
            self.contract_classes[type] = compiled_class

    def get_contract_class(self, type: ContractType) -> ContractClass:
        return self.contract_classes[type]

class StarknetService:

    def __init__(self, starknet: Starknet, contracts_holder: ContractsHolder, compilation_cache: LRUCache):
        self.starknet = starknet
        self.contracts_holder = contracts_holder
        self.compilation_cache = compilation_cache

    async def declare(self, type: ContractType):
        contract_class = self.contracts_holder.get_contract_class(type)
        with set_class_hash_cache(self.compilation_cache):
            return await self.starknet.declare(contract_class=contract_class)

    async def deploy(self, type: ContractType, calldata) -> StarknetContract:
        contract_class = self.contracts_holder.get_contract_class(type)
        ### Computing class cache is the most expensive part of deploy call
        ### We reduce tests duration keeping class hashes in LRUCache shared between all tests (via Fixture)
        with set_class_hash_cache(self.compilation_cache):
            deployed_contract = await self.starknet.deploy(contract_class=contract_class, constructor_calldata=calldata)
            return deployed_contract

class AccountFactory:

    def __init__(self, starknet_service: StarknetService, L1_user_address, registry_address, version):
        self.starknet_service = starknet_service
        self.L1_user_address = L1_user_address
        self.registry_address = registry_address
        self.version = version

    async def deploy_account(self, public_key) -> StarknetContract:
        return await self.starknet_service.deploy(ContractType.Account, [
            public_key
        ])

    async def deploy_ZKX_account(self, public_key) -> StarknetContract:
        return await self.starknet_service.deploy(ContractType.AccountManager, [
            public_key,
            self.L1_user_address,
            self.registry_address,
            self.version
        ])