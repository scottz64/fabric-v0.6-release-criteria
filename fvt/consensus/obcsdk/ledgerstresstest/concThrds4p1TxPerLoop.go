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

var loopCtr, numReq, numPeers int
var failedToSend int64
var MY_CHAINCODE_NAME string = "concurrency"

func main() {

	////////////////////////////////////////////////////////////////////////////////////////////////
	// Configuration

	lstutil.TESTNAME = "concThrds4p1TxPerLoop"
	lstutil.FinalResultStr = ("FINAL RESULT ")

	numPeers = 4

	// How long should the test run?
        // 1 min            60  unit = seconds
        // 1 hr           3600
        // 12 hr         43200
        // 1 day         86400
        // 2 day        172800
        // 3 day        259200 (72 hr)

        //var numSecs int64 = 60
        var numSecs int64 = 60

	// Each of 4 peers starts "numReq" number of GO threads in parallel. A value of 25
	// implies that 100 Tx are sent concurrently - once per InvokeLoop, break, InvokeLoop, etc.
	// Using larger numbers would allow more to be sent in parallel - but it would also
	// cause extreme resource contention where this test program uses most of the processor
	// to send Invokes, leaving less for the peers to actually start processing them.
	// In other words, for example, using 250 (which sends 1000 concurrent Tx) would cause
	// a vast majority of the Tx to simply be queued up during the time (minute) we send them,
	// and then we poll and wait until all those queued Tx are processed.

	// Using 25 (create 100 go threads to each send one Tx concurrently, then close the threads, and
	// then do it again repeatedly for a minute), it sends about 2000+ total transactions in a minute.
	// 
	// Using 250 (sending 1000 Tx concurrently), it sends about 6000+ total transactions in a minute.
	// It takes at least 7 secs to get them sent, due to test threads competing for same CPU and other delays.
	// However, virtually all of them are processed AFTER we are done sending transactions after a minute.

  	//numReq = 250	// number of threads on each peer. 250 implies max 1000 invokes per secs_interval
  	numReq = 250

	//var secs_interval int64 = 1	// each InvokeLoop uses at least this many secs (and sleeps if completed early)
	var secs_interval int64 = 10	// each InvokeLoop uses at least this many secs (and sleeps if completed early)

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

	starterString := fmt.Sprintf("START %s : Use %d concurrent go-threads on each of %d peers, send 1 Tx per thread every %d secs, for total %d secs =========", lstutil.TESTNAME, numReq, numPeers, secs_interval, numSecs)
        fmt.Fprintln(lstutil.Writer,starterString)
        lstutil.Writer.Flush()
        lstutil.Logger(starterString)

        defer lstutil.TimeTracker(time.Now())

	fmt.Println("Using an existing docker network")
	_ = chaincode.InitNetwork()
	chaincode.InitChainCodes()
	chaincode.RegisterUsers()

        //data := lstutil.RandomString(1024)
        data := lstutil.FixedString(1024)

	time.Sleep(10 * time.Second)

	fmt.Println("\nPOST/Chaincode: Deploying chaincode ", MY_CHAINCODE_NAME)
        //dAPIArgs0 := []string{MY_CHAINCODE_NAME, "init", "PEER1"}
        dAPIArgs0 := []string{MY_CHAINCODE_NAME, "init", peernetwork.PeerName(1)}
        depArgs0 := []string{"a", data, "counter", "0"}
        chaincode.DeployOnPeer(dAPIArgs0, depArgs0)
        //time.Sleep(120 * time.Second)
        time.Sleep(60 * time.Second)
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
	// Loop to send all the transactions concurrently 

	failedToSend = 0
        loopCtr = 0
        start := time.Now().Unix()
	timer := start
        endTime := start + numSecs
        fmt.Println("Start, End, time.Now: ", start, endTime, time.Now())
	fmt.Println("loopCtr, TxCount, TimeNow")
	fmt.Println("-------  -------  -------")
	prevtime := timer
	var endlooptime int64 = 0
        for timer < endTime {
	    InvokeLoop(numReq, data)
            loopCtr++
            timer = time.Now().Unix()
            fmt.Println(loopCtr, loopCtr*numPeers*numReq, timer)
	    endlooptime = prevtime + secs_interval
	    if timer < endlooptime { time.Sleep(time.Second * time.Duration(endlooptime - timer)) } // sleep if time remaining unused from the interval
            prevtime = endlooptime
            timer = time.Now().Unix()
  	}
        requestedTx := int64(loopCtr * numReq * numPeers)
        if failedToSend > 0 { fmt.Println(fmt.Sprintf("ERROR: chaincode could not get valid TxID for all Invokes requested; FailedToSend = %d", failedToSend)) }
        expectedTx := requestedTx + startCounter - failedToSend
        fmt.Println(fmt.Sprintf("Done with loop sending transactions, elapsed = %d secs. Querying peers.\n  Tx requested = %d\n  FailedToSend = %d\n  startTxCounter = %d\n  expectedTxCountFinal = %d", (timer-start), requestedTx, failedToSend, startCounter, expectedTx))


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
	postStr := fmt.Sprintf("counter = %d (expected=%d), numSecs=%d, concurrentThreads=%d", curr, expectedTx, numSecs, numReq * numPeers)
	fmt.Println("Recovery secs to catch up processing transactions, after stopped sending them: ", time.Now().Unix() - recoverStart)

	lstutil.FinalResultStr += fmt.Sprintf("%s %s, %s", result, lstutil.TESTNAME, postStr)
}

func InvokeLoop(numReq int, data string) {
	var wg sync.WaitGroup
	iAPIArgs := []string{"a", data, "counter"}
	wg.Add(numPeers*numReq)

	for p := 0 ; p < numPeers ; p++ {
		go func(p int) {
			//fmt.Println("debuginfo: threads, peerNum, peerName: ", numReq, p, peernetwork.PeerName(p))
			invArgs0 := []string{"concurrency", "invoke", peernetwork.PeerName(p)}
			k := 1
			for k <= numReq {
				go func() {
					_, err := chaincode.InvokeOnPeer(invArgs0, iAPIArgs)
					if err != nil { atomic.AddInt64(&failedToSend, 1) }
					wg.Done()
				}()
				k++
			}
			//fmt.Println("# of Req Invoked on PEER ", p, k-1)
		}(p)
	}
	wg.Wait()
}

func QueryValAndHeight(expectedCtr int64) (passed bool, cntr int64) {
	// Note: this function is optimized for 4 peers. For more, try using chco2 or lstutil functions.

	cntr = 0
	passed = false

	fmt.Println("\nPOST/Chaincode: Querying counter from chaincode ", MY_CHAINCODE_NAME)
	qAPIArgs00 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(0)}
	qAPIArgs01 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(1)} 
	qAPIArgs02 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(2)}
	qAPIArgs03 := []string{MY_CHAINCODE_NAME, "query", peernetwork.PeerName(3)}

	qArgsb := []string{"counter"}

	resCtr0, _ := chaincode.QueryOnHost(qAPIArgs00, qArgsb)
	resCtr1, _ := chaincode.QueryOnHost(qAPIArgs01, qArgsb)
	resCtr2, _ := chaincode.QueryOnHost(qAPIArgs02, qArgsb)
	resCtr3, _ := chaincode.QueryOnHost(qAPIArgs03, qArgsb)


	ht0, _ := chaincode.GetChainHeight( peernetwork.PeerName(0))
	ht1, _ := chaincode.GetChainHeight( peernetwork.PeerName(0))
	ht2, _ := chaincode.GetChainHeight( peernetwork.PeerName(2))
	ht3, _ := chaincode.GetChainHeight( peernetwork.PeerName(3))

	fmt.Println("Ht in  PEER0 : ", ht0)
	fmt.Println("Ht in  PEER1 : ", ht1)
	fmt.Println("Ht in  PEER2 : ", ht2)
	fmt.Println("Ht in  PEER3 : ", ht3)

	resCtrI0, _ := strconv.Atoi(resCtr0) 
	resCtrI1, _ := strconv.Atoi(resCtr1) 
	resCtrI2, _ := strconv.Atoi(resCtr2) 
	resCtrI3, _ := strconv.Atoi(resCtr3) 

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
			fmt.Printf("Pass: %d PEERS MATCH expectedCounter=%d and ALL Heights match=%d\n", matches, expectedCtr, ht0)
		} else {
			if ( ht0 == ht1 && ht0 == ht2 ) ||
			   ( ht0 == ht1 && ht0 == ht3 ) ||
			   ( ht0 == ht2 && ht0 == ht3 ) ||
			   ( ht1 == ht2 && ht1 == ht3 ) {
				passed = true
				fmt.Printf("Pass: %d PEERS MATCH expectedCounter=%d, and 3 HEIGHTS MATCH: ht0=%d ht1=%d ht2=%d ht3=%d\n", matches, expectedCtr, ht0, ht1, ht2, ht3)
			} else {
				fmt.Printf("Fail: %d PEERS MATCH expectedCounter=%d, BUT HEIGHTS NOT MATCHING: ht0=%d ht1=%d ht2=%d ht3=%d\n", matches, expectedCtr, ht0, ht1, ht2, ht3)
			}
		}
	} else {
		fmt.Printf("Fail: expectedCounter=%d is matched on only %d peers\nresCtr0:  %d\nresCtr1:  %d\nresCtr2:  %d\nresCtr3:  %d\n", expectedCtr, matches, resCtrI0, resCtrI1, resCtrI2, resCtrI3)
	}
	return passed, cntr
}

