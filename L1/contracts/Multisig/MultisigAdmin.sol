// SPDX-License-Identifier: Apache-2.0.
pragma solidity 0.8.14;

import {IMultisig} from "./IMutisig.sol";

contract MultisigAdmin is IMultisig {
    //////////////
    // Settings //
    //////////////

    uint32 public immutable quorum;
    uint256 public constant MIN_DELAY = 10 minutes;
    uint256 public constant MAX_DELAY = 30 days;
    uint256 public constant EXECUTION_PERIOD = 7 days;

    /////////////
    // Storage //
    /////////////

	uint256[] private allTransactions;
    mapping(uint256 => Transaction) private txById;
    mapping(uint256 => Call[]) private txCallsById;
    mapping(uint256 => mapping(address => bool)) isApproved;
    mapping(address => bool) public isAdmin;

    /////////////////
    // Constructor //
    /////////////////

    constructor(uint32 _quorum, address[] memory _admins) {
        require(
            _quorum > 1 && uint256(_quorum) < _admins.length,
            "Invalid _quorum value"
        );
        quorum = _quorum;
        for (uint256 i = 0; i < _admins.length; i++) {
            address admin = _admins[i];
            require(admin != address(0), "Zero address passed as admin");
            require(!isAdmin[admin], "Duplicate admin");
            isAdmin[admin] = true;
        }
    }

    //////////
    // View //
    //////////

	function getAllTxIds() external view returns (uint256[] memory) {
		return allTransactions;
	}

    function getTxInfo(uint256 id) external view returns (Transaction memory) {
        return txById[id];
    }

    function getTxCalls(uint256 id) external view returns (Call[] memory) {
        return txCallsById[id];
    }

    function isTxApproved(uint256 id, address admin)
        external
        view
        returns (bool)
    {
        return isApproved[id][admin];
    }

    function canBeExecuted(uint256 id, uint256 value)
        external
        view
        returns (bool)
    {
        // 1. Check status and quorum
        Transaction storage _tx = txById[id];
        bool isTxPending = _tx.status == Status.Pending;
        bool isQuorumReached = _tx.approvals >= quorum;

        // 2. Check execution date
        bool isQuorumDateSet = _tx.quorumTime != 0;
        uint256 earliestExecuteDate = uint256(_tx.quorumTime + _tx.delay);
        bool isDelayPassed = block.timestamp >= earliestExecuteDate;
        bool isNotExpired = block.timestamp <= earliestExecuteDate + EXECUTION_PERIOD;

        // 3. Check ETH value to be spent
        uint256 valueToBeSpent = 0;
		Call[] memory calls = txCallsById[id];
        for (uint256 i = 0; i < calls.length; i++) {
            valueToBeSpent += calls[i].value;
        }
        bool isEnoughValue = value >= valueToBeSpent;

        // 4. Result
        return
            isTxPending &&
            isQuorumReached &&
            isQuorumDateSet &&
            isDelayPassed &&
            isNotExpired &&
            isEnoughValue;
    }

    ///////////
    // Write //
    ///////////

	function fund() external payable {
		/* Does nothing, just receives ether */
	}

    function proposeTx(uint256 id, Call[] calldata calls, uint256 delay)
        external
        onlyAdmins
    {
        // 1. Validate tx
		require(txById[id].status == Status.Absent, "Tx already exists");
        require(calls.length > 0, "No calls provided");
        require(delay >= MIN_DELAY && delay <= MAX_DELAY, "Invalid delay");

        // 2. Store tx
		allTransactions.push(id);
        txById[id] = Transaction({
            initiator: msg.sender,
            status: Status.Pending,
            approvals: 0,
            delay: uint128(delay),
            quorumTime: 0
        });

        // 3. Store tx calls
        Call[] storage txCalls = txCallsById[id];
        for (uint256 i = 0; i < calls.length; i++) {
            require(
                calls[i].toAddress != address(0),
                "Invalid call to 0 address"
            );
            txCalls.push(calls[i]);
        }

        // 4. Emit event
        emit TxProposed(id, delay);
    }

    function approve(uint256 id) external onlyAdmins {
        // 1. Ensure can approve
        Transaction storage _tx = txById[id];
        require(_tx.status == Status.Pending, "Tx not in Pending status");
        require(!isApproved[id][msg.sender], "Tx already approved by caller");

        // 2. Add approval
        isApproved[id][msg.sender] = true;
        _tx.approvals++;
        emit TxApproved(id);

        if (_tx.approvals == quorum) {
            _tx.quorumTime = uint128(block.timestamp);
            emit TxQuorumReached(id);
        }
    }

    function removeApproval(uint256 id) external onlyAdmins {
        // 1. Ensure has approved
        Transaction storage _tx = txById[id];
        require(_tx.status == Status.Pending, "Tx not in Pending status");
        require(isApproved[id][msg.sender], "Tx not approved by caller");

        // 2. Remove approval
        isApproved[id][msg.sender] = false;
        _tx.approvals--;
        emit TxApprovalRemoved(id);

        if (_tx.approvals == quorum - 1) {
            _tx.quorumTime = 0;
            emit TxQuorumDissolved(id);
        }
    }

    function executeTx(uint256 id) external payable onlyAdmins {
        // 1. Ensure tx can be executed
        Transaction storage _tx = txById[id];
        require(_tx.status == Status.Pending, "Tx not in Pending status");
        require(_tx.approvals >= quorum, "Quorum not reached");
        require(_tx.quorumTime != 0, "Unknown when quorum was reached");
        uint256 earliestExecuteDate = uint256(_tx.quorumTime + _tx.delay);
        require(block.timestamp >= earliestExecuteDate, "Too early");
        require(block.timestamp <= earliestExecuteDate + EXECUTION_PERIOD, "Tx expired");

        // 2. Execute tx
        _tx.status = Status.Executed;
        Call[] storage calls = txCallsById[id];
        uint256 valueSpent = 0;
        for (uint256 i = 0; i < calls.length; i++) {
            Call storage call = calls[i];
            bytes memory data = prepareCalldata(call);
            (bool isSuccess, ) = call.toAddress.call{value: call.value}(data);
            require(isSuccess);
            valueSpent += call.value;
        }

        // 3. Check value spent
        require(msg.value >= valueSpent, "Insufficient msg.value");

        // 4. Emit executed event
        emit TxExecuted(id);
    }

    function cancelTx(uint256 id) external onlyAdmins {
        // 1. Ensure tx can be canceled
        Transaction storage _tx = txById[id];
        require(_tx.status == Status.Pending, "Tx not in Pending status");
        require(_tx.initiator == msg.sender, "Caller is not tx initiator");

        // 2. Cancel tx
        _tx.status = Status.Canceled;
        emit TxCanceled(id);
    }

    /////////////
    // Private //
    /////////////

    function prepareCalldata(Call memory call)
        public
        pure
        returns (bytes memory)
    {
        bytes memory selectorAsBytes = bytes(call.selector);
        if (selectorAsBytes.length == 0) {
            return call.data;
        } else {
            bytes4 selector4Bytes = bytes4(keccak256(selectorAsBytes));
            return abi.encodePacked(selector4Bytes, call.data);
        }
    }

    modifier onlyAdmins() {
        require(isAdmin[msg.sender], "User is not admin");
        _;
    }
}
