package main

import (
	"../lstutil"
)

/*************** Test Objective : Ledger Stress with 4 Clients and 4 Peers, Long Run, approx 3 days ************
* 
*   1. Connect to a 4 node peer network with security enabled, and deploy a modified version of
*	chaincode_example02 that stores an additional block of data with every transaction
*	Refer to lstutil.go for more details, including parameters and further configuration.
*   2. Invoke transactions in parallel, divided among each go client thread on the peer
*   3. Check if the expected total counter value matches with query values
* 
*   To use this test script:			go run <testname.go>
*   or (to save output files):			../automation/go_record.sh <testname.go>
* 
***********************************************************************************************/

func main() {
	// args:  testname, # client threads, # peers, total # transactions
	lstutil.RunLedgerStressTest( "LST_4client4peer4M", 4, 4, 3000000 )
}
