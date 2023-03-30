![ABR](https://zkx.fi/mediakit/zkx-black.svg)
#
![L1 Tests](https://github.com/zkxteam/zkxprotocol/actions/workflows/L1-tests.yml/badge.svg) ![L2 Tests](https://github.com/zkxteam/zkxprotocol/actions/workflows/L2-tests.yml/badge.svg)
# What is ZKX?

ZKX is a decentralized perpetual futures exchange on Starknet that prioritizes user control through self-custody and community governance. Our platform leverages ZK-STARK technology and our node network for unparalleled scalability and on-chain trading benefits such as account abstraction and low-cost transactions.

Our goal is to create a decentralized and permissionless infrastructure for derivative trading on an L2 network and trade any market through our data provider system with up to 20x leverage. 

Unlike other DEXs, we offer a unique risk management strategy called deleveraging that allows users to mitigate losses caused by sudden market shifts. Our deleveraging tools provide an additional layer of protection, and if that's not enough, we trigger liquidation to prevent even greater losses.

With three different UI options, ZKX offers a seamless onboarding process directly from L1. Ultimately, ZKX aims to create a decentralized and permissionless infrastructure for derivative trading across all markets.

**ZKX Provides**

- A fast decentralized limit order book
- A trader focused user interface
- Robust risk management engine
- A new funding rate that offers innovative payoff structures.
- Ability to earn USDC revenue of the exchange by staking ZKX token

**Our Mission**

ZKX was born with a very exciting combination of real market insight, the gap in the market, and an offering that nobody was thinking about. We are building a Trustless, Borderless DAO, and our mission is to democratize access to global yields through our offerings to anyone, anywhere.
# Features
## 1. The Tech
ZKX has a novel order book architecture with a decentralized node network optimized for high-speed and high-throughput scalability. A dedicated consensus algorithm along the node client has been developed to provide the linear scaling capacity of the exchange. DEXs have low TPS compared to CEXs that leverage centralized cloud computing solutions; with a node network that verifies its computation through Starknet and settles on Ethereum, ZKX can scale and compete with a centralized order book while being decentralized.

## 2. Innovative Tokenomics with our Liquid Governance model
One of the standout features of ZKX is their unique governance mechanism called liquid governance. This mechanism separates voting power from token holding, giving users a more democratic say in the protocol's direction.

Under this model, ZKX token holders can stake their tokens to gain digital shares of ZKX, which are tied to both governance and protocol rewards. By performing various actions such as trading, staking, providing liquidity, or becoming a node provider, stakeholders accumulate more digital shares, each of which equals one vote in the DAO.

One of the benefits of this mechanism is that it incentivizes positive behavior and promotes long-term growth. Holding digital shares provides access to protocol fee revenue, discounted trading fees, and unlocks premium features in the exchange. This approach is designed to ensure that the protocol's direction is shaped by the community of actual users and value providers, rather than just token holders such as whales and institutions.

## 3. Security
ZKX's use of the Ethereum network (L1), Starknet network, and ZKX Decentralized Off-chain Limit Order Book provides a robust security framework for users. Ethereum is known for its decentralized and open-source nature, and its smart contract functionality ensures that transactions are executed automatically without intermediaries. Starknet, built using the STARK cryptographic proof system, provides high security by ensuring that transactions are verified and processed off-chain before committing to the Ethereum network. By leveraging these technologies, ZKX offers a secure and reliable platform for derivative trading on an L2 network.

## 4. Layer 2 scaling with Starkware (™) 
One of the key features of the platform is its use of Layer 2 scaling technology with Starkware™. By leveraging StarkNet, a ZK rollup solution developed by StarkWare, the platform is able to offer users low trading fees, instant settlements, and fast withdrawals. This allows for a seamless trading experience that is both efficient and cost-effective.

# ZKX Architecture 

**ZKX's architecture comprises two layers - Ethereum smart contracts in solidity and Starknet smart contracts in Cairo.** The decentralized ZKX node network sits on top of these two layers, consisting of data availability, network prediction, computation algorithms, and consensus within the network. 

The Node Network consists of nodes that use a consensus algorithm for decentralized order matching, prioritizing scalability and performance. We prioritized scalability and performance while building a network that , and our tests reveal the current network can handle over 9000 TPS.

**The Node Network has two fundamental parts: DLOB and DPS.** 

- DLOB directly interacts between users, smart contracts, and the ZKX node, providing the much-needed security and reliability users demand. 
- DPS serves as a bridge between external data sources and ZKX's pricing, allowing greater flexibility in procuring assets, data sources, and prices. 

The robust Catamaran consensus algorithm is used to ensure reliable and efficient communication among ZKX nodes. It enhances reliability, separates the key elements of consensus, and enforces a higher degree of coherence to reduce the number of states that need to be calculated.

Decentralization and permission lessness are the foundation of ZKX, ensuring users have complete control over their investments and protocol functions. 

***Deep dive into the architecture in this [blog](https://zkx.fi/blogs/zkx-architecture-a-deep-dive?tab=announcements).***

# Technical Paper on our Funding Rate - ABR

The technical paper on our funding rate called Adaptive Balancing Rate is authored by **Busra Temocin, Vitaly Yakovlev, Eduard Jubany Tur, and Naman Sehgal**. 

The technical paper examines the funding rates of diverse exchanges concerning the price jumps of underlying assets and calculates trading spike windows under different funding rates. The paper also evaluates the ABR's response to Black Swan events and includes a long-term profit and loss analysis. Ultimately, the ABR reduces market risk exposure by offering a premium to assets with higher implied volatility.

**Breakdown of the ABR Mechanism**

The premium in ABR is based on the volatility of the underlying asset, measured through Bollinger Bands. As volatility increases, additional risk is created when traders make more bets or leave the orderbook. 

To balance this risk, a premium is added, but it is removed when volatility decreases and traders return to the orderbook. The difference between Bollinger Band Price and Mark price is integrated and added to the funding premium through a logarithmic function. 

![ABR](https://media.zkx.fi/abr1.png)

The premium is calculated every hour using TWAP and a fixed interest rate is added to account for differences in interest rates between currencies. The funding rate is charged/paid to ZKX traders every 8 hours and is adjustable in the long run.

![ABR](https://media.zkx.fi/abr2.png)

Technical Paper is available [here](https://media.zkx.fi/abr.pdf)

# Testnet Documentation

1. [How to Trade on ZKX](https://zkx.fi/blogs/how-to-trade-on-zkx)
2. [Testnet FAQ](https://zkx.fi/blogs/testnet-faq)
3. [ZKX Perpetual Market Orders](https://zkx.fi/blogs/zkx-perpetual-order-types)

# Contracts
## Layer 1 contracts

|**Contract Name**|**Description**|
| :- | :- |
|[L1ZKXContract](https://github.com/zkxteam/zkxprotocol/blob/main/L1/contracts/L1ZKXContract.sol)|Main ZKX Contract on L1|
|[IStarknetCore](https://github.com/zkxteam/zkxprotocol/tree/main/L1/contracts)|Starknet core contract interface|

## Layer 2 contracts

|**Contract Name**|**Description**|
| :- | :- |
|[ABRCalculations](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/ABRCalculations.cairo)|Calculates the ABR value|
|[ABRCore](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/ABRCore.cairo)|Main contract for ABR|
|[ABRFund](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/ABRFund.cairo)|Holds the ABR Funds|
|[ABRPayment](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/ABRPayment.cairo)|Contract that does ABR Payments|
|[AccountDeployer](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/AccountDeployer.cairo)|Creates a new account for the user|
|[AccountManager](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/AccountManager.cairo)|Stores all information related to specific user such as positions held and withdrawal history|
|[AccountRegistry](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/AccountRegistry.cairo)|Stores the L2 address of all the contracts deployed through **AccountDeployer**|
|[AdminAuth](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/AdminAuth.cairo)|Sets different admin roles for ZKX Protocol|
|[Asset](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Asset.cairo)|Stores the details of all assets of ZKX Protocol|
|[AuthorizedRegistry](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/AuthorizedRegistry.cairo)|Stores all ZKX contract addresses|
|[Constants](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Constants.cairo)|Stores the constant values which are used across all contracts|
|[DataTypes](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/DataTypes.cairo)|Stores the user defined datatypes|
|[DepositDataManager](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/DepositDataManager.cairo)|Stores deposit related information|
|[EmergencyFund](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/EmergencyFund.cairo)|Holds the emergency funds|
|[FeeBalance](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/FeeBalance.cairo)|Stores the fee collected from the user while opening an order|
|[FeeDiscount](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/FeeDiscount.cairo)|Stores the fee discount|
|[Holding](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Holding.cairo)|Holds the funds which correspond to open positions|
|[InsuranceFund](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/InsuranceFund.cairo)|Holds the insurance funds|
|[Liquidate](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Liquidate.cairo)|Handles the liquidation and deleveraging|
|[LiquidityFund](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/LiquidityFund.cairo)|Holds the liquidity funds which can be borrowed by the users|
|[MarketPrices](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/MarketPrices.cairo)|Holds the market prices|
|[Markets](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Markets.cairo)|Stores the details of all markets of ZKX Protocol|
|[Math_64x61](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Math_64x61.cairo)|Library used for arithmetic operations|
|[Settings](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Settings.cairo)|Stores settings related to the node|
|[Trading](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/Trading.cairo)|Holds all the trading logic|
|[TradingFees](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/TradingFees.cairo)|Stores and calculates the trading fees|
|[WithdrawalFeeBalance](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/WithdrawalFeeBalance.cairo)|Stores the fee for withdrawing funds|
|[WithdrawalRequest](https://github.com/zkxteam/zkxprotocol/blob/main/L2/contracts/WithdrawalRequest.cairo)|Keeps tracks of message payload for withdrawing funds|

# Security
## Independent Audits
The smart contracts deployed on both Layer 1 and 2 are independently audited by [Nethermind](https://nethermind.io/). The audit was performed on the Layer 1 and Layer 2 contracts written in Solidity and Cairo. The codebase is composed of 261 lines of Solidity code and 9200 lines of Cairo, the biggest Cairo smart contract audit by Nethermind.

Audit Report is available [here](https://media.zkx.fi/audit.pdf)

## Code Coverage
All smart contracts are passing tests and are production ready while passing 100% line and branch coverage.
## Vulnerability Disclousure Policy
It is important to note that reporting a security vulnerability is an ethical and responsible action that helps ensure the security and safety of users.
### How to report a security vulnerability?
To ensure the security of our users, we encourage the disclosure of any security vulnerabilities found in our contracts or platforms. If you discover a security vulnerability, please report it to us by sending an email to <security@zkx.fi>. Your report should include the following details:

1. Description of the vulnerability and its potential impact.
1. Detailed steps required to reproduce the vulnerability.
### Scope
This refers to any vulnerability that has not been previously disclosed either by us or by our independent auditors in their reports.
### Guidelines
We have certain requirements for all reporters which include:

1. Making every possible effort to avoid privacy violations, degradation of user experience, disruption to production systems, and destruction of data during security testing.
2. Using the designated communication channels to report vulnerability information to us.
3. Maintaining confidentiality of the information related to any vulnerabilities discovered by the reporter between themselves and ZKX for a certain period to allow us to resolve the issue.

In return, we commit to:

1. Not pursuing or supporting any legal action related to the reporter's findings.
2. Working with the reporter to quickly understand and resolve the issue.


