const { expect, Assertion } = require("chai");
const { ethers } = require("hardhat");

//////////////////////
/// TEST CONSTANTS ///
//////////////////////

const ETH = ethers.utils.parseEther;
const ONE_ETH = ETH("1.0");
const ROGUE_L2_ADDRESS = 444444444444444;
const ALICE_L2_ADDRESS =
  "0x2bcede62aeb41831af3b1d24b0f3733abbf7590eb38e7dc1b923ef578d76ea8";
const TOKEN_UNIT = 10 ** 6;
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const DUMMY_ADDRESS = "0x3333333333333333333333333333333333333333";
const L2_ASSET_ADDRESS =
  "0x054a91922c368c98503e3820330b997babaaf2beb05d96f5d9283bd2285fcbda";
const L2_WITHDRAWAL_ADDRESS =
  "0x054a91922c368c98503e3820330b997babaaf2beb05d96f5d9283bd2285fcbdb";

const ETH_ASSET = {
  ticker: 4543560,
  collateralID: 2012314141,
};

const ZKX_ASSET = {
  ticker: 1431520323,
  collateralID: 90986567876,
};

const ASSET_1 = {
  ticker: 123,
  collateralID: 90001,
  tokenAddress: "0x1111111111111111111111111111111111111111",
};
const ASSET_2 = {
  ticker: 234,
  collateralID: 90002,
  tokenAddress: "0x2222222222222222222222222222222222222222",
};
const ASSET_3 = {
  ticker: 345,
  collateralID: 90003,
  tokenAddress: "0x3333333333333333333333333333333333333333",
};

const INDEX = {
  ADD_ASSET: 1,
  REMOVE_ASSET: 2,
  WITHDRAWAL: 3,
};

//////////////////////
// TEST ENVIRONMENT //
//////////////////////

let L1ZKXContract;
let starknetCoreMock;
let ZKXToken;
let admin;
let alice;
let bob;
let rogue;

//////////////////////
// HELPER FUNCTIONS //
//////////////////////

async function prepareUsers() {
  [admin, alice, bob, rogue] = await ethers.getSigners();
}

async function deployStarknetCoreMock(deployer) {
  const factory = await ethers.getContractFactory("StarknetCoreMock", deployer);
  const mock = await factory.deploy();
  await mock.deployed();
  starknetCoreMock = mock;
  return mock;
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

async function deployZKXToken(deployer) {
  const factory = await ethers.getContractFactory("ZKXToken", deployer);
  const token = await factory.deploy();
  await token.deployed();
  ZKXToken = token;
  return token;
}

async function preapreToAdd(
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

async function addAsset(
  asset,
  zkxContract = L1ZKXContract,
  starknetMock = starknetCoreMock,
  assetAddress = L2_ASSET_ADDRESS
) {
  await preapreToAdd(asset, zkxContract, starknetMock, assetAddress);
  await zkxContract.updateAssetListInL1(asset.ticker, asset.collateralID);
}

async function prepareToRemove(
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

async function prepareToWithdraw(
  asset,
  recipient,
  L2Address,
  amount,
  requestID
) {
  const payload = [
    INDEX.WITHDRAWAL,
    recipient.address,
    asset.ticker,
    amount,
    requestID,
  ];
  await starknetCoreMock.addL2ToL1Message(
    L2Address,
    L1ZKXContract.address,
    payload
  );
}

//////////////////////
//// ASSET TESTS /////
//////////////////////

describe("Asset management", function () {
  beforeEach(async function () {
    await prepareUsers();
    starknetCoreMock = await deployStarknetCoreMock(admin);
    L1ZKXContract = await deployL1ZKXContract(admin, starknetCoreMock.address);
    ZKXToken = await deployZKXToken(admin);
  });

  it("Add ETH", async function () {
    // Given
    await preapreToAdd(ETH_ASSET);

    // When
    await L1ZKXContract.updateAssetListInL1(
      ETH_ASSET.ticker,
      ETH_ASSET.collateralID
    );

    // Then
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(1);
    expect(assetList[0]).to.be.eq(ETH_ASSET.ticker);
    expect(await L1ZKXContract.assetID(ETH_ASSET.ticker)).to.be.eq(
      ETH_ASSET.collateralID
    );
  });

  it("Add ZKXToken", async function () {
    // Given
    await preapreToAdd(ZKX_ASSET);

    // When
    await L1ZKXContract.updateAssetListInL1(
      ZKX_ASSET.ticker,
      ZKX_ASSET.collateralID
    );
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );

    // Then
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(1);
    expect(assetList[0]).to.be.eq(ZKX_ASSET.ticker);
    expect(await L1ZKXContract.assetID(ZKX_ASSET.ticker)).to.be.eq(
      ZKX_ASSET.collateralID
    );
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(
      ZKXToken.address
    );
  });

  it("Add both ETH & ZKXToken", async function () {
    // Given
    await preapreToAdd(ETH_ASSET);
    await preapreToAdd(ZKX_ASSET);

    // When
    await L1ZKXContract.updateAssetListInL1(
      ETH_ASSET.ticker,
      ETH_ASSET.collateralID
    );
    await L1ZKXContract.updateAssetListInL1(
      ZKX_ASSET.ticker,
      ZKX_ASSET.collateralID
    );
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );

    // Then
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(2);
    expect(assetList[0]).to.be.eq(ETH_ASSET.ticker);
    expect(assetList[1]).to.be.eq(ZKX_ASSET.ticker);
    expect(await L1ZKXContract.assetID(ETH_ASSET.ticker)).to.be.eq(
      ETH_ASSET.collateralID
    );
    expect(await L1ZKXContract.assetID(ZKX_ASSET.ticker)).to.be.eq(
      ZKX_ASSET.collateralID
    );
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(
      ZKXToken.address
    );
  });

  it("Add ETH & ZKXToken, then remove ETH", async function () {
    // Given
    await addAsset(ETH_ASSET);
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    await prepareToRemove(ETH_ASSET);

    // When
    await L1ZKXContract.removeAssetFromList(
      ETH_ASSET.ticker,
      ETH_ASSET.collateralID
    );

    // Then
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(1);
    expect(assetList[0]).to.be.eq(ZKX_ASSET.ticker);
    expect(await L1ZKXContract.assetID(ETH_ASSET.ticker)).to.be.eq(0);
    expect(await L1ZKXContract.assetID(ZKX_ASSET.ticker)).to.be.eq(
      ZKX_ASSET.collateralID
    );
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(
      ZKXToken.address
    );
  });

  it("Add ETH & ZKXToken, then remove ZKXToken", async function () {
    // Given
    await addAsset(ETH_ASSET);
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    await prepareToRemove(ZKX_ASSET);

    // When
    await L1ZKXContract.removeAssetFromList(
      ZKX_ASSET.ticker,
      ZKX_ASSET.collateralID
    );

    // Then
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(1);
    expect(assetList[0]).to.be.eq(ETH_ASSET.ticker);
    expect(await L1ZKXContract.assetID(ETH_ASSET.ticker)).to.be.eq(
      ETH_ASSET.collateralID
    );
    expect(await L1ZKXContract.assetID(ZKX_ASSET.ticker)).to.be.eq(0);
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(
      ZERO_ADDRESS
    );
  });

  it("NOT possible to add ETH twice", async function () {
    // Given
    await addAsset(ETH_ASSET);
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    await preapreToAdd(ETH_ASSET);

    // When
    await expect(
      L1ZKXContract.updateAssetListInL1(
        ETH_ASSET.ticker,
        ETH_ASSET.collateralID
      )
    ).to.be.revertedWith("Failed to add asset: Ticker already exists");

    // Then
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(2);
  });

  it("NOT possible to add ZKXToken twice", async function () {
    // Given
    await addAsset(ETH_ASSET);
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    await preapreToAdd(ZKX_ASSET);

    // When
    await expect(
      L1ZKXContract.updateAssetListInL1(
        ZKX_ASSET.ticker,
        ZKX_ASSET.collateralID
      )
    ).to.be.revertedWith("Failed to add asset: Ticker already exists");

    // Then
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(2);
  });

  it("NOT possible to set token address for non-existing asset", async function () {
    // When
    await expect(
      L1ZKXContract.setTokenContractAddress(ZKX_ASSET.ticker, ZKXToken.address)
    ).to.be.revertedWith("Failed to set token address: non-registered asset");

    // Then
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(
      ZERO_ADDRESS
    );
  });

  it("NOT possible to set token address to ZERO", async function () {
    // Given
    await addAsset(ZKX_ASSET);

    // When
    await expect(
      L1ZKXContract.setTokenContractAddress(ZKX_ASSET.ticker, ZERO_ADDRESS)
    ).to.be.revertedWith("Failed to set token address: zero address provided");

    // Then
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(
      ZERO_ADDRESS
    );
  });

  it("NOT possible to change already set token address", async function () {
    // Given
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );

    // When
    await expect(
      L1ZKXContract.setTokenContractAddress(ZKX_ASSET.ticker, DUMMY_ADDRESS)
    ).to.be.revertedWith("Failed to set token address: Already set");

    // Then
    expect(await L1ZKXContract.tokenContractAddress(ZKX_ASSET.ticker)).to.be.eq(
      ZKXToken.address
    );
  });

  it("Add 3 assets, then remove first", async function () {
    // Prepare
    await preapreToAdd(ASSET_1);
    await preapreToAdd(ASSET_2);
    await preapreToAdd(ASSET_3);

    // Add 5 assets
    await L1ZKXContract.updateAssetListInL1(
      ASSET_1.ticker,
      ASSET_1.collateralID
    );
    await L1ZKXContract.updateAssetListInL1(
      ASSET_2.ticker,
      ASSET_2.collateralID
    );
    await L1ZKXContract.updateAssetListInL1(
      ASSET_3.ticker,
      ASSET_3.collateralID
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_1.ticker,
      ASSET_1.tokenAddress
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_2.ticker,
      ASSET_2.tokenAddress
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_3.ticker,
      ASSET_3.tokenAddress
    );
    expect((await L1ZKXContract.getAssetList()).length).to.be.eq(3);

    // Remove first asset
    await prepareToRemove(ASSET_1);
    await L1ZKXContract.removeAssetFromList(
      ASSET_1.ticker,
      ASSET_1.collateralID
    );

    // Check that 3rd is 1st now, 2nd didn't move, 1st is gone
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(2);
    expect(assetList[0]).to.be.eq(ASSET_3.ticker);
    expect(assetList[1]).to.be.eq(ASSET_2.ticker);

    // Check asset IDs
    expect(await L1ZKXContract.assetID(ASSET_1.ticker)).to.be.eq(0);
    expect(await L1ZKXContract.assetID(ASSET_2.ticker)).to.be.eq(
      ASSET_2.collateralID
    );
    expect(await L1ZKXContract.assetID(ASSET_3.ticker)).to.be.eq(
      ASSET_3.collateralID
    );

    // Check token addresses
    expect(await L1ZKXContract.tokenContractAddress(ASSET_1.ticker)).to.be.eq(
      ZERO_ADDRESS
    );
    expect(await L1ZKXContract.tokenContractAddress(ASSET_2.ticker)).to.be.eq(
      ASSET_2.tokenAddress
    );
    expect(await L1ZKXContract.tokenContractAddress(ASSET_3.ticker)).to.be.eq(
      ASSET_3.tokenAddress
    );
  });

  it("Add 3 assets, then remove middle", async function () {
    // Prepare
    await preapreToAdd(ASSET_1);
    await preapreToAdd(ASSET_2);
    await preapreToAdd(ASSET_3);

    // Add 5 assets
    await L1ZKXContract.updateAssetListInL1(
      ASSET_1.ticker,
      ASSET_1.collateralID
    );
    await L1ZKXContract.updateAssetListInL1(
      ASSET_2.ticker,
      ASSET_2.collateralID
    );
    await L1ZKXContract.updateAssetListInL1(
      ASSET_3.ticker,
      ASSET_3.collateralID
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_1.ticker,
      ASSET_1.tokenAddress
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_2.ticker,
      ASSET_2.tokenAddress
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_3.ticker,
      ASSET_3.tokenAddress
    );
    expect((await L1ZKXContract.getAssetList()).length).to.be.eq(3);

    // Remove first asset
    await prepareToRemove(ASSET_2);
    await L1ZKXContract.removeAssetFromList(
      ASSET_2.ticker,
      ASSET_2.collateralID
    );

    // Check that 3rd is 2nd now, 1st didn't move, 2nd is gone
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(2);
    expect(assetList[0]).to.be.eq(ASSET_1.ticker);
    expect(assetList[1]).to.be.eq(ASSET_3.ticker);

    // Check asset IDs
    expect(await L1ZKXContract.assetID(ASSET_1.ticker)).to.be.eq(
      ASSET_1.collateralID
    );
    expect(await L1ZKXContract.assetID(ASSET_2.ticker)).to.be.eq(0);
    expect(await L1ZKXContract.assetID(ASSET_3.ticker)).to.be.eq(
      ASSET_3.collateralID
    );

    // Check token addresses
    expect(await L1ZKXContract.tokenContractAddress(ASSET_1.ticker)).to.be.eq(
      ASSET_1.tokenAddress
    );
    expect(await L1ZKXContract.tokenContractAddress(ASSET_2.ticker)).to.be.eq(
      ZERO_ADDRESS
    );
    expect(await L1ZKXContract.tokenContractAddress(ASSET_3.ticker)).to.be.eq(
      ASSET_3.tokenAddress
    );
  });

  it("Add 3 assets, then remove last", async function () {
    // Prepare
    await preapreToAdd(ASSET_1);
    await preapreToAdd(ASSET_2);
    await preapreToAdd(ASSET_3);

    // Add 5 assets
    await L1ZKXContract.updateAssetListInL1(
      ASSET_1.ticker,
      ASSET_1.collateralID
    );
    await L1ZKXContract.updateAssetListInL1(
      ASSET_2.ticker,
      ASSET_2.collateralID
    );
    await L1ZKXContract.updateAssetListInL1(
      ASSET_3.ticker,
      ASSET_3.collateralID
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_1.ticker,
      ASSET_1.tokenAddress
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_2.ticker,
      ASSET_2.tokenAddress
    );
    await L1ZKXContract.setTokenContractAddress(
      ASSET_3.ticker,
      ASSET_3.tokenAddress
    );
    expect((await L1ZKXContract.getAssetList()).length).to.be.eq(3);

    // Remove first asset
    await prepareToRemove(ASSET_3);
    await L1ZKXContract.removeAssetFromList(
      ASSET_3.ticker,
      ASSET_3.collateralID
    );

    // Check that 3rd is gone, other didn't move
    const assetList = await L1ZKXContract.getAssetList();
    expect(assetList.length).to.be.eq(2);
    expect(assetList[0]).to.be.eq(ASSET_1.ticker);
    expect(assetList[1]).to.be.eq(ASSET_2.ticker);

    // Check asset IDs
    expect(await L1ZKXContract.assetID(ASSET_1.ticker)).to.be.eq(
      ASSET_1.collateralID
    );
    expect(await L1ZKXContract.assetID(ASSET_2.ticker)).to.be.eq(
      ASSET_2.collateralID
    );
    expect(await L1ZKXContract.assetID(ASSET_3.ticker)).to.be.eq(0);

    // Check token addresses
    expect(await L1ZKXContract.tokenContractAddress(ASSET_1.ticker)).to.be.eq(
      ASSET_1.tokenAddress
    );
    expect(await L1ZKXContract.tokenContractAddress(ASSET_2.ticker)).to.be.eq(
      ASSET_2.tokenAddress
    );
    expect(await L1ZKXContract.tokenContractAddress(ASSET_3.ticker)).to.be.eq(
      ZERO_ADDRESS
    );
  });
});

//////////////////////
// DEPLOYMENT TESTS //
//////////////////////

describe("Deployment", function () {
  it("Constructor event emission ", async function () {
    const [admin] = await ethers.getSigners();
    const starknetCoreMock = await deployStarknetCoreMock(admin);
    const L1ZKXContractFactory = await ethers.getContractFactory(
      "L1ZKXContract",
      admin
    );
    const L2ZKXContract = await L1ZKXContractFactory.deploy(
      starknetCoreMock.address,
      54,
      42
    );
    await L2ZKXContract.deployed();

    await expect(L2ZKXContract.deployTransaction)
      .to.emit(L2ZKXContract, "LogContractInitialized")
      .withArgs(starknetCoreMock.address, 54, 42);
  });

  it("State after deployment", async function () {
    // Deploy contract
    const [admin] = await ethers.getSigners();
    const starknetCoreMock = await deployStarknetCoreMock(admin);
    const L1ZKXContract = await deployL1ZKXContract(
      admin,
      starknetCoreMock.address
    );

    // Check state
    expect(await L1ZKXContract.owner()).to.be.eq(admin.address);
    expect(await L1ZKXContract.starknetCore()).to.be.eq(
      starknetCoreMock.address
    );
  });

  it("Unable to deploy with zero StarknetCore address", async function () {
    const [admin] = await ethers.getSigners();

    await expect(
      deployL1ZKXContract(
        admin,
        ZERO_ADDRESS,
        L2_ASSET_ADDRESS,
        L2_WITHDRAWAL_ADDRESS
      )
    ).to.be.revertedWith("StarknetCore address not provided");
  });

  it("Change Withdrawal Request Address", async function () {
    // Setup environment
    const assetContractAddress =
      BigInt(
        0x06e2ed6c28ff10eef7391edd6f3151ebc3528ccb55dd78f9babfc89a40ac6139
      );
    const withdrawalRequestAddress =
      BigInt(
        0x04f9a757a5d412b6f2996b2dfd2b598e5bd4bad4d8fbf2e6437f59e7da718833
      );

    const [admin, alice, rogue] = await ethers.getSigners();
    const starknetCoreMock = await deployStarknetCoreMock(admin);
    const L1ZKXContract = await deployL1ZKXContract(
      admin,
      starknetCoreMock.address,
      assetContractAddress,
      withdrawalRequestAddress
    );
    const rogueContract = L1ZKXContract.connect(rogue);

    // Address of the malicious withdrawal address
    const maliciousContract =
      BigInt(
        0x0543a757a5d412b6f2996b2dfd2b598e5bd4bad4d8fbf2e6437f59e7da718855
      );
    const properContract =
      BigInt(
        0x0673a757a5d412b6f2996b2dfd2b598e5bd4bad4d8fbf2e6437f59e7da718875
      );

    // Should revert if called by a non-admin
    await expect(
      rogueContract.setWithdrawalRequestAddress(maliciousContract)
    ).to.be.revertedWith("Ownable: caller is not the owner");

    // Connect admin account to L1ZKXContract
    const adminContract = L1ZKXContract.connect(admin);

    // Admin should be able to change the Withdrawal Request Address
    await expect(adminContract.setWithdrawalRequestAddress(properContract))
      .to.emit(L1ZKXContract, "LogWithdrawalRequestContractChanged")
      .withArgs(withdrawalRequestAddress, properContract);

    // Check if the address has changed
    expect(await L1ZKXContract.withdrawalRequestContractAddress()).to.be.eq(
      properContract
    );
  });

  it("Change Asset Address", async function () {
    // Setup environment
    const assetContractAddress =
      BigInt(
        0x06e2ed6c28ff10eef7391edd6f3151ebc3528ccb55dd78f9babfc89a40ac6139
      );
    const withdrawalRequestAddress =
      BigInt(
        0x04f9a757a5d412b6f2996b2dfd2b598e5bd4bad4d8fbf2e6437f59e7da718833
      );

    const [admin, alice, rogue] = await ethers.getSigners();
    const starknetCoreMock = await deployStarknetCoreMock(admin);
    const L1ZKXContract = await deployL1ZKXContract(
      admin,
      starknetCoreMock.address,
      assetContractAddress,
      withdrawalRequestAddress
    );
    const rogueContract = L1ZKXContract.connect(rogue);

    // Address of the malicious withdrawal contract
    const maliciousContract =
      BigInt(
        0x0543a757a5d412b6f2996b2dfd2b598e5bd4bad4d8fbf2e6437f59e7da718855
      );
    const properContract =
      BigInt(
        0x0673a757a5d412b6f2996b2dfd2b598e5bd4bad4d8fbf2e6437f59e7da718875
      );

    // Should revert if called by a non-admin
    await expect(
      rogueContract.setAssetContractAddress(maliciousContract)
    ).to.be.revertedWith("Ownable: caller is not the owner");

    // Connect admin account to L1ZKXContract
    const adminContract = L1ZKXContract.connect(admin);

    // Admin should be able to change the Asset Address
    await expect(adminContract.setAssetContractAddress(properContract))
      .to.emit(L1ZKXContract, "LogAssetContractAddressChanged")
      .withArgs(assetContractAddress, properContract);

    // Check if the address has changed
    expect(await L1ZKXContract.assetContractAddress()).to.be.eq(properContract);
  });
});

//////////////////////
/// DEPOSIT TESTS ////
//////////////////////

describe("Deposits", function () {
  let aliceContract;
  let rogueContract;

  beforeEach(async function () {
    await prepareUsers();
    starknetCoreMock = await deployStarknetCoreMock(admin);
    L1ZKXContract = await deployL1ZKXContract(admin, starknetCoreMock.address);
    ZKXToken = await deployZKXToken(admin);
    aliceContract = L1ZKXContract.connect(alice);
    rogueContract = L1ZKXContract.connect(rogue);
  });

  it("Not possible to deposit ETH before asset added", async function () {
    await expect(
      aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: ONE_ETH })
    ).to.be.revertedWith("Deposit failed: ETH not registered as asset");
  });

  it("Not possible to deposit 0 ETH", async function () {
    await expect(
      aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: ETH("0") })
    ).to.be.revertedWith("Deposit failed: no value provided");
  });

  it("Successful ETH deposit", async function () {
    await addAsset(ETH_ASSET);
    await starknetCoreMock.resetCounters();

    await expect(
      aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: ONE_ETH })
    ).to.emit(L1ZKXContract, "LogDeposit");

    // Deposit should not consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      0
    );
    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);
  });

  it("Deposit and then withdraw ETH", async function () {
    await addAsset(ETH_ASSET);
    await starknetCoreMock.resetCounters();
    const amount = ETH("2.5");

    await aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: amount });

    // Deposit should not consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      0
    );
    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);

    // Prepare mock for withdrawal
    const requestID = 42;
    await prepareToWithdraw(
      ETH_ASSET,
      alice,
      ALICE_L2_ADDRESS,
      amount,
      requestID
    );
    await starknetCoreMock.resetCounters();

    // Rogue can't withdraw Alice's funds
    const rogueContract = L1ZKXContract.connect(rogue);
    await expect(
      rogueContract.withdrawEth(
        rogue.address,
        ROGUE_L2_ADDRESS,
        amount,
        requestID
      )
    ).to.be.revertedWith("INVALID_MESSAGE_TO_CONSUME");
    await expect(
      rogueContract.withdrawEth(
        rogue.address,
        ALICE_L2_ADDRESS,
        amount,
        requestID
      )
    ).to.be.revertedWith("INVALID_MESSAGE_TO_CONSUME");

    // Alice successfully withdraws funds
    await aliceContract.withdrawEth(
      alice.address,
      ALICE_L2_ADDRESS,
      amount,
      requestID
    );
    // Withdrawal should consume 1 message from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      1
    );
    // Withdrawal should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);
  });

  it("Not possible to deposit Tokens before asset added", async function () {
    await expect(
      aliceContract.depositToL1(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        100 * TOKEN_UNIT
      )
    ).to.be.revertedWith("Deposit failed: non-registered asset");
  });

  it("Not possible to deposit Tokens is address not set", async function () {
    await addAsset(ZKX_ASSET);

    await expect(
      aliceContract.depositToL1(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        100 * TOKEN_UNIT
      )
    ).to.be.revertedWith("Deposit failed: token address not set");
  });

  it("Not possible to deposit more Tokens than user has", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    await ZKXToken.mint(alice.address, 100 * TOKEN_UNIT);

    await expect(
      aliceContract.depositToL1(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        101 * TOKEN_UNIT
      )
    ).to.be.reverted;
  });

  it("Successful Token deposit", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    await ZKXToken.mint(alice.address, 100 * TOKEN_UNIT);
    await ZKXToken.connect(alice).approve(
      L1ZKXContract.address,
      100 * TOKEN_UNIT
    );
    await starknetCoreMock.resetCounters();

    await expect(
      aliceContract.depositToL1(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        100 * TOKEN_UNIT
      )
    ).to.emit(L1ZKXContract, "LogDeposit");

    // Deposit doesn't consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      0
    );
    // Deposit sends message from L1 to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);
  });

  it("Deposit and then withdraw tokens", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    const amount = 100 * TOKEN_UNIT;
    await ZKXToken.mint(alice.address, amount);
    await ZKXToken.connect(alice).approve(L1ZKXContract.address, amount);
    await starknetCoreMock.resetCounters();

    await aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_ASSET.ticker, amount);

    // Deposit should not consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      0
    );
    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);

    // Prepare withdrawal details
    const requestID = 42;
    await prepareToWithdraw(
      ZKX_ASSET,
      alice,
      ALICE_L2_ADDRESS,
      amount,
      requestID
    );
    await starknetCoreMock.resetCounters();

    // Rogue can't withdraw Alice's funds
    await expect(
      rogueContract.withdraw(
        rogue.address,
        ROGUE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        requestID
      )
    ).to.be.revertedWith("INVALID_MESSAGE_TO_CONSUME");

    await expect(
      rogueContract.withdraw(
        rogue.address,
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        requestID
      )
    ).to.be.revertedWith("INVALID_MESSAGE_TO_CONSUME");

    // Alice successfully withdraws funds
    await aliceContract.withdraw(
      alice.address,
      ALICE_L2_ADDRESS,
      ZKX_ASSET.ticker,
      amount,
      requestID
    );
    // Withdrawal should consume 1 message from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      1
    );
    // Withdrawal should send a message from L1 to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);
  });

  it("Multiple token deposits", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    await ZKXToken.mint(alice.address, 300 * TOKEN_UNIT);
    await ZKXToken.connect(alice).approve(
      L1ZKXContract.address,
      1_000_000 * TOKEN_UNIT
    );
    await starknetCoreMock.resetCounters();

    // Transfer reverts inside ERC20, because Alice has only 300 tokens
    await expect(
      aliceContract.depositToL1(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        301 * TOKEN_UNIT
      )
    ).to.be.reverted;

    // This deposit succeeds, after tx Alice has 200 tokens left
    await aliceContract.depositToL1(
      ALICE_L2_ADDRESS,
      ZKX_ASSET.ticker,
      100 * TOKEN_UNIT
    );

    // Second deposit succeeds, after tx Alice has 100 tokens left
    await aliceContract.depositToL1(
      ALICE_L2_ADDRESS,
      ZKX_ASSET.ticker,
      100 * TOKEN_UNIT
    );

    // Third deposti also succeeds, after tx Alice has no tokens left
    await aliceContract.depositToL1(
      ALICE_L2_ADDRESS,
      ZKX_ASSET.ticker,
      100 * TOKEN_UNIT
    );

    // Deposit doesn't consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      0
    );
    // Deposit sends message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(3);

    // Revert second deposit because Alice has no more tokens left
    await expect(
      aliceContract.depositToL1(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        1 * TOKEN_UNIT
      )
    ).to.be.reverted;
  });

  it("Multiple ETH deposits", async function () {
    await addAsset(ETH_ASSET);
    await starknetCoreMock.resetCounters();

    // Transfer ETH 3 times, all should succeed
    await aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: ETH("10") });
    await aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: ETH("5") });
    await aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: ETH("7") });

    // Deposits don't consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(
      0
    );
    // Every deposit sends a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(3);
  });
});

////////////////////////////////////
//// DEPOSIT CANCELLATION TESTS ////
////////////////////////////////////

describe("Deposit Cancellation", function () {
  let aliceContract;
  let rogueContract;

  beforeEach(async function () {
    await prepareUsers();
    starknetCoreMock = await deployStarknetCoreMock(admin);
    L1ZKXContract = await deployL1ZKXContract(admin, starknetCoreMock.address);
    ZKXToken = await deployZKXToken(admin);
    aliceContract = L1ZKXContract.connect(alice);
    rogueContract = L1ZKXContract.connect(rogue);
  });

  it("deposit by one user, cancellation by another user", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    const amount = 100 * TOKEN_UNIT;
    await ZKXToken.mint(alice.address, amount);
    await ZKXToken.connect(alice).approve(L1ZKXContract.address, amount);
    await starknetCoreMock.resetCounters();

    await aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_ASSET.ticker, amount);

    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);

    // Prepare mock for cancelling deposit
    const nonce = 100;
    await expect(
      rogueContract.depositCancelRequest(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        nonce
      )
    ).to.be.revertedWith("NO_MESSAGE_TO_CANCEL");
  });

  it("Trying to finalize cancel without initiating", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    const amount = 100 * TOKEN_UNIT;
    await ZKXToken.mint(alice.address, amount);
    await ZKXToken.connect(alice).approve(L1ZKXContract.address, amount);
    await starknetCoreMock.resetCounters();

    await aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_ASSET.ticker, amount);

    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);

    // Prepare mock for cancelling deposit
    const nonce = 100;
    await expect(
      aliceContract.depositReclaim(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        nonce
      )
    ).to.be.revertedWith("MESSAGE_CANCELLATION_NOT_REQUESTED");
  });

  it("Initiating cancel before Message Cancellation delay is complete", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    const amount = 100 * TOKEN_UNIT;
    await ZKXToken.mint(alice.address, amount);
    await ZKXToken.connect(alice).approve(L1ZKXContract.address, amount);
    await starknetCoreMock.resetCounters();

    await aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_ASSET.ticker, amount);

    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);

    // Prepare mock for cancelling deposit
    const nonce = 100;
    await expect(
      aliceContract.depositCancelRequest(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        nonce
      )
    ).to.emit(L1ZKXContract, "LogDepositCancelRequest");

    expect(await starknetCoreMock.invokedCancelMessageToL2Count()).to.be.eq(1);

    await expect(
      aliceContract.depositReclaim(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        nonce
      )
    ).to.be.revertedWith("MESSAGE_CANCELLATION_NOT_ALLOWED_YET");
  });

  it("Successful Cancellation of deposit", async function () {
    await addAsset(ZKX_ASSET);
    await L1ZKXContract.setTokenContractAddress(
      ZKX_ASSET.ticker,
      ZKXToken.address
    );
    const amount = 100 * TOKEN_UNIT;
    await ZKXToken.mint(alice.address, amount);
    await ZKXToken.connect(alice).approve(L1ZKXContract.address, amount);
    await starknetCoreMock.resetCounters();

    await aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_ASSET.ticker, amount);

    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);

    // Prepare mock for cancelling deposit
    const nonce = 100;
    await expect(
      aliceContract.depositCancelRequest(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        nonce
      )
    ).to.emit(L1ZKXContract, "LogDepositCancelRequest");

    expect(await starknetCoreMock.invokedCancelMessageToL2Count()).to.be.eq(1);
    await ethers.provider.send("evm_increaseTime", [600]);
    await ethers.provider.send("evm_mine");
    await expect(
      aliceContract.depositReclaim(
        ALICE_L2_ADDRESS,
        ZKX_ASSET.ticker,
        amount,
        nonce
      )
    ).to.emit(L1ZKXContract, "LogDepositReclaimed");
  });
});
