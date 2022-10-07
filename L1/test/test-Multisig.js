const { expect, Assertion } = require("chai");
const { ethers, userConfig } = require("hardhat");

//////////////////////
/// TEST CONSTANTS ///
//////////////////////

const ETH = ethers.utils.parseEther;
const ONE_ETH = ETH("1.0");
const BOB_L2_ADDRESS =
  "0x2bcede62aeb41831af3b1d24b0f3733abbf7590eb38e7dc1b923ef578d76ea8";
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const L2_ASSET_ADDRESS =
  "0x054a91922c368c98503e3820330b997babaaf2beb05d96f5d9283bd2285fcbda";
const L2_WITHDRAWAL_ADDRESS =
  "0x054a91922c368c98503e3820330b997babaaf2beb05d96f5d9283bd2285fcbdb";
const L2_DUMMY_ADDRESS =
  "0x075c53354a129c84512a2419241a884b0b0cf28ac04c84b3a8152ad1257accab";

const ETH_ASSET = {
  ticker: 4543560,
  collateralID: 2012314141,
};
const ZKX_ASSET = {
  ticker: 1431520323,
  collateralID: 90986567876,
  contractAddress: "0x3333333333333333333333333333333333333333"
};
const ONE_HOUR = 60 * 60;
const ONE_DAY = 24 * ONE_HOUR;

const INDEX = {
  ADD_ASSET: 1,
  REMOVE_ASSET: 2,
  WITHDRAWAL: 3,
};

//////////////////////
// TEST ENVIRONMENT //
//////////////////////

let L1ZKXContract;
let MultisigAdmin;
let starknetCoreMock;
let admin1;
let admin2;
let admin3;
let admin4;

//////////////////////
// HELPER FUNCTIONS //
//////////////////////

async function prepareUsers() {
  [admin1, admin2, admin3, admin4, admin5, bob] = await ethers.getSigners();
}

async function deployMultisigAdmin(deployer, quorum, admins) {
  const factory = await ethers.getContractFactory("MultisigAdmin", deployer);
  const contract = await factory.deploy(quorum, admins);
  await contract.deployed();
  MultisigAdmin = contract;
  return contract;
}

async function deployL1ZKXContract(
  deployer,
  starknetCoreAddress,
  assetContractAddress = L2_ASSET_ADDRESS,
  withdrawalRequestContractAddress = L2_WITHDRAWAL_ADDRESS
) {
  const factory = await ethers.getContractFactory("L1ZKXContract", deployer);
  const contract = await factory.deploy(
    starknetCoreAddress,
    assetContractAddress,
    withdrawalRequestContractAddress
  );
  await contract.deployed();
  L1ZKXContract = contract;
  return contract;
}

async function deployStarknetCoreMock(deployer) {
  const factory = await ethers.getContractFactory("StarknetCoreMock", deployer);
  const mock = await factory.deploy();
  await mock.deployed();
  starknetCoreMock = mock;
  return mock;
}

async function prepareStarknetToAdd(
  asset,
  zkxContract = L1ZKXContract,
  starknetMock = starknetCoreMock,
  assetAddress = L2_ASSET_ADDRESS
) {
  const payload = [INDEX.ADD_ASSET, asset.ticker, asset.collateralID];
  await starknetMock.addL2ToL1Message(
    assetAddress,
    zkxContract.address,
    payload
  );
}

async function prepareStarknetToRemove(
  asset,
  zkxContract = L1ZKXContract,
  starknetMock = starknetCoreMock,
  assetAddress = L2_ASSET_ADDRESS
) {
  const payload = [INDEX.REMOVE_ASSET, asset.ticker, asset.collateralID];
  await starknetMock.addL2ToL1Message(
    assetAddress,
    zkxContract.address,
    payload
  );
}

async function addAsset(
  asset,
  zkxContract = L1ZKXContract,
  starknetMock = starknetCoreMock,
  assetAddress = L2_ASSET_ADDRESS
) {
  await prepareStarknetToAdd(asset, zkxContract, starknetMock, assetAddress);
  await zkxContract.updateAssetListInL1(asset.ticker, asset.collateralID);
}

async function increaseTime(time) {
  await ethers.provider.send('evm_increaseTime', [time]);
  await ethers.provider.send('evm_mine');
}

function encode(types, values) {
  return ethers.utils.defaultAbiCoder.encode(types, values);
}

async function verifyAssetList(expectedAssets) {
  const assetsInContract = await L1ZKXContract.getAssetList();
  expect(assetsInContract.length).to.be.eq(expectedAssets.length);
  for (let i = 0; i < expectedAssets.length; i++) {
    expect(assetsInContract[i]).to.be.eq(expectedAssets[i].ticker);
  }
}

///////////
// TESTS //
///////////

describe("Multisig", function () {
  beforeEach(async function () {
    await prepareUsers();
    await deployStarknetCoreMock(admin1);
    await deployL1ZKXContract(admin1, starknetCoreMock.address);
    await deployMultisigAdmin(
      admin1,
      3,
      [admin1.address, admin2.address, admin3.address, admin4.address]
    );
    await L1ZKXContract.transferOwnership(MultisigAdmin.address);
  });

  it("Initial state", async function () {
    expect((await MultisigAdmin.getAllTxIds()).length).to.be.eq(0);
  });

  it("Withdraw ETH", async function () {
    const sentEtherCall = [
      admin2.address,
      "",
      "0x00",
      ONE_ETH
    ];
    const TX_ID = 42;
    await MultisigAdmin.proposeTx(TX_ID, [sentEtherCall], ONE_DAY);

    await increaseTime(ONE_DAY);

    expect((await MultisigAdmin.getAllTxIds()).length).to.be.eq(1);

    // Approve by admin1
    expect(await MultisigAdmin.isTxApproved(TX_ID, admin1.address)).to.be.eq(false);
    await (MultisigAdmin.connect(admin1).approve(TX_ID));
    expect(await MultisigAdmin.isTxApproved(TX_ID, admin1.address)).to.be.eq(true);

    // Approve by admin2
    expect(await MultisigAdmin.isTxApproved(TX_ID, admin2.address)).to.be.eq(false);
    await (MultisigAdmin.connect(admin2).approve(TX_ID));
    expect(await MultisigAdmin.isTxApproved(TX_ID, admin2.address)).to.be.eq(true);
    expect(await MultisigAdmin.canBeExecuted(TX_ID, ONE_ETH)).to.be.eq(false);

    // Approve by admin3
    expect(await MultisigAdmin.isTxApproved(TX_ID, admin3.address)).to.be.eq(false);
    await (MultisigAdmin.connect(admin3).approve(TX_ID));
    expect(await MultisigAdmin.isTxApproved(TX_ID, admin3.address)).to.be.eq(true);
    expect(await MultisigAdmin.canBeExecuted(TX_ID, ONE_ETH)).to.be.eq(false);

    await increaseTime(ONE_DAY);
    expect(await MultisigAdmin.canBeExecuted(TX_ID, ONE_ETH)).to.be.eq(true);

    const balanceBefore = await ethers.provider.getBalance(admin2.address);
    await MultisigAdmin.executeTx(TX_ID, { value: ONE_ETH })
    const balanceAfter = await ethers.provider.getBalance(admin2.address);

    expect(balanceAfter).to.be.eq(
      balanceBefore.add(ONE_ETH)
    );
  });

  it("Add assets (ZKX token & ETH), then remove ZKX token", async function () {
    // Add ZKX token as asset
    await prepareStarknetToAdd(ZKX_ASSET);
    const ADD_ZKX_TX_ID = 42;
    const addTokenCall = [
      L1ZKXContract.address,
      "updateAssetListInL1(uint256,uint256)",
      encode(["uint256", "uint256"], [ZKX_ASSET.ticker, ZKX_ASSET.collateralID]),
      0
    ];
    await MultisigAdmin.proposeTx(ADD_ZKX_TX_ID, [addTokenCall], ONE_HOUR);
    await (MultisigAdmin.connect(admin3).approve(ADD_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin4).approve(ADD_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin1).approve(ADD_ZKX_TX_ID));

    expect(await MultisigAdmin.canBeExecuted(ADD_ZKX_TX_ID, 0)).to.be.eq(false);
    await increaseTime(ONE_HOUR);
    expect(await MultisigAdmin.canBeExecuted(ADD_ZKX_TX_ID, 0)).to.be.eq(true);

    await MultisigAdmin.executeTx(ADD_ZKX_TX_ID);

    await verifyAssetList([ZKX_ASSET]);
    expect(await L1ZKXContract.assetID(ZKX_ASSET.ticker)).to.be.eq(ZKX_ASSET.collateralID);

    // Set ZKX token contract address
    const SET_ZKX_TX_ID = 44;
    const setZkxContractCall = [
      L1ZKXContract.address,
      "setTokenContractAddress(uint256,address)",
      encode(["uint256", "address"], [ZKX_ASSET.ticker, ZKX_ASSET.contractAddress]),
      0
    ];
    await MultisigAdmin.proposeTx(SET_ZKX_TX_ID, [setZkxContractCall], ONE_HOUR);

    await (MultisigAdmin.connect(admin4).approve(SET_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin2).approve(SET_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin3).approve(SET_ZKX_TX_ID));

    await increaseTime(ONE_HOUR);
    expect(await MultisigAdmin.canBeExecuted(SET_ZKX_TX_ID, 0)).to.be.eq(true);

    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(ZERO_ADDRESS);
    await MultisigAdmin.executeTx(SET_ZKX_TX_ID);
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(ZKX_ASSET.contractAddress);

    // Add ETH as asset
    await prepareStarknetToAdd(ETH_ASSET);
    const ADD_ETH_TX_ID = 55;
    const addEthCall = [
      L1ZKXContract.address,
      "updateAssetListInL1(uint256,uint256)",
      encode(["uint256", "uint256"], [ETH_ASSET.ticker, ETH_ASSET.collateralID]),
      0
    ];
    await MultisigAdmin.proposeTx(ADD_ETH_TX_ID, [addEthCall], ONE_HOUR);

    await (MultisigAdmin.connect(admin1).approve(ADD_ETH_TX_ID));
    await (MultisigAdmin.connect(admin2).approve(ADD_ETH_TX_ID));
    await (MultisigAdmin.connect(admin4).approve(ADD_ETH_TX_ID));

    expect(await MultisigAdmin.canBeExecuted(ADD_ETH_TX_ID, 0)).to.be.eq(false);
    await increaseTime(ONE_HOUR);
    expect(await MultisigAdmin.canBeExecuted(ADD_ETH_TX_ID, 0)).to.be.eq(true);

    await MultisigAdmin.executeTx(ADD_ETH_TX_ID);

    await verifyAssetList([ZKX_ASSET, ETH_ASSET]);
    expect(await L1ZKXContract.assetID(ETH_ASSET.ticker)).to.be.eq(ETH_ASSET.collateralID);

    // Remove ZKX token asset
    await prepareStarknetToRemove(ZKX_ASSET);
    const REMOVE_ZKX_TX_ID = 88;
    const removeTokenCall = [
      L1ZKXContract.address,
      "removeAssetFromList(uint256,uint256)",
      encode(["uint256", "uint256"], [ZKX_ASSET.ticker, ZKX_ASSET.collateralID]),
      0
    ];
    await MultisigAdmin.proposeTx(REMOVE_ZKX_TX_ID, [removeTokenCall], ONE_DAY);

    await (MultisigAdmin.connect(admin3).approve(REMOVE_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin1).approve(REMOVE_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin2).approve(REMOVE_ZKX_TX_ID));

    expect(await MultisigAdmin.canBeExecuted(REMOVE_ZKX_TX_ID, 0)).to.be.eq(false);
    await increaseTime(ONE_HOUR);
    expect(await MultisigAdmin.canBeExecuted(REMOVE_ZKX_TX_ID, 0)).to.be.eq(false);
    await increaseTime(ONE_DAY);
    expect(await MultisigAdmin.canBeExecuted(REMOVE_ZKX_TX_ID, 0)).to.be.eq(true);

    await MultisigAdmin.executeTx(REMOVE_ZKX_TX_ID);

    await verifyAssetList([ETH_ASSET]);
    expect(await L1ZKXContract.assetID(ZKX_ASSET.ticker)).to.be.eq(0);
    expect(await L1ZKXContract.assetID(ETH_ASSET.ticker)).to.be.eq(ETH_ASSET.collateralID);
  });

  it("Atomicly add ZKX token and set its contract address", async function () {
    await prepareStarknetToAdd(ZKX_ASSET);
    const ADD_ZKX_TX_ID = 42;
    const addTokenCall = [
      L1ZKXContract.address,
      "updateAssetListInL1(uint256,uint256)",
      encode(["uint256", "uint256"], [ZKX_ASSET.ticker, ZKX_ASSET.collateralID]),
      0
    ];
    const setZkxContractCall = [
      L1ZKXContract.address,
      "setTokenContractAddress(uint256,address)",
      encode(["uint256", "address"], [ZKX_ASSET.ticker, ZKX_ASSET.contractAddress]),
      0
    ];
    await MultisigAdmin.proposeTx(ADD_ZKX_TX_ID, [addTokenCall, setZkxContractCall], ONE_HOUR);

    await (MultisigAdmin.connect(admin1).approve(ADD_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin2).approve(ADD_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin4).approve(ADD_ZKX_TX_ID));

    expect(await MultisigAdmin.canBeExecuted(ADD_ZKX_TX_ID, 0)).to.be.eq(false);
    await increaseTime(ONE_HOUR);
    expect(await MultisigAdmin.canBeExecuted(ADD_ZKX_TX_ID, 0)).to.be.eq(true);

    await MultisigAdmin.executeTx(ADD_ZKX_TX_ID);

    await verifyAssetList([ZKX_ASSET]);
    expect(await L1ZKXContract.assetID(ZKX_ASSET.ticker)).to.be.eq(ZKX_ASSET.collateralID);
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(ZKX_ASSET.contractAddress);
  });

  it("Change asset contract address", async function () {
    const TX_ID = 42;
    const txCall = [
      L1ZKXContract.address,
      "setAssetContractAddress(uint256)",
      encode(["uint256"], [L2_DUMMY_ADDRESS]),
      0
    ];
    await MultisigAdmin.proposeTx(TX_ID, [txCall], ONE_DAY);

    await (MultisigAdmin.connect(admin3).approve(TX_ID));
    await (MultisigAdmin.connect(admin1).approve(TX_ID));
    await (MultisigAdmin.connect(admin4).approve(TX_ID));

    expect(await L1ZKXContract.assetContractAddress()).to.be.eq(L2_ASSET_ADDRESS);

    await increaseTime(ONE_DAY);
    await MultisigAdmin.executeTx(TX_ID);

    expect(await L1ZKXContract.assetContractAddress()).to.be.eq(L2_DUMMY_ADDRESS);
  });

  it("Change withdrawal contract address", async function () {
    const TX_ID = 42;
    const txCall = [
      L1ZKXContract.address,
      "setWithdrawalRequestAddress(uint256)",
      encode(["uint256"], [L2_DUMMY_ADDRESS]),
      0
    ];
    await MultisigAdmin.proposeTx(TX_ID, [txCall], ONE_DAY);

    await (MultisigAdmin.connect(admin3).approve(TX_ID));
    await (MultisigAdmin.connect(admin1).approve(TX_ID));
    await (MultisigAdmin.connect(admin4).approve(TX_ID));

    expect(await L1ZKXContract.withdrawalRequestContractAddress()).to.be.eq(L2_WITHDRAWAL_ADDRESS);

    await increaseTime(ONE_DAY);
    await MultisigAdmin.executeTx(TX_ID);

    expect(await L1ZKXContract.withdrawalRequestContractAddress()).to.be.eq(L2_DUMMY_ADDRESS);
  });

  it("Atomicly Change asset & withdrawal contract addresses", async function () {
    const TX_ID = 42;
    const assetAddressCall = [
      L1ZKXContract.address,
      "setAssetContractAddress(uint256)",
      encode(["uint256"], [L2_DUMMY_ADDRESS]),
      0
    ];
    const withdrawalAddressCall = [
      L1ZKXContract.address,
      "setWithdrawalRequestAddress(uint256)",
      encode(["uint256"], [L2_DUMMY_ADDRESS]),
      0
    ];
    await MultisigAdmin.proposeTx(TX_ID, [assetAddressCall, withdrawalAddressCall], ONE_DAY);

    await (MultisigAdmin.connect(admin3).approve(TX_ID));
    await (MultisigAdmin.connect(admin1).approve(TX_ID));
    await (MultisigAdmin.connect(admin4).approve(TX_ID));

    expect(await L1ZKXContract.assetContractAddress()).to.be.eq(L2_ASSET_ADDRESS);
    expect(await L1ZKXContract.withdrawalRequestContractAddress()).to.be.eq(L2_WITHDRAWAL_ADDRESS);

    await increaseTime(ONE_DAY);
    await MultisigAdmin.executeTx(TX_ID);

    expect(await L1ZKXContract.assetContractAddress()).to.be.eq(L2_DUMMY_ADDRESS);
    expect(await L1ZKXContract.withdrawalRequestContractAddress()).to.be.eq(L2_DUMMY_ADDRESS);
  });

  it("Withdraw ETH to Multisig", async function () {
    // Add ETH as asset to L1ZKXContract
    await prepareStarknetToAdd(ETH_ASSET);
    const ADD_ETH_TX_ID = 1;
    const addEthCall = [
      L1ZKXContract.address,
      "updateAssetListInL1(uint256,uint256)",
      encode(["uint256", "uint256"], [ETH_ASSET.ticker, ETH_ASSET.collateralID]),
      0
    ];
    await MultisigAdmin.proposeTx(ADD_ETH_TX_ID, [addEthCall], ONE_HOUR);
    await (MultisigAdmin.connect(admin1).approve(ADD_ETH_TX_ID));
    await (MultisigAdmin.connect(admin2).approve(ADD_ETH_TX_ID));
    await (MultisigAdmin.connect(admin4).approve(ADD_ETH_TX_ID));
    await increaseTime(ONE_HOUR);
    await MultisigAdmin.executeTx(ADD_ETH_TX_ID);

    // Deposit 1 ETH to L1ZKXContract
    await L1ZKXContract.connect(bob).depositEthToL1(BOB_L2_ADDRESS, { value: ONE_ETH });

    const withdrawFromZKXCall = [
      L1ZKXContract.address,
      "transferEth(address,uint256)",
      encode(["address", "uint256"], [MultisigAdmin.address, ONE_ETH]),
      0
    ];
    const WITHDRAW_ZKX_TX_ID = 2;
    await MultisigAdmin.proposeTx(WITHDRAW_ZKX_TX_ID, [withdrawFromZKXCall], ONE_DAY);
    await increaseTime(ONE_DAY);

    // Approve by admins
    await (MultisigAdmin.connect(admin1).approve(WITHDRAW_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin2).approve(WITHDRAW_ZKX_TX_ID));
    await (MultisigAdmin.connect(admin3).approve(WITHDRAW_ZKX_TX_ID));

    await increaseTime(ONE_DAY);
    await MultisigAdmin.executeTx(WITHDRAW_ZKX_TX_ID);
    expect(await ethers.provider.getBalance(MultisigAdmin.address)).to.be.eq(ONE_ETH);

    // Withdraw funds from Multisig to some other address
    const withdrawFromMultisigCall = [
      MultisigAdmin.address,
      "withdraw(address,uint256)",
      encode(["address", "uint256"], [admin4.address, ONE_ETH]),
      0
    ];
    const WITHDRAW_MULTISIG_TX_ID = 3;
    await MultisigAdmin.proposeTx(WITHDRAW_MULTISIG_TX_ID, [withdrawFromMultisigCall], ONE_DAY);
    await increaseTime(ONE_DAY);

    // Approve by admins
    await (MultisigAdmin.connect(admin1).approve(WITHDRAW_MULTISIG_TX_ID));
    await (MultisigAdmin.connect(admin2).approve(WITHDRAW_MULTISIG_TX_ID));
    await (MultisigAdmin.connect(admin3).approve(WITHDRAW_MULTISIG_TX_ID));
    
    await increaseTime(ONE_DAY);
    const adminBalanceBefore = await ethers.provider.getBalance(admin4.address);
    await MultisigAdmin.executeTx(WITHDRAW_MULTISIG_TX_ID);

    // Check results
    expect(await ethers.provider.getBalance(MultisigAdmin.address)).to.be.eq(0);
    const adminBalanceAfter = await ethers.provider.getBalance(admin4.address);
    expect(adminBalanceAfter).to.be.eq(
      adminBalanceBefore.add(ONE_ETH)
    );
  });
});
