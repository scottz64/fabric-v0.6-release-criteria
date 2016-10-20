#!/bin/bash

date; echo "Start new network, and run all LedgerStressTests in the Regression Suite:"
echo "BasicFuncExistingNetworkLST.go LST_1client1peer20K.go LST_2client1peer20K.go LST_2client2peer20K.go LST_4client1peer20K.go LST_4client4peer20K.go"

##### start anew:

export CORE_PBFT_GENERAL_BATCHSIZE=500
export TEST_EXISTING_NETWORK=FALSE

cd ../ledgerstresstests

../automation/local_fabric_gerrit.sh -n 4 -b $CORE_PBFT_GENERAL_BATCHSIZE -s -c $COMMIT

##### Run LedgerStressTest Regression Tests, using the existing network
##### Ensure no envvars override the parms that each testcase uses

export TEST_EXISTING_NETWORK=TRUE
export TEST_LST_TX_COUNT=""
export TEST_LST_NUM_CLIENTS=""
export TEST_LST_NUM_PEERS=""
export TEST_LST_THROUGHPUT_RATE=""

# these LST tests generate their own log files, so we can simply use "go run" instead of using go_record.sh or tee the output to a file.
date; echo "==================== Start of LST - REST API Test ===================="
date; go run BasicFuncExistingNetworkLST.go
date; echo "==================== Start of LST - Regression Tests ===================="
date; go run LST_1client1peer20K.go
date; go run LST_2client1peer20K.go
date; go run LST_2client2peer20K.go
date; go run LST_4client1peer20K.go
date; go run LST_4client4peer20K.go
#date; go run LST_4client1peer1M.go
date; echo "==================== End of LST Regression Tests, 100,000 total transactions for 5 tests (plus a few from earlier tests) ===================="

