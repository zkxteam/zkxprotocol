// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

contract ChainLinkETHStub {
  uint80 public roundId;
  int256 public answer;
  uint256 public startedAt;
  uint256 public updatedAt;
  uint80 public answeredInRound;

  function setPrice(uint80 roundId_, int256 answer_, uint256 startedAt_, uint256 updatedAt_, uint80 answeredInRound_) external {
    roundId = roundId_;
    answer = answer_;
    startedAt = startedAt_;
    updatedAt = updatedAt_;
    answeredInRound = answeredInRound_;
  }

  function decimals() external view returns (uint8) {
    return 18;
  }

  function description() external view returns (string memory) {
    return "chainlink ETH Stub";
  }

  function version() external view returns (uint256) {
    return 1;
  }


  function getRoundData(uint80 _roundId)
    external
    view
    returns (
      uint80,
      int256,
      uint256,
      uint256,
      uint80
    ) {
        return (roundId, answer, startedAt, updatedAt, answeredInRound);
    }

  function latestRoundData()
    external
    view
    returns (
      uint80,
      int256,
      uint256,
      uint256,
      uint80
    ) {
        return (roundId, answer, startedAt, updatedAt, answeredInRound);
    }
}