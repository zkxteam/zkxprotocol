// SPDX-License-Identifier: Apache-2.0.
pragma solidity 0.8.14;

interface IMultisig {
    ////////////////
    // Data types //
    ////////////////

    enum Status {
        Absent,
        Pending,
        Executed,
        Canceled
    }

    struct Call {
        address toAddress;
        string selector;
        bytes data;
        uint256 value;
    }

    struct Transaction {
        address initiator;
        Status status;
        uint32 approvals;
        uint128 delay;
        uint128 quorumTime;
    }

    //////////
    // Read //
    //////////

    function totalTransactions() external view returns (uint256);

    function getTxInfo(uint256 id) external view returns (Transaction memory);

    function getTxCalls(uint256 id) external view returns (Call[] memory);

    function isTxApproved(uint256 id, address user)
        external
        view
        returns (bool);

    ///////////
    // Write //
    ///////////

    function proposeTx(Call[] calldata calls, uint128 delay) external;

    function executeTx(uint256 id) external payable;

    function cancelTx(uint256 id) external;

    function approve(uint256 id) external;

    function removeApproval(uint256 id) external;

    ////////////
    // Events //
    ////////////

    event TxProposed(uint256 indexed id, uint128 delay);
    event TxExecuted(uint256 indexed id);
    event TxCanceled(uint256 indexed id);
    event TxApproved(uint256 indexed id);
    event TxApprovalRemoved(uint256 indexed id);
    event TxQuorumReached(uint256 indexed id);
    event TxQuorumDissolved(uint256 indexed id);
}
