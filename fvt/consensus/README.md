
# Release Criteria for Functional Area: Consensus

## Consensus Acceptance Testcases (CAT)

GO SDK tests were executed on local fabric in vagrant environment with docker containers.
Additional details (the date the tests were run, commit image, test config parameters, the test steps,
output summary and details, etc.) are available in the GO_TEST files in this folder.

### CAT test naming convention 

The testnames themselves indicate the steps performed. For example:

	CAT_210_S2S1_IQ_R1_IQ.go	Consensus Acceptance Test (CAT) suite, testcase number 210
	       _S2S1			Stop Validating PEERs VP2 and VP1 at virtually the same time
	            _IQ			Send some Invoke requests to all running peers, and Query all to validate A/B/ChainHeight results
	               _R1		Restart VP1
	                  _IQ		Send some Invoke requests to all running peers, and Query all to validate A/B/ChainHeight results

## Test Coverage

The objective of Consensus Acceptance Tests (CAT) is to ensure the stability and resiliency of the
PBFT Batch design when Byzantine faults occur in a 4 peer network.
Test areas coverage:

Stop 1 peer: the network continues to process deploys, invokes, and query transactions.
Perform this operation on each peer in the fabric.
While exactly 3 peers are running, their ledgers will remain in synch.
(In a 4 peer network, 3 represents 2F+1, the minimum number required for consensus.)
Restarting a 4th peer will cause it to join in the network operations again.
Note: when queried after having been restarted, the ledger on extra peers ( additional nodes beyond  2(F+1) )
may appear to lag for some time. It will catch up if another peer is stopped (leaving it as one of
exactly 2F+1 participating peers), OR, with no further disruptions in the network,
it could catch up after huge numbers of transaction batches are processed. 

Stop 2 peers: the network should halt advancement, due to a lack of consensus.
Restarting 1 or 2 peers will cause the network to resume processing transactions because
enough nodes are available to reach consensus. This may include processing transactions
that were received and queued by any running peers while consensus was halted. 

Stop 3 peers: the network should halt advancement due to a lack of consensus.
Restarting just one of the peers should not resume consensus.
Restarting 2 or 3 peers should cause the network to resume consensus. 

Deploys should be processed, or queued if appropriate, with any number of running peers.


## RESULTS SUMMARY

	Date       Testcases     Pass/Fail   Release   Commit       Time       Notable Parameters
	20160928   CAT 100-410   39 /  7     v0.6      gerritv0.6   8h00m31s   batchsize=2          
	 
	Issues Found
	FAB-331 FAB-332 FAB-333 FAB-334 FAB-335 FAB-336 FAB-337

	FAILED Testcases:
	CAT_111_SnIQRnIQ_cycleDownLoop.go
	CAT_303_S0S1S2_IQ_R0R1R2_IQ.go
	CAT_305_S1S2S3_IQ_R1R2R3_IQ.go
	CAT_407_S0S1S2_D_I_R0R1_IQ.go
	CAT_408_S0S1S2_D_I_R0R1R2_IQ.go
	CAT_409_S1S2S3_D_I_R1R2_IQ.go
	CAT_410_S1S2S3_D_I_R1R2R3_IQ.go

