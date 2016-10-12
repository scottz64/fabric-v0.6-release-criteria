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
  	defer timeTrack(time.Now(), "Testcase execution Done")
  	now := time.Now().Unix()
  	endTime := now + 1 * 60
        fmt.Println("Start now, End Time: ", now, endTime)
  	for now < endTime {
            fmt.Println("loopCtr, Time Now: ", loopCtr, time.Now())
	    InvokeLoop(numReq, data)
            loopCtr++
            now = time.Now().Unix()
  	}
  	var numRequestsSent = loopCtr * numReq * 4
  	myStr = fmt.Sprintf("\nnum of requests sent =  %d in 1 min ", numRequestsSent)
  	fmt.Println(myStr)

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

func QueryHeight(expectedCtr int, waitTime int) {

  time.Sleep(300000 * time.Millisecond)
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




	fmt.Println("Results in b vp0 : ", resCtr0)
	fmt.Println("Results in b vp1 : ", resCtr1)
	fmt.Println("Results in b vp2 : ", resCtr2)
	fmt.Println("Results in b vp3 : ", resCtr3)

	ht0, _ := chaincode.GetChainHeight("PEER0")
	ht1, _ := chaincode.GetChainHeight("PEER1")
	ht2, _ := chaincode.GetChainHeight("PEER2")
	ht3, _ := chaincode.GetChainHeight("PEER3")

	fmt.Printf("ht0: %d, ht1: %d, ht2: %d, ht3: %d ", ht0, ht1, ht2, ht3)
}


func timeTrack(start time.Time, name string) {
	elapsed := time.Since(start)
        expectedValue := loopCtr * numReq * 4
        QueryHeight(expectedValue, 300)
	fmt.Printf("\n################# %s took %s \n", name, elapsed)
	fmt.Println("################# Execution Completed #################")
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

