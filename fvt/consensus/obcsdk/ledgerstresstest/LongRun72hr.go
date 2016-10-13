package main

/******************** Testing Objective consensu: Sending Invoke Requests in Parallel ********
*   Setup: 4 node local docker peer network with security and consensus mode using pbft
*   0. Deploy chaincode_example02 with 100000000, 0 as initial args
*   1. Send Invoke Requests in parallel on all peers using go routines, and
*   2. query every so often to confirm results match on all peers.
*   3. After specified time (72 hrs), query all peers again to get final result.
*********************************************************************/

import (
	"fmt"
	"strconv"
	"time"
        "sync"
        "../threadutil"
	"../chaincode"
	"../peernetwork"
)

var curra, currb, numPeers, numReq int
var MY_CHAINCODE_NAME string =  "example02"

func main() {

	defer timeTrack(time.Now(), "Testcase execution Done")
	// 1 min	    60	unit = seconds
	// 1 hr		  3600
	// 12 hr	 43200
	// 1 day	 86400
	// 2 day	172800
	// 3 day	259200 (72 hr)

	var loopSecs int64 = 60

	var myNetwork peernetwork.PeerNetwork

	fmt.Println("Creating a local docker network")
	//peernetwork.SetupLocalNetwork(4, true)

	//with the InvokeLoop designed with this 8 peer 4 req setup we would have 144 requests in one round
	numPeers = 4
	numReq = 250

	myNetwork = chaincode.InitNetwork()
	chaincode.InitChainCodes()
	chaincode.RegisterUsers()

	//get a URL details to get info n chainstats/transactions/blocks etc.
	aPeer, _ := peernetwork.APeer(myNetwork)
	url := "http://" + aPeer.PeerDetails["ip"] + ":" + aPeer.PeerDetails["port"]

	fmt.Println("Peers on network ")
	chaincode.NetworkPeers(url)

	fmt.Println("\nPOST/Chaincode: Deploying chaincode at the beginning ....")

	//var inita, initb int
	//inita = 100000000
	//initb = 0

	dAPIArgs0 := []string{"example02", "init"}
	depArgs0 := []string{"a", "100000000", "b", "0"}
	chaincode.Deploy(dAPIArgs0, depArgs0)

	time.Sleep(60000 * time.Millisecond)
	fmt.Println("\nPOST/Chaincode: Querying a and b after deploy >>>>>>>>>>> ")

	qAPIArgs0 := []string{"example02", "query"}
	qArgsa := []string{"a"}
	qArgsb := []string{"b"}
	A, _ := chaincode.Query(qAPIArgs0, qArgsa)
	B, _ := chaincode.Query(qAPIArgs0, qArgsb)
	curra, _ = strconv.Atoi(A)
	currb, _ = strconv.Atoi(B)
	myStr := fmt.Sprintf("\nStarting Values: A = %s B= %s", A, B)
	fmt.Println(myStr)

	InvokeLoop(numPeers, numReq, loopSecs)
}

func InvokeLoop(numPeers int, numReq int, numSecs int64) {

	var wg sync.WaitGroup

	start := time.Now().Unix()
	endTime := start + numSecs
	fmt.Println("Start , End Time: ", start, endTime)
	for start < endTime {
        	wg.Add(4)
		j := 0
		for j < numPeers {
			//currPeer := "PEER" + strconv.Itoa(j)
                        currPeer := threadutil.GetPeer(j) 
			iAPIArgsCurrPeer := []string{"example02", "invoke", currPeer}
			go func() {
				invokeOnOnePeer(j, numReq, iAPIArgsCurrPeer)
				wg.Done()
			}()
			j++
		}
		wg.Wait()
		QueryValAndHeight(currb)
		start = time.Now().Unix()
	}
}

func invokeOnOnePeer(j int, numReq int, iArgs []string) {
			invArgs0 := []string{"a", "b", "1"}
			k := 1
			for k <= numReq {
				chaincode.InvokeOnPeer(iArgs, invArgs0)
				k++
			}
			curra = curra - numReq
			currb = currb + numReq

/*
			m := j - 1
			for m >= 0 {
				//loopPeer := "PEER" + strconv.Itoa(m)
				loopPeer := threadutil.GetPeer(m)
				iAPIArgsLoopPeer := []string{"example02", "invoke", loopPeer}
				k = 1
				for k <= numReq {
					chaincode.InvokeOnPeer(iAPIArgsLoopPeer, invArgs0)
					k++
				}
				m = m - 1
			}
*/
}


func QueryValAndHeight(expectedCtr int) (passed bool, cntr int) {

        passed = false

        fmt.Println("\nPOST/Chaincode: Querying counter from chaincode ", MY_CHAINCODE_NAME)
        qAPIArgs00 := []string{MY_CHAINCODE_NAME, "query", threadutil.GetPeer(0)}
        qAPIArgs01 := []string{MY_CHAINCODE_NAME, "query", threadutil.GetPeer(1)}
        qAPIArgs02 := []string{MY_CHAINCODE_NAME, "query", threadutil.GetPeer(2)}
        qAPIArgs03 := []string{MY_CHAINCODE_NAME, "query", threadutil.GetPeer(3)}

        qArgsb := []string{"b"}

        resCtr0, _ := chaincode.QueryOnHost(qAPIArgs00, qArgsb)
        resCtr1, _ := chaincode.QueryOnHost(qAPIArgs01, qArgsb)
        resCtr2, _ := chaincode.QueryOnHost(qAPIArgs02, qArgsb)
        resCtr3, _ := chaincode.QueryOnHost(qAPIArgs03, qArgsb)


        ht0, _ := chaincode.GetChainHeight( threadutil.GetPeer(0))
        ht1, _ := chaincode.GetChainHeight( threadutil.GetPeer(0))
        ht2, _ := chaincode.GetChainHeight( threadutil.GetPeer(2))
        ht3, _ := chaincode.GetChainHeight( threadutil.GetPeer(3))

        fmt.Println("Ht in  PEER0 : ", ht0)
        fmt.Println("Ht in  PEER1 : ", ht1)
        fmt.Println("Ht in  PEER2 : ", ht2)
        fmt.Println("Ht in  PEER3 : ", ht3)

        resCtrI0, _ := strconv.Atoi(resCtr0)
        resCtrI1, _ := strconv.Atoi(resCtr1)
        resCtrI2, _ := strconv.Atoi(resCtr2)
        resCtrI3, _ := strconv.Atoi(resCtr3)

        matches := 0
        if resCtrI0 == expectedCtr { matches++ }
        if resCtrI1 == expectedCtr { matches++ }
        if resCtrI2 == expectedCtr { matches++ }
        if resCtrI3 == expectedCtr { matches++ }
        if matches == 4 {
                if ht0 == ht1 && ht0 == ht2 && ht0 == ht3 {
                        passed = true
                        fmt.Printf("ALL PEERS MATCH expected %d, ht=%d\n", expectedCtr, ht0)
                } else {
                        fmt.Printf("ALL PEERS counters match expected %d, BUT HEIGHTS DO NOT ALL MATCH: ht0=%d ht1=%d ht2=%d ht3=%d\n", expectedCtr, ht0, ht1, ht2, ht3)
                }
        } else {
                fmt.Printf("expected: %d\nresCtr0:  %d\nresCtr1:  %d\nresCtr2:  %d\nresCtr3:  %d\n", expectedCtr, resCtrI0, resCtrI1, resCtrI2, resCtrI3)
        }
        return passed, resCtrI0
}


func timeTrack(start time.Time, name string) {
        elapsed := time.Since(start)
        expectedValue := currb 
        result := "FAILED"
        passed, curr := QueryValAndHeight(expectedValue)
        prev := curr-1
        for !passed && curr != prev {
                fmt.Println("sleep 1 minute to allow network to process queued transactions, and try again")
                time.Sleep(60 * time.Second)
                prev = curr
                passed, curr = QueryValAndHeight(expectedValue)
        }
        if passed { result = "PASSED" }
        fmt.Printf("\nFINAL RESULT %s %s, elapsed %s \n", name, result, elapsed)
}

