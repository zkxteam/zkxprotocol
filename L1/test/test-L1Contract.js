const { expect } = require("chai");
const { ethers } = require("hardhat");

async function deployStarknetCoreMock(deployer) {
  const factory = await ethers.getContractFactory('StarknetCoreMock', deployer);
  const mock = await factory.deploy();
  await mock.deployed();
  return mock;
}

async function deployL1ZKXContract(deployer, starknetCoreAddress, assetContractAddress, withdrawalRequestContractAddress) {
  const factory = await ethers.getContractFactory('L1ZKXContract', deployer);
  const contract = await factory.deploy(starknetCoreAddress, assetContractAddress, withdrawalRequestContractAddress);
  await contract.deployed();
  return contract;
}

async function deployZKXToken(deployer) {
  const factory = await ethers.getContractFactory('ZKXToken', deployer);
  const token = await factory.deploy();
  await token.deployed();
  return token;
}

const parseEther = ethers.utils.parseEther;
const ETH_TICKER = 4543560;
const WITHDRAWAL_INDEX = 0;
const ALICE_L2_ADDRESS = 123456789987654;
const TOKEN_UNIT = 10**6;
const ZKX_TICKER = 1234567;

describe('L1ZKXContract', function () {

  it('Deposit and then withdraw ETH', async function () {
    // Setup environment
    const [admin, alice, rogue] = await ethers.getSigners();
    const starknetCoreMock = await deployStarknetCoreMock(admin);
    const L1ZKXContract = await deployL1ZKXContract(admin, starknetCoreMock.address, 0, 0);
    const aliceContract = L1ZKXContract.connect(alice);

    // Deposit to L1
    await aliceContract.depositEthToL1(ALICE_L2_ADDRESS, { value: parseEther("2.5") });
    // Deposit should not consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(0)
    // Deposit should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1)

    // Prepare withdrawal details
    const requestID = 42;
    const withdrawalAmount = parseEther('2.4');
    const payload = [
      WITHDRAWAL_INDEX,
      alice.address,
      ETH_TICKER,
      withdrawalAmount,
      requestID
    ];

    // Prepare mock for withdrawal
    await starknetCoreMock.addL2ToL1Message(ALICE_L2_ADDRESS, L1ZKXContract.address, payload);

    // Rogue can't withdraw Alice's funds
    const rogueContract = L1ZKXContract.connect(rogue)
    await expect(
      rogueContract.withdrawEth(alice.address, withdrawalAmount, requestID)
    ).to.be.revertedWith('Sender is not withdrawal recipient')
    
    // Alice successfully withdraws funds
    await aliceContract.withdrawEth(alice.address, withdrawalAmount, requestID);
    // Withdrawal should consume 1 message from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(1);
    // Withdrawal should send a message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(2);
  });

  it('Deposit tokens', async function () {
    // Setup environment
    const [admin, alice, rogue] = await ethers.getSigners();
    const starknetCoreMock = await deployStarknetCoreMock(admin);
    const L1ZKXContract = await deployL1ZKXContract(admin, starknetCoreMock.address, 0, 0);
    const ZKXToken = await deployZKXToken(admin);
    const aliceContract = L1ZKXContract.connect(alice);

    // Now Alice's balance is 100 tokens
    ZKXToken.mint(alice.address, 100 * TOKEN_UNIT);
    
    // Reverts because ZKXToken is not registered by admin yet
    await expect(
      aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_TICKER, 100 * TOKEN_UNIT)
    ).to.be.revertedWith('Unregistered ticker');

    // Now admin registers ZXKToken address linked to ZKX ticker
    await expect(L1ZKXContract.setTokenContractAddress(ZKX_TICKER, ZKXToken.address))
      .to.emit(L1ZKXContract, 'LogTokenContractAddressUpdated')
      .withArgs(ZKX_TICKER, ZKXToken.address)

    // Before deposit Alice sets large allowance amount for ZKXContract
    await ZKXToken.connect(alice).approve(L1ZKXContract.address, 1_000_000 * TOKEN_UNIT)

    // Transfer reverts inside ERC20, because Alice has only 100 tokens
    await expect(aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_TICKER, 101 * TOKEN_UNIT)).to.be.reverted;
    
    // This deposit succeeds, because Alice has exactly 100 tokens (and 0 tokens left after deposit)
    await aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_TICKER, 100 * TOKEN_UNIT);
    // Deposit doesn't consume messages from L2
    expect(await starknetCoreMock.invokedConsumeMessageFromL2Count()).to.be.eq(0);
    // Deposit sends message to L2
    expect(await starknetCoreMock.invokedSendMessageToL2Count()).to.be.eq(1);

    // Revert second deposit because Alice has no more tokens left
    await expect(aliceContract.depositToL1(ALICE_L2_ADDRESS, ZKX_TICKER, 1 * TOKEN_UNIT)).to.be.reverted;
  });
});
