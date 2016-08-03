
# Release Criteria for Functional Area: Consensus

## Testing was done to ensure the stability and resiliency of the PBFT Batch design when Byzantine faults occur. Test objectives:

A.  	Stop 1 peer: the network continues to process deploys, invokes, and query transactions. Perform this operation on each peer in the fabric.
	Restarting the peer should cause it to join in the network operations. Note: although F (the minimum number required for consensus) peers
	should always remain synched up, the extra peer may appear to lag until another peer stops.

B. 	Stop 2 peers: the network should halt due to a lack of consensus. Restarting 1 or 2 peers should cause the network to resume consensus,
	including processing all transactions received and queued by any running peers while consensus was halted; and one restarted peer
	should sync up after enough invokes and exactly match CH/A/B.
	
C.	Stop 3 peers: the network should halt due to a lack of consensus. Restarting just one of the peers should not resume consensus.
	Restarting 2 or 3 peers should cause the network to resume consensus.

D.  	Deploys should be processed, or queued if necessary, with any number of running peers.


## Consensus Acceptance Tests

On July 27, 2016: 
The following GO SDK testnames were executed on local fabric in vagrant environment with docker containers.
Additional details (the date the tests were run, commit image, test config parameters, the test steps, output summary and details, etc.)
are available in the GO_TEST files in this folder.
Results are indicated first - either PASS or the test_escape #issue created on https://github.com/hyperledger/fabric/issues

The testnames themselves indicate the steps performed. For example, CAT_01_S1_IQDQIQ.go may be interpreted as:

	CAT_01_	Consensus Acceptance Test, number 01
	S1	Stop Validating PEER 1
	I	Invokes sent to all running peers
	Q	Query sent to all running peers and validate results
	D	Deploy sent to a running peer
	Q	Query sent to all running peers and validate results
	I	Invokes sent to all running peers
	Q	Query sent to all running peers and validate results


A.  	Stop 1 peer: the network continues to process deploys, invokes, and query transactions. Perform this operation on each peer in the fabric.
	Restarting the peer should cause it to join in the network operations. Note: although F (the minimum number required for consensus) peers
	should always remain synched up, the extra peer may appear to lag until another peer stops.

 PASS	CAT_01_S1_IQDQIQ.go			Stop a secondary peer. Send Invokes and new Deploy. Query to verify CH/A/B in sync in all running peers.
 PASS	CAT_02_S0_IQDQIQ.go			Stop the primary peer. Send Invokes and new Deploy. Query to verify CH/A/B in sync in all running peers.
 PASS	CAT_03_SnIQRnIQ_CycleAndRepeat.go		Stop/restart each VP, never losing consensus. Send Invokes and Queries at all steps. Repeat 3 cycles.
 PASS	CAT_04_SnIQRnIQDQIQ_CycleAndRepeat.go	Stop/restart each VP, never losing consensus, and some Deploys while all 4 peers running. Repeat 3 cycles.
 PASS	CAT_05_S1_IQDQIQ_R1_IQIQ_repeats.go	Stop/Deploy/Restart a single VP peer repeatedly. Invokes/Queries at all steps.
 PASS	CAT_06_S1_IQDQIQ_R1_IQ_S2_IQ.go		Stop/Deploy/Restart a single peer. Stop another secondary peer, and verify in sync (exact matching CH/A/B).
 PASS	CAT_07_S1_IQDQIQ_R1_IQ_S0_IQ.go		Stop/Deploy/Restart a single peer. Stop primary peer, and verify exact matching CH/A/B.
 PASS	CAT_08_S0_IQDQIQ_R0_IQIQ_repeats.go	Stop/Deploy/Restart primary peer repeatedly. Invokes/Queries at all steps.
 PASS	CAT_09_S0_IQDQIQ_R0_IQ_S2_IQ.go		Stop/Deploy/Restart primary peer. Stop secondary peer VP2, and verify exact matching CH/A/B.
 PASS	CAT_10_S0_IQDQIQ_R0_IQ_S1_IQ.go		Stop/Deploy/Restart primary peer. Stop alternate primary peer VP1, and verify exact matching CH/A/B.

B. 	Stop 2 peers: the network should halt due to a lack of consensus. Restarting 1 or 2 peers should cause the network to resume consensus,
	including processing all transactions received and queued by any running peers while consensus was halted; and one restarted peer
	should sync up after enough invokes and exactly match CH/A/B.

 PASS	CAT_11_S2S1_IQDIQ.go			Stop 2 secondary peers. Invokes/Query (no consensus). Deploy/Invokes/Query (queued, but not deployed yet).
 PASS	CAT_12_S0S1_IQDI.go			Stop VP 0,1. Invokes/Query (no consensus). Deploy/Invoke.
 PASS	CAT_13_S2_IQDQIQ_S1_IQDD.go		Stop a peer, new Deploy and stop another peer. More new Deploys (recv transaction ID, but cannot query it yet).
 PASS	CAT_14_S0_IQDQIQ_S1_IQDD.go		Stop VP0, new Deploy and stop VP1. New Deploys (recv transaction ID, but cannot query it yet).
 PASS	CAT_15_S1_IQ_S2_R1_IQ.go		One at a time, stop 2 secondary peers. Restart the first, and verify matching CH/A/B.
 PASS	CAT_16_S2_IQ_S1_IQ_R1_IQ.go	One at a time, stop 2 secondary peers. Invokes/Query. Restart the second, and verify matching CH/A/B.
 PASS	CAT_17_S1_IQ_S0_R0_IQ.go		One at a time, stop VP 1,0. Restart VP0, and verify matching CH/A/B.
 PASS	CAT_18_S0_IQ_S1_IQ_R0_IQ.go	One at a time, stop VP 0,1. Invokes/Query. Restart VP0, and verify matching CH/A/B.
 PASS	CAT_19_S2S1_IQ_R1_IQ.go		Together, stop VP 2,1. Invokes/Query (no consensus; transactions queued). Restart VP1. Verify consensus.
 PASS	CAT_20_S2S1_IQ_R1R2_IQ.go		Together, stop VP 2,1. Invokes/Query (no consensus; transactions queued). Restart both. Verify matching CH/A/B.
 PASS	CAT_21_S0S1_IQ_R0_IQ.go		Together, stop VP 0,1. Invokes/Query (no consensus; transactions queued). Restart VP0. Verify consensus.
 PASS	CAT_22_S0S1_IQ_R0R1_IQ.go		Together, stop VP 0,1. Invokes/Query (no consensus; transactions queued). Restart both. Verify matching CH/A/B.

C.	Stop 3 or 4 peers: the network should halt due to a lack of consensus. Restarting just one of the peers should not resume consensus.
	Restarting 2 (or 3) peers should cause the network to resume consensus.
	[Note:  #2265 out of order transactions is observed in several scenarios.]

 PASS	CAT_23_S0S1S2_IQ_R0_IQ_R1_IQ.go	Stop VP 0,1,2. Invokes/Q (no consensus). Restart VP 0. Invokes/Q (no consensus). Restart VP1. Verify matching CH/A/B.
 #2265	CAT_24_S0S1S2_IQ_R0R1_IQIQ.go	Stop VP 0,1,2. Invokes/Q (no consensus). Restart VP 0,1. Invokes/Q. Verify matching CH/A/B.
 #2308	CAT_25_S0S1S2_IQ_R0R1R2_IQ.go	Stop VP 0,1,2. Invokes/Q (no consensus). Restart all 3 peers. Invokes/Q. Verify consensus, min 3 with matching CH/A/B.
 PASS	CAT_26_S1S2S3_IQ_R1R2_IQ.go	Stop VP 1,2,3. Invokes/Q (no consensus). Restart VP 1,2. Invokes/Q. Verify matching CH/A/B.
 #2308	CAT_27_S1S2S3_IQ_R1R2R3_IQ.go	Stop VP 1,2,3. Invokes/Q (no consensus). Restart all 3 peers. Invokes/Q. Verify consensus, min 3 with matching CH/A/B.
 PASS	CAT_28_S0S1S2S3_R0R1R2_IQ_R3_IQ.go	Stop all peers. Restart VP 0,1,2. Verify matching CH/A/B. Restart VP3. Verify consensus.
 PASS	CAT_29_S0S1S2S3_R0R1R2R3_IQ.go	Stop all peers. Restart all peers. Verify consensus, with a minimum of 3 peers with matching CH/A/B.

D.  	Deploys should be processed, or queued if necessary, with any number of running peers.
	Note:  Future enhancement: when multiple deploys, we should validate all chaincode instances (not just the latest one).

 PASS	CAT_30_DQIQDQIQ.go  		Deploy using SAME init values and hash (ignored). Q.I.Q. Next Deploy using NEW values. Q.I.Q.
 PASS	CAT_31_S1_DQIQDQIQ.go  		Stop secondary peer. Execute Deploy tests.
 PASS	CAT_32_S0_IQ_DQIQDQIQ.go  		Stop primary peer VP0. Execute Deploy tests.
 PASS	CAT_33_S1S2_D_I_R1_IQ.go  		Stop VP 1,2. New Deploy, and Invokes (queued, since no consensus). Restart VP1. Verify new deployment, matching CH/A/B.
 PASS	CAT_34_S0S1_D_I_R0_IQ.go  		Stop VP 0,1. New Deploy, and Invokes (queued, since no consensus). Restart VP0. Verify new deployment, matching CH/A/B.
 PASS	CAT_35_S0S1_D_I_R0R1_IQ.go		Stop VP 0,1. New Deploy, and Invokes (queued, since no consensus). Restart both. Verify new deployment, and consensus.
 #2309	CAT_36_S0S1S2_D_I_R0R1_IQ.go	Stop VP 0,1,2. New Deploy, and Invokes (queued). Restart VP 0,1. Verify new deployment, matching CH/A/B.
 #2313	CAT_37_S0S1S2_D_I_R0R1R2_IQ.go  	Stop VP 0,1,2. New Deploy, and Invokes (queued). Restart all 3 peers. Verify new deployment, consensus.
 #2309	CAT_38_S1S2S3_D_I_R1R2_IQ.go	Stop VP 1,2,3. New Deploy, and Invokes (queued). Restart VP 1,2. Verify new deployment, matching CH/A/B.
 #2313	CAT_39_S1S2S3_D_I_R1R2R3_IQ.go  	Stop VP 1,2,3. New Deploy, and Invokes (queued). Restart all 3 peers. Verify new deployment, consensus.

## RESULTS SUMMARY:

 Testcases    Pass/Fail    Release    Commit    Date    Time    Params non-default
 CAT  1-39     33 /  6     v0.5       3e0e80a   07/26   8 hrs   batchsize=2, DEBUG, nullrequest=1s

## OTHER:

### Long runs:

 PASS	40.  CRT_40_StopAndRestartRandom_12Hrs.go	Stop/restart random peer, never losing consensus. Run for 12 hours.
 #2148	41.  CRT_41_StopAndRestart1or2_12Hrs.go		Cycle through stopping/restarting one, or sometimes two, peers at a time. Run for 12 hours.

### FUTURE TEST IDEAS:

	+ Run with different batch size, timer values, larger F and number of nodes N (not CAT), etc.
	+ DUPLICATE all tests using PAUSE instead of STOP by setting chco2.go constant pauseInsteadOfStop to true.


