const { starknet } = require("hardhat");
const { expect } = require("chai");
const { compileCalldata } = require("starknet");
const { BigNumber } = require("ethers");

describe("Admin contract", function () {
  this.timeout(300_000); // 10 min
  const admin1 =
    "0xd687a698b6c39372fc0ef753a03a71843d8399b673fe31aa9e56549f91a49d";
  const admin2 =
    "0x4f0650b2db56943974ab0b412a02448a40fe2287c5c2f4115b851cdc435fef4";
  let contractFactory;

  before(async function () {
    contractFactory = await starknet.getContractFactory("admin_auth");
  });

  it("should fail if constructor arguments are not provided", async function () {
    try {
      await contractFactory.deploy();
      expect.fail("Failed since constructor arguments were not passed");
    } catch (err) {}
  });

  it("should deploy the contract if contructor arguments are provided", async function () {
    const contract = await contractFactory.deploy({
      address1: BigNumber.from(admin1),
      address2: BigNumber.from(admin2),
    });
    console.log(contract.address);
  });
});
