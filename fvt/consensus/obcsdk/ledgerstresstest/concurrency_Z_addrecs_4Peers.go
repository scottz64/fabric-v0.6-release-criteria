package main

/******************** Testing Objective consensu:STATE TRANSFER ********
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
	"math/rand"
        "strconv"
)

var loopCtr, numReq int
var MY_CHAINCODE_NAME string = "concurrency"

func main() {

	fmt.Println("Using an existing docker network")
	_ = chaincode.InitNetwork()
	chaincode.InitChainCodes()
	chaincode.RegisterUsers()

        data := RandomString(1024)

	time.Sleep(30000 * time.Millisecond)

	fmt.Println("\nPOST/Chaincode: Deploying chaincode  addrecs...")
        dAPIArgs0 := []string{MY_CHAINCODE_NAME, "init", "PEER1"}
        depArgs0 := []string{"a", data, "counter", "0"}
        chaincode.DeployOnPeer(dAPIArgs0, depArgs0)

        time.Sleep(240000 * time.Millisecond)
        fmt.Println("\nPOST/Chaincode: Querying a and counter from adddrecs after deploy >>>>>>>>>>> ")
        qAPIArgs0 := []string{MY_CHAINCODE_NAME, "query"} 
        qArgsa := []string{"a"}
        qArgsb := []string{"counter"}
        A, _ := chaincode.Query(qAPIArgs0, qArgsa)
        B, _ := chaincode.Query(qAPIArgs0, qArgsb)
        myStr := fmt.Sprintf("\nA = %s B= %s", A, B)
        fmt.Println(myStr)

        loopCtr = 0
  	numReq = 50
  	defer timeTrack(time.Now(), "concurrency_Z_addrecs_4Peers")
  	now := time.Now().Unix()
  	endTime := now + 1 * 60
        fmt.Println("Start now, End Time: ", now, endTime)
  	for now < endTime {
            fmt.Println("loopCtr, Time Now: ", loopCtr, time.Now())
	    InvokeLoop(numReq, data)
            loopCtr++
            now = time.Now().Unix()
  	}

}

func InvokeLoop(numReq int, data string) {

	var wg sync.WaitGroup
      
        iAPIArgs := []string{"a", data, "counter"}

	wg.Add(4*numReq)

	go func() {

		k := 1

	  invArgs0 := []string{MY_CHAINCODE_NAME, "invoke", "PEER0"}

		for k <= numReq {
		   go func() {
		      chaincode.InvokeOnPeer(invArgs0, iAPIArgs)
		      wg.Done()
	           }()
		   k++
	       }

		fmt.Println("# of Req Invoked on PEER0 ", k)
	}()

	go func() {

		k := 1
	  invArgs1 := []string{MY_CHAINCODE_NAME, "invoke", "PEER1"}
		for k <= numReq {
		   go func() {
			chaincode.InvokeOnPeer(invArgs1, iAPIArgs)
			wg.Done()
	      }()
		   k++
		}
		fmt.Println("# of Req Invoked on PEER1 ", k)
	}()


	go func() {

		k := 1
	        invArgs2 := []string{MY_CHAINCODE_NAME, "invoke", "PEER2"}
		for k <= numReq {
		   go func() {
			chaincode.InvokeOnPeer(invArgs2, iAPIArgs)
			wg.Done()
	           }()
		   k++
		}
		fmt.Println("# of Req Invoked on PEER2 ", k)
	}()

	go func() {

		invArgs3 := []string{MY_CHAINCODE_NAME, "invoke", "PEER3"}
		k := 1
		for k <= numReq {
		    go func() {
			chaincode.InvokeOnPeer(invArgs3, iAPIArgs)
			wg.Done()
	            }()
		    k++
		}
		fmt.Println("# of Req Invoked  on PEER3", k)
	}()

	wg.Wait()
}

func QueryHeight(expectedCtr int) (passed bool) {

	passed = false

	fmt.Println("\nPOST/Chaincode: Querying counter from addrecs chaincode after invoke >>>>>>>>>>> ")
	qAPIArgs00 := []string{MY_CHAINCODE_NAME, "query", "PEER0"}
	qAPIArgs01 := []string{MY_CHAINCODE_NAME, "query", "PEER1"}
	qAPIArgs02 := []string{MY_CHAINCODE_NAME, "query", "PEER2"}
	qAPIArgs03 := []string{MY_CHAINCODE_NAME, "query", "PEER3"}

	qArgsb := []string{"counter"}

	resCtr0, _ := chaincode.QueryOnHost(qAPIArgs00, qArgsb)
	resCtr1, _ := chaincode.QueryOnHost(qAPIArgs01, qArgsb)
	resCtr2, _ := chaincode.QueryOnHost(qAPIArgs02, qArgsb)
	resCtr3, _ := chaincode.QueryOnHost(qAPIArgs03, qArgsb)


	ht0, _ := chaincode.GetChainHeight("PEER0")
	ht1, _ := chaincode.GetChainHeight("PEER1")
	ht2, _ := chaincode.GetChainHeight("PEER2")
	ht3, _ := chaincode.GetChainHeight("PEER3")

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
		passed = true
		fmt.Printf("expected: %d.  ALL PEERS MATCH.\n", expectedCtr)
	} else {
		fmt.Printf("expected: %d\nresCtr0:  %d\nresCtr1:  %d\nresCtr2:  %d\nresCtr3:  %d\n", expectedCtr, resCtrI0, resCtrI1, resCtrI2, resCtrI3)
	}
	return passed
}


func timeTrack(start time.Time, name string) {
	elapsed := time.Since(start)
        expectedValue := loopCtr * numReq * 4
	result := "FAILED"
        QueryHeight(expectedValue)
	time.Sleep(510000 * time.Millisecond)  // 8.5 minutes
        if QueryHeight(expectedValue) { result = "PASSED" }
	fmt.Printf("\nFINAL RESULT %s %s, elapsed %s \n", name, result, elapsed)
}

func RandomString(strlen int) string {
    rand.Seed(time.Now().UTC().UnixNano())
    const chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    result := make([]byte, strlen)
    for i := 0; i < strlen; i++ {
        result[i] = chars[rand.Intn(len(chars))]
    }
    return string(result)
}

