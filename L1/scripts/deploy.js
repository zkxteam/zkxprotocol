const fs = require("fs");
const { artifacts } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("Deploying contracts with the account:", deployer.address);

  console.log("Account balance:", (await deployer.getBalance()).toString());

  // const Token = await ethers.getContractFactory("ZKXToken");
  // const token = await Token.deploy();

  // console.log("ZKX Token smart contract address:", token.address);

  const Bridge = await ethers.getContractFactory("L1ZKXContract");
  //Passing Starknet core contract address and ZKX asset contract address
  const bridge = await Bridge.deploy(
    %%StarknetCoreContractAddress%%, //"0xde29d060D45901Fb19ED6C6e959EB22d8626708e",
    %%AssetContractAddress%%, //"0x3f4b9335d1ff39f7742cc2c2b20e7ce6670e2eb4e1c29e5a410b1c293100f31",
    %%WithdrawalRequestContractAddress%% //"0x02bb42772fbe52ec8b8a3fc5db12369aaf1cc5a95c20e88a0ef8c2d4b5ab1a24"
  );
  console.log("L1 ZKX smart contract address:", bridge.address);

  const data_bridge = {
    address: bridge.address,
    abi: JSON.parse(bridge.interface.format("json")),
  };

  if (!fs.existsSync("artifacts/ABI")) fs.mkdirSync("artifacts/ABI");
  fs.writeFileSync("artifacts/ABI/Bridge.json", JSON.stringify(data_bridge), {
    flag: "w",
  });

  // const data_token = {
  //     address: token.address,
  //     abi: JSON.parse(token.interface.format('json'))
  // };
  // fs.writeFileSync('artifacts/ABI/Token.json', JSON.stringify(data_token));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
