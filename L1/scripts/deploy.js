const fs = require("fs");

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
    %%StarknetCoreContractAddress%% //"0xde29d060D45901Fb19ED6C6e959EB22d8626708e"
    %%L2AssetContractAddress%% //"0x053d0b4b4fddbcc728414ba3077716b4d5c09b284ab095fb2824bac2f7f6412c"
  );
  console.log("L1 ZKX smart contract address:", bridge.address);

  const data_bridge = {
    address: bridge.address,
    abi: JSON.parse(bridge.interface.format("json")),
  };
  fs.writeFileSync("artifacts/ABI/Bridge.json", JSON.stringify(data_bridge));

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
