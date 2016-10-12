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
	"../chaincode"
	"../peernetwork"
)

var curra, currb int

func main() {

	defer timeTrack(time.Now(), "Testcase execution Done")
	// 1 min	    60	unit = seconds
	// 1 hr		  3600
	// 12 hr	 43200
	// 1 day	 86400
	// 2 day	172800
	// 3 day	259200 (72 hr)

	var loopSecs int64 = 259200

	var myNetwork peernetwork.PeerNetwork

	fmt.Println("Creating a local docker network")
	//peernetwork.SetupLocalNetwork(4, true)

	//with the InvokeLoop designed with this 8 peer 4 req setup we would have 144 requests in one round
	numPeers := 4
	numReq := 2500

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
			currPeer := "PEER" + strconv.Itoa(j)
			iAPIArgsCurrPeer := []string{"example02", "invoke", currPeer}
			go func() {
				invokeOnOnePeer(j, numReq, iAPIArgsCurrPeer)
				wg.Done()
			}()
			j++
		}
		wg.Wait()
		QueryMatch(curra, currb)
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
				loopPeer := "PEER" + strconv.Itoa(m)
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

func QueryMatch(curra int, currb int) (passed bool) {

	passed = false
	//fmt.Println("Inside Query match ********************************* &&&&&&&&&&&&&& %%%%%%%%%%%%%%%%")
	//fmt.Println("Sleeping for 20 seconds ")
	//time.Sleep(20000 * time.Millisecond)

	//fmt.Println("\nPOST/Chaincode: Querying a and b after invoke >>>>>>>>>>> ")
	qAPIArgs00 := []string{"example02", "query", "PEER0"}
	qAPIArgs01 := []string{"example02", "query", "PEER1"}
	qAPIArgs02 := []string{"example02", "query", "PEER2"}
	qAPIArgs03 := []string{"example02", "query", "PEER3"}

	qArgsa := []string{"a"}
	qArgsb := []string{"b"}

	res0A, _ := chaincode.QueryOnHost(qAPIArgs00, qArgsa)
	res0B, _ := chaincode.QueryOnHost(qAPIArgs00, qArgsb)

	res0AI, _ := strconv.Atoi(res0A)
	res0BI, _ := strconv.Atoi(res0B)

	res1A, _ := chaincode.QueryOnHost(qAPIArgs01, qArgsa)
	res1B, _ := chaincode.QueryOnHost(qAPIArgs01, qArgsb)

	res1AI, _ := strconv.Atoi(res1A)
	res1BI, _ := strconv.Atoi(res1B)

	res2A, _ := chaincode.QueryOnHost(qAPIArgs02, qArgsa)
	res2B, _ := chaincode.QueryOnHost(qAPIArgs02, qArgsb)

	res2AI, _ := strconv.Atoi(res2A)
	res2BI, _ := strconv.Atoi(res2B)

	res3A, _ := chaincode.QueryOnHost(qAPIArgs03, qArgsa)
	res3B, _ := chaincode.QueryOnHost(qAPIArgs03, qArgsb)

	res3AI, _ := strconv.Atoi(res3A)
	res3BI, _ := strconv.Atoi(res3B)

 /*
	valueStr0 := fmt.Sprintf(" PEER0 resa : %d , resb : %d", res0AI, res0BI)
	valueStr1 := fmt.Sprintf(" PEER1 resa : %d , resb : %d", res1AI, res1BI)
	valueStr2 := fmt.Sprintf(" PEER2 resa : %d , resb : %d", res2AI, res2BI)
	valueStr3 := fmt.Sprintf(" PEER3 resa : %d , resb : %d", res3AI, res3BI)
	fmt.Println(valueStr0)
	fmt.Println(valueStr1)
	fmt.Println(valueStr2)
	fmt.Println(valueStr3)
 */

	matches := 0
	if (curra == res0AI) && (currb == res0BI) {
		matches++
		//fmt.Println("Results in a and b match with Invoke values on PEER0: PASS")
		//valueStr := fmt.Sprintf(" curra : %d, currb : %d, resa : %d , resb : %d", curra, currb, res0AI, res0BI)
		//fmt.Println(valueStr)
	} else {
                fmt.Println("Results in a and b DO NOT match on PEER0 a, b: ", res0AI, res0BI)
	}

	if (curra == res1AI) && (currb == res1BI) {
		matches++
		//fmt.Println("Results in a and b match with Invoke values on PEER1: PASS")
		//valueStr := fmt.Sprintf(" curra : %d, currb : %d, resa : %d , resb : %d", curra, currb, res1AI, res1BI)
		//fmt.Println(valueStr)
	} else {
                fmt.Println("Results in a and b DO NOT match on PEER1 a, b: ", res1AI, res1BI)
	}


	if (curra == res2AI) && (currb == res2BI) {
		matches++
                //fmt.Println("Results in a and b match with Invoke values on PEER2: PASS")
                //valueStr := fmt.Sprintf(" curra : %d, currb : %d, resa : %d , resb : %d", curra, currb, res2AI, res2BI)
                //fmt.Println(valueStr)
        } else {
                fmt.Println("Results in a and b DO NOT match on PEER2 a, b: ", res2AI, res2BI)
        }


	if (curra == res3AI) && (currb == res3BI) {
		matches++
                //fmt.Println("Results in a and b match with Invoke values on PEER3: PASS")
                //valueStr := fmt.Sprintf(" curra : %d, currb : %d, resa : %d , resb : %d", curra, currb, res3AI, res3BI)
                //fmt.Println(valueStr)
        } else {
                fmt.Println("Results in a and b DO NOT match on PEER3 a, b: ", res3AI, res3BI)
	}

	if matches == 4 {
		passed = true
		fmt.Println(fmt.Sprintf ("All PEERs MATCH curra: %d , currb: %d", curra, currb))
	} else {
		fmt.Println(fmt.Sprintf ("curra: %d, currb: %d, matches=%d", curra, currb, matches))
	}
	return passed
}

func timeTrack(start time.Time, name string) {

	//fmt.Println("Sleeping for 60 seconds ")
	//time.Sleep(60000 * time.Millisecond)
	result := "FAILED"
	if QueryMatch(curra, currb) { result = "PASSED" }
	elapsed := time.Since(start)
	myStr := fmt.Sprintf("\nFINAL RESULT %s %s , elapsed %s\n", name, result, elapsed)
	fmt.Println(myStr)
}
