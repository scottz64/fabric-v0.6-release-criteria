package main

/******************** Testing Objective consensu: Sending Invoke Requests in Parallel ********
*   Setup: 4 node local docker peer network with security and consensus mode using pbft
*   0. Deploy chaincode_example02 with 100000000, 0 as initial args
*   1. Send Invoke Requests in parallel on all peers using go routines, every 10 secs
*   2. query every so often (45 minutes) to confirm results are matching on all peers.
*   3. After specified time (72 hrs), query all peers again to get final result.
*********************************************************************/

import (
	"fmt"
	"os"
	"time"
        "sync"
        "bufio"
        "../threadutil"
	"../lstutil"
	"../chaincode"
	"../peernetwork"
	"../chco2"
	"sync/atomic"
)

var numPeers, numReq int
var numSecs int64
var actuala, actualb, actualch int
var starta, startb int
var curra, currb int64
var failedToSend int64
var MY_CHAINCODE_NAME string =  "example02"
var myNetwork peernetwork.PeerNetwork

func main() {

	lstutil.TESTNAME = "LongRun72hrAuto"
	lstutil.FinalResultStr = ("FINAL RESULT ")

	// 1 min	    60	unit = seconds
	// 1 hr		  3600
	// 12 hr	 43200
	// 1 day	 86400
	// 2 day	172800
	// 3 day	259200 (72 hr)

	numSecs = 259200 

	numReq = 250

	numPeers = 4

	////////////////////////////////////////////////////////////////////////////////////////////////
	// Open files for output, Setup and Deploy

	var openFileErr error
	lstutil.SummaryFile, openFileErr = os.OpenFile(lstutil.OutputSummaryFileName, os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
	if openFileErr != nil {
		fmt.Println(fmt.Sprintf("error opening OutputSummaryFileName=<%s> openFileErr: %s", lstutil.OutputSummaryFileName, openFileErr))
		panic(fmt.Sprintf("error opening OutputSummaryFileName=<%s> openFileErr: %s", lstutil.OutputSummaryFileName, openFileErr))
	}
	defer lstutil.SummaryFile.Close()
	lstutil.Writer = bufio.NewWriter(lstutil.SummaryFile)

	starterString := fmt.Sprintf("START %s : Using %d peers, send occasional Transactions to all peers, for total duration %dd %dh %dm %ds =========", lstutil.TESTNAME, numPeers, numSecs/86400, (numSecs%86400)/3600, (numSecs%3600)/60, numSecs%60)
	fmt.Fprintln(lstutil.Writer,starterString)
	lstutil.Writer.Flush()
	fmt.Println(starterString)
	defer lstutil.TimeTracker(time.Now())

	fmt.Println("Using an existing network...")
	myNetwork = chaincode.InitNetwork()
	chaincode.InitChainCodes()
	chaincode.RegisterUsers()

	//get a URL details to get info n chainstats/transactions/blocks etc.
	aPeer, _ := peernetwork.APeer(myNetwork)
	url := "http://" + aPeer.PeerDetails["ip"] + ":" + aPeer.PeerDetails["port"]
	fmt.Println("Peers on network:")
	chaincode.NetworkPeers(url)

	fmt.Println("\nPOST/Chaincode: Deploying chaincode ", MY_CHAINCODE_NAME)
	dAPIArgs0 := []string{MY_CHAINCODE_NAME, "init"}
	depArgs0 := []string{"a", "100000000", "b", "0"}
	chaincode.Deploy(dAPIArgs0, depArgs0)
	time.Sleep(60 * time.Second)

	actualch = -1
	starta = -1
	startb = -1
	qConsensus := chco2.QueryAllHostsToGetCurrentValues(myNetwork, &starta, &startb, &actualch)
	if !qConsensus {
		fmt.Println(fmt.Sprintf("CANNOT find consensus! A(%d) B(%d) CH(%d)", starta, startb, actualch))
		panic("CANNOT proceed: NO Consensus")
	}
	curra = int64(starta)
	currb = int64(startb)
	fmt.Println(fmt.Sprintf("Initial values:    A=%d B=%d CH=%d", starta, startb, actualch))
	fmt.Println(fmt.Sprintf("Planned Duration:  %dd %dh %dm %ds", numSecs/86400, (numSecs%86400)/3600, (numSecs%3600)/60, numSecs%60))

	//////////////////////////////////////////////////////////////////////////////////////
	// run !!!

	finished := InvokeLoop(numPeers, numReq, numSecs)

	fmt.Println("Reached end of test: attempted, successfullySentTx, failedToSendTx: ", int(currb+failedToSend)-startb, int(currb)-startb, failedToSend)
	fmt.Println("Querying to see if network processed all the Transactions that were successfully sent...")

	//////////////////////////////////////////////////////////////////////////////////////
        // Retrieve results

	time.Sleep(60 * time.Second)
	result := "FAILED"
	timeStr := ""	// if we did not finish (and failed) the test, then the function already printed out the duration until the test stopped itself
	actuala = -1
	actualb = -1
	actualch = -1
	qConsensus = chco2.QueryAllHostsToGetCurrentValues(myNetwork, &actuala, &actualb, &actualch)
	if finished && qConsensus && (actuala == int(curra)) && (actualb == int(currb)) {
		result = "PASSED"
		// remind folks how long we ran:
		timeStr = fmt.Sprintf(", finished total duration %dd %dh %dm %ds", numSecs/86400, (numSecs%86400)/3600, (numSecs%3600)/60, numSecs%60)
	}
	dataStr := fmt.Sprintf("A=%d (expectedA=%d) B=%d (expectedB=%d) ch=%d", actuala, curra, actualb, currb, actualch)
	lstutil.FinalResultStr += fmt.Sprintf("%s %s, %s", result, lstutil.TESTNAME, dataStr+timeStr)
}

func InvokeLoop(numPeers int, numReq int, numSecs int64) (finished bool) {
	var wg sync.WaitGroup
	start := time.Now().Unix()
	endTime := start + numSecs
	currTime := start
	for currTime < endTime {
        	wg.Add(4)
		j := 0
		for j < numPeers {
                        currPeer := threadutil.GetPeer(j) 
			iAPIArgsCurrPeer := []string{"example02", "invoke", currPeer}
			go func() {
				invokeOnOnePeer(j, numReq, iAPIArgsCurrPeer)
				wg.Done()
			}()
			j++
		}
		wg.Wait()
		currTime = time.Now().Unix()
		dur := currTime-start
		actuala = -1
		actualb = -1
		actualch = -1
		qConsensus := chco2.QueryAllHostsToGetCurrentValues(myNetwork, &actuala, &actualb, &actualch)
		if !(qConsensus && (actuala == int(curra)) && (actualb == int(currb))) {
			fmt.Println(fmt.Sprintf("ERROR: A=%d (expectedA=%d) B=%d (expectedB=%d) ch=%d ; aborting after only %dd %dh %dm %ds =========",
				 actuala, curra, actualb, currb, actualch, dur/86400, (dur%86400)/3600, (dur%3600)/60, dur%60))
			return false
		}
		fmt.Println(fmt.Sprintf("Progressing wonderfully!  A=%d B=%d CH=%d elapsed %dd %dh %dm %ds", 
			actuala, actualb, actualch, dur/86400, (dur%86400)/3600, (dur%3600)/60, dur%60))
	}
	return true
}

func invokeOnOnePeer(peerNum int, numReq int, iArgs []string) {
			var sendFailure int64 = 0
			invArgs0 := []string{"a", "b", "1"}
			k := 1
			for k <= numReq {
				_, err := chaincode.InvokeOnPeer(iArgs, invArgs0)
				if err != nil { sendFailure++ }
	                        time.Sleep(10 * time.Second)
				k++
			}
			if sendFailure != 0 {
				atomic.AddInt64(&failedToSend, sendFailure)
				fmt.Println(fmt.Sprintf("WARNING: on peer %d, failed to send %d / %d invoke requests in current interval", peerNum, sendFailure, numReq))
			}
			atomic.AddInt64(&curra, sendFailure-int64(numReq))
			atomic.AddInt64(&currb, int64(numReq)-sendFailure)
}
