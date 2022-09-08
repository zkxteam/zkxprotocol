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

	/// @notice Total number of transactions
    function totalTransactions() external view returns (uint256);

	/// @notice Information about tx initiator, status, approval count, delay and quorum time
	/// @param id - id of tx
	/// @return - Transaction object, containing information about tx
    function getTxInfo(uint256 id) external view returns (Transaction memory);

	/// @notice Provides information about tx calls
	/// @param id — id of tx
	/// @return — Array of tx calls to be executed
    function getTxCalls(uint256 id) external view returns (Call[] memory);

	/// @notice Was tx approved by admin?
	/// @param id — id of tx
	/// @param admin — admin address
	/// @return — Bool value telling if this admin has approved the tx
    function isTxApproved(uint256 id, address admin)
        external
        view
        returns (bool);

	/// @notice Was tx approved by admin?
	/// @dev Should be called before tx execution to prevent failure and lost gas
	/// @param id — id of tx
	/// @param value — value amount that will be passed to executeTx function
	/// @return — Bool value telling if tx can be executed
	function canBeExecuted(uint256 id, uint256 value)
        external
        view
        returns (bool);

    ///////////
    // Write //
    ///////////

	/// @notice Propose tx for confirmation and execution
	/// @param calls - array of calls to be executed during tx execution
	/// @param delay — delay in seconds between tx confirmation and execution
    function proposeTx(Call[] calldata calls, uint128 delay) external;

	/// @notice Execute already confirmed tx
	/// @param id — id of tx to be executed
    function executeTx(uint256 id) external payable;

	/// @notice Cancel tx
	/// @param id — id of tx to be canceled
    function cancelTx(uint256 id) external;

	/// @notice Approve tx
	/// @param id — id of tx to be approved
    function approve(uint256 id) external;

	/// @notice Remove already given approval for tx
	/// @param id — id of tx
    function removeApproval(uint256 id) external;

    ////////////
    // Events //
    ////////////

	/// @notice Triggered when new tx was proposed
    event TxProposed(uint256 indexed id, uint128 delay);

	/// @notice Triggered when tx was executed
    event TxExecuted(uint256 indexed id);

	/// @notice Triggered when tx was canceled
    event TxCanceled(uint256 indexed id);

	/// @notice Triggered when some admin approved a tx
    event TxApproved(uint256 indexed id);

	/// @notice Triggered when some admin removed tx approval
    event TxApprovalRemoved(uint256 indexed id);

	/// @notice Triggered when required number of approvals was reached
    event TxQuorumReached(uint256 indexed id);

	/// @notice Triggered when tx approvals dropped below required number of approvals
    event TxQuorumDissolved(uint256 indexed id);
}
