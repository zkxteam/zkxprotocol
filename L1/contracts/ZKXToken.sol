// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract ZKXToken is ERC20 {
    constructor() ERC20("USDZ Token", "USDZ") {}

    /**
     * @dev function to mint tokens
     * @param to The address to mint tokens to.
     * @param amount The amount of tokens to be minted
     **/
    function mint(address to, uint256 amount) public {
        _mint(to, amount);
    }

    /**
     * @dev Function which returns the decimals of the ERC20 token
     */
    function decimals() public pure override returns (uint8) {
        return 6;
    }
}
