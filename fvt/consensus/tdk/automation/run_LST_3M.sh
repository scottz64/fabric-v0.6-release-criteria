#!/bin/bash

date; echo "Execute a long running test with addrecs chaincode, 3 Million transactions - expected duration about 3 days"

##### start anew:

export CORE_PBFT_GENERAL_BATCHSIZE=500
export TEST_EXISTING_NETWORK=FALSE

cd ../ledgerstresstest

../automation/local_fabric_gerrit.sh -n 4 -b $CORE_PBFT_GENERAL_BATCHSIZE -s -c $COMMIT -l critical

##### Run LedgerStressTest Regression Tests, using the existing network
##### Ensure no envvars override the parms that each testcase uses

export TEST_EXISTING_NETWORK=TRUE
export TEST_LST_TX_COUNT=""
export TEST_LST_NUM_CLIENTS=""
export TEST_LST_NUM_PEERS=""
export TEST_LST_THROUGHPUT_RATE=""

# these LST tests generate their own log files, so we can simply use "go run" instead of using go_record.sh or tee the output to a file.
date;df -h
go run LST_4client4peer3M.go
date;df -h

