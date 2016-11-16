package main

/******************** Testing Objective : processing 1 minute blast of concurrency ********
*   Setup: 4 node local docker peer network with security
*   0. Deploy chaincode concurrency == addrecs == modified example02+add1Kpayload
*   1. Send Invoke Requests on multiple peers using go routines.
*   2. Verify query results match on vp0 and vp1 after invoke
*********************************************************************/

import (
	"fmt"
	"time"
	"../chaincode"
	"sync"
        "strconv"
        "../lstutil"
        "bufio"
        "os"
	"sync/atomic"
	"../peernetwork"
)
var numThreadsPerPeer int
var numPeers int
var numSecs int64
var failedToSend int64
var requestedTx int64
var loopCtr int64
var MY_CHAINCODE_NAME string = "concurrency"
var verbose bool = false

func main() {

	////////////////////////////////////////////////////////////////////////////////////////////////
	// Configuration

	lstutil.TESTNAME = "speedtest10Min4p1Thrd"
	lstutil.FinalResultStr = ("FINAL RESULT ")

	numPeers = 4

	// How long should the test run?
        // 1 min            60  unit = seconds
        // 1 hr           3600
        // 12 hr         43200
        // 1 day         86400
        // 2 day        172800
        // 3 day        259200 (72 hr)

        numSecs = 600

	// Each of 4 peers starts "numThreadsPerPeer" number of GO threads in parallel. A value of 25
	// implies that 100 concurrent processes are sending Invoke requests in parallel. Using larger
	// numThreadsPerPeer would create more threads in parallel - but that would simply worsen the
	// resource contention on a local docker network where this test program
	// uses most of the CPU cycles to send Invokes, leaving less for the peers to actually
	// start processing them. (It would work better on an external/remote network, where
	// the peers would not be competing for processor cycles on the same CPU as this GO program,
	// and so the remote peers could start processing the requests right away.)
	// In other words, for example, using 250 (which sends 1000 concurrent Tx) would cause
	// a vast majority of the Tx to simply be queued up during the time (minute) we send them,
	// and then we poll and wait until all those queued Tx are processed in batches.
	// Thus, this may be more of a test of the queues sizes and parallel processing in the API code
	// (currently REST - but could exercise Node.js if we ever provide that option in the future).
	// 
	// Using 25 on each peer, to create 100 total GO threads each sending Tx concurrently for a minute,
	// with docker containers on the local environment, sends over 9,000 total transactions.
	// 
	// 250 will use 1000 threads sending Tx concurrently, sends about between 11,000 - 14,000
	// total transactions in a minute.
	// Note, with 250, they each send only 14 (on average) in one minute (total 14,000 transactions).
	// 
	// Note: in all tests with all values of numThreadsPerPeer, virtually all of transactions are
	// processed only AFTER we are done sending transactions after a minute.

  	//numThreadsPerPeer = 100		// results in sending more than 12,000 Tx in a minute
  	numThreadsPerPeer = 1


	////////////////////////////////////////////////////////////////////////////////////////////////
	// Open files for output, Setup and Deploy

        var openFileErr error
        lstutil.SummaryFile, openFileErr = os.OpenFile(lstutil.OutputSummaryFileName, os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
        if openFileErr != nil {
                lstutil.Logger(fmt.Sprintf("error opening OutputSummaryFileName=<%s> openFileErr: %s", lstutil.OutputSummaryFileName, openFileErr))
                panic(fmt.Sprintf("error opening OutputSummaryFileName=<%s> openFileErr: %s", lstutil.OutputSummaryFileName, openFileErr))
        }
        defer lstutil.SummaryFile.Close()
        lstutil.Writer = bufio.NewWriter(lstutil.SummaryFile)

	starterString := fmt.Sprintf("START %s : Using %d threads on each of %d peers, send concurrent transactions for %d secs =========", lstutil.TESTNAME, numThreadsPerPeer, numPeers, numSecs)
        fmt.Fprintln(lstutil.Writer,starterString)
        lstutil.Writer.Flush()
        lstutil.Logger(starterString)

        defer lstutil.TimeTracker(time.Now())

	fmt.Println("Using an existing network...")
	_ = chaincode.InitNetwork()
	chaincode.InitChainCodes()
	chaincode.RegisterUsers()

        data := lstutil.RandomString(1024)
        //data := lstutil.FixedString(1024)

	time.Sleep(30 * time.Second)

	fmt.Println("\nPOST/Chaincode: Deploying chaincode ", MY_CHAINCODE_NAME)
        //dAPIArgs0 := []string{MY_CHAINCODE_NAME, "init", "PEER1"}
        dAPIArgs0 := []string{MY_CHAINCODE_NAME, "init", peernetwork.PeerName(1)}
        depArgs0 := []string{"a", data, "counter", "0"}
        chaincode.DeployOnPeer(dAPIArgs0, depArgs0)
        time.Sleep(120 * time.Second)
        fmt.Println("\nPOST/Chaincode: Querying A and B (counter) after deploy >>>>>>>>>>> ")
        qAPIArgs0 := []string{MY_CHAINCODE_NAME, "query"} 
        qArgsa := []string{"a"}
        qArgsb := []string{"counter"}
        A, _ := chaincode.Query(qAPIArgs0, qArgsa)
        B, _ := chaincode.Query(qAPIArgs0, qArgsb)
        myStr := fmt.Sprintf("\nA = %s B= %s", A, B)
        fmt.Println(myStr)
        sc, err := strconv.Atoi(B)
        var startCounter int64 = int64(sc)
	if err != nil { panic("cannot convert initial counter value to integer") }
        passed, curr := QueryValAndHeight(startCounter)
	if !passed {
		fmt.Println("CANNOT GET CONSENSUS on current/start counter!")
		panic("CANNOT START")
	}

	////////////////////////////////////////////////////////////////////////////////////////////////
	// Send all the transactions concurrently from go funcs, for the duration numSecs

        requestedTx = 0
	failedToSend = 0
	InvokeConcurrently(numThreadsPerPeer, data)
        fmt.Println("AFTER Invokes: Total successfully requestedTx, failedSendingTx: ", requestedTx, failedToSend)
        if failedToSend > 0 { fmt.Println(fmt.Sprintf("ERROR: chaincode could not get valid TxID for all Invokes requested; FailedToSend = %d", failedToSend)) }
        expectedTx := requestedTx + startCounter - failedToSend
        fmt.Println(fmt.Sprintf("Done with loop sending transactions.\n  Tx requested = %d\n  FailedToSend = %d\n  startTxCounter = %d\n  expectedTxCountFinal = %d\nQuerying peers for counter and CH.", requestedTx, failedToSend, startCounter, expectedTx))


	////////////////////////////////////////////////////////////////////////////////////////////////
	// Poll to retrieve results, waiting until network processes all the Tx we requested

	result := "FAILED"
        passed, curr = QueryValAndHeight(expectedTx)
	prev := curr-1
        recoverStart := time.Now().Unix()
	for !passed && curr != prev {
		fmt.Println("sleep 1 minute to allow network to process queued transactions, and try again")
		time.Sleep(60 * time.Second)
		prev = curr
        	passed, curr = QueryValAndHeight(expectedTx)
	}
        if passed { result = "PASSED" }
	postStr := fmt.Sprintf("counter = %d (expected=%d), numSecs=%d, numPeers=%d X numConcurrentThreads=%d", curr, expectedTx, numSecs, numPeers, numThreadsPerPeer)
	fmt.Println("Recovery secs to catch up processing transactions, after stopped sending them: ", time.Now().Unix() - recoverStart)

	lstutil.FinalResultStr += fmt.Sprintf("%s %s, %s", result, lstutil.TESTNAME, postStr)
}

func InvokeConcurrently(numThreadsPerPeer int, data string) {
	var wg sync.WaitGroup
	iAPIArgs := []string{"a", data, "counter"}
	wg.Add(numPeers*numThreadsPerPeer)
	timer := time.Now().Unix()
        endTime := timer + numSecs
        fmt.Println("Start, End, time.Now: ", timer, endTime, time.Now())
	if verbose {
		fmt.Println("---- ---- ------ ------")
		fmt.Println("Peer Thrd TxSent Failed")
		fmt.Println("---- ---- ------ ------")
	}
	for p := 0 ; p < numPeers ; p++ {
		// use a go_func for each peer, so we can hopefully create all the threads 4 times as fast
		go func(p int) {
			invArgs0 := []string{"concurrency", "invoke", peernetwork.PeerName(p)}
			k := 1
			for k <= numThreadsPerPeer {
				go func(p int, k int) {
					var failedSend int64 = 0
					var successSend int64 = 0
        				mytimer := timer
					for mytimer < endTime {
						_, err := chaincode.InvokeOnPeer(invArgs0, iAPIArgs)
						if err != nil {
							failedSend++
						} else {
							successSend++
						}
            					mytimer = time.Now().Unix()
					}
					if failedSend > 0 { atomic.AddInt64(&failedToSend, failedSend) }
					atomic.AddInt64(&requestedTx, successSend)
					if verbose {
						fmt.Println(fmt.Sprintf("%4d%5d%7d%7d", p, k, successSend, failedSend))
					}
					wg.Done()
				}(p,k)
				k++
			}
		}(p)
	}
	wg.Wait()
}

func QueryValAndHeight(expectedCtr int64) (passed bool, cntr int64) {
	// Note: this function is optimized for 4 peers. For more, try using chco2 or lstutil functions.

	passed = false
	cntr = 0

	fmt.Println("\nPOST/Chaincode: Querying height and counter from chaincode", MY_CHAINCODE_NAME)
	qAPIArgs00 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(0)}
	qAPIArgs01 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(1)} 
	qAPIArgs02 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(2)}
	qAPIArgs03 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(3)}

	qArgsb := []string{"counter"}

	resCtr0, qe0 := chaincode.QueryOnHost(qAPIArgs00, qArgsb)
	resCtr1, qe1 := chaincode.QueryOnHost(qAPIArgs01, qArgsb)
	resCtr2, qe2 := chaincode.QueryOnHost(qAPIArgs02, qArgsb)
	resCtr3, qe3 := chaincode.QueryOnHost(qAPIArgs03, qArgsb)
	if qe0 != nil || qe1 != nil || qe2 != nil || qe3 != nil {
		fmt.Println("WARNING: error(s): could not query and convert all B values from all peers: qe0 qe1 qe2 qe3", qe0, qe1, qe2, qe3)
	}

	ht0, _ := chaincode.GetChainHeight( peernetwork.PeerName(0))
	ht1, _ := chaincode.GetChainHeight( peernetwork.PeerName(0))
	ht2, _ := chaincode.GetChainHeight( peernetwork.PeerName(2))
	ht3, _ := chaincode.GetChainHeight( peernetwork.PeerName(3))

	fmt.Println("Ht in  PEER0 : ", ht0)
	fmt.Println("Ht in  PEER1 : ", ht1)
	fmt.Println("Ht in  PEER2 : ", ht2)
	fmt.Println("Ht in  PEER3 : ", ht3)

	resCtrI0, e0 := strconv.Atoi(resCtr0) 
	resCtrI1, e1 := strconv.Atoi(resCtr1) 
	resCtrI2, e2 := strconv.Atoi(resCtr2) 
	resCtrI3, e3 := strconv.Atoi(resCtr3) 
	if e0 != nil || e1 != nil || e2 != nil || e3 != nil {
		fmt.Println("WARNING: error(s): could not query and convert all B values from all peers: e0 e1 e2 e3", e0, e1, e2, e3)
	}
	
	cntr = int64(resCtrI0)	// pick peer0 counter to return

        matches := 0
	if int64(resCtrI0) == expectedCtr { matches++ }
	if int64(resCtrI1) == expectedCtr { matches++ }
	if int64(resCtrI2) == expectedCtr { matches++ }
	if int64(resCtrI3) == expectedCtr { matches++ }
	if matches >= 3 {
		if resCtrI0 != resCtrI1 { cntr = int64(resCtrI2) } // set cntr = the consensus value matched by at least 3 peers
		if ht0 == ht1 && ht0 == ht2 && ht0 == ht3 {
			passed = true
			fmt.Printf("Pass: %d PEERS MATCH expectedCounter(%d) and ALL Heights match(%d)\n", matches, expectedCtr, ht0)
		} else {
			if ( ht0 == ht1 && ht0 == ht2 ) ||
			   ( ht0 == ht1 && ht0 == ht3 ) ||
			   ( ht0 == ht2 && ht0 == ht3 ) ||
			   ( ht1 == ht2 && ht1 == ht3 ) {
				passed = true
				fmt.Printf("Pass: %d PEERS MATCH expectedCounter(%d), and 3 HEIGHTS MATCH: ht0=%d ht1=%d ht2=%d ht3=%d\n", matches, expectedCtr, ht0, ht1, ht2, ht3)
			} else {
				fmt.Printf("Fail: %d PEERS MATCH expectedCounter(%d), BUT HEIGHTS NOT MATCHING: ht0=%d ht1=%d ht2=%d ht3=%d\n", matches, expectedCtr, ht0, ht1, ht2, ht3)
			}
		}
	} else {
		fmt.Printf("Fail: expectedCounter(%d) is matched on only %d peers. Query counter results:\nresCtr0:  %d\nresCtr1:  %d\nresCtr2:  %d\nresCtr3:  %d\n", expectedCtr, matches, resCtrI0, resCtrI1, resCtrI2, resCtrI3)
	}
	return passed, cntr
}

