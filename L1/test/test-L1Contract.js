const { expect } = require("chai");
const { ethers } = require("hardhat");

async function deployStarknetCoreMock(deployer) {
  const factory = await ethers.getContractFactory("StarknetCoreMock", deployer);
  const mock = await factory.deploy();
  await mock.deployed();
  return mock;
}

async function deployL1ZKXContract(deployer, starknetCoreAddress, assetContractAddress, withdrawalRequestContractAddress) {
  const factory = await ethers.getContractFactory("L1ZKXContract", deployer);
  const contract = await factory.deploy(starknetCoreAddress, assetContractAddress, withdrawalRequestContractAddress);
  await contract.deployed();
  return contract;
}

const parseEther = ethers.utils.parseEther;
const ETH_TICKER = 4543560;
const WITHDRAWAL_INDEX = 0;

describe("L1ZKXContract", function () {

  it("Should consume messages from StarknetCore", async function () {
    // Setup
    const [admin, alice, bob] = await ethers.getSigners();
    const starknetCoreMock = await deployStarknetCoreMock(admin);
    const L1ZKXContract = await deployL1ZKXContract(admin, starknetCoreMock.address, 0, 0);
    const aliceL2Address = 123456789987654;

    // Deposit to L1
    const aliceContract = L1ZKXContract.connect(alice);
    await aliceContract.depositEthToL1(aliceL2Address, { value: parseEther("2.5") });

    // Prepare withdrawal details
    const requestID = 42;
    const withdrawalAmount = parseEther("2.4");
    const payload = [
      WITHDRAWAL_INDEX,
      alice.address,
      ETH_TICKER,
      withdrawalAmount,
      requestID
    ];

    // Prepare mock for withdrawal
    await starknetCoreMock.addL2ToL1Message(aliceL2Address, L1ZKXContract.address, payload);

    // Bob can't withdraw Alice's funds
    const bobContract = L1ZKXContract.connect(bob)
    await expect(
      bobContract.withdrawEth(alice.address, withdrawalAmount, requestID)
    ).to.be.revertedWith("Sender is not withdrawal recipient")
    
    // Alice successfully withdraws
    await aliceContract.withdrawEth(alice.address, withdrawalAmount, requestID);
  });
});
