package main

import (
	"fmt"
	"strconv"
	"time"
	"obcsdk/chaincode"
	"obcsdk/peernetwork"
	"obcsdk/lstutil"
)

var peerNetworkSetup peernetwork.PeerNetwork
var AVal, BVal, curAVal, curBVal, invokeValue int64
var argA = []string{"a"}
var argB = []string{"counter"}

var data string
var counter int64
const(
	TOTAL_NODES = 1
)
var url string

func setupNetwork() {
	fmt.Println("Creating a local docker network")
  //peernetwork.SetupLocalNetwork(TOTAL_NODES, true)
	peernetwork.GetNC_Local()
	//peernetwork.PrintNetworkDetails()
	peerNetworkSetup = chaincode.InitNetwork()
	chaincode.InitChainCodes()
	chaincode.RegisterUsers()
}

func sleep(secs int64) {
	time.Sleep(time.Second * time.Duration(secs))
}

func deployChaincode (done chan bool){
	var funcArgs = []string{lstutil.CHAINCODE_NAME, "init"}
	var args = []string{argA[0], data, argB[0], "0"}

	chaincode.Deploy(funcArgs, args)
	sleep(35)
	done <- true
}

func invokeChaincode (){
	counter ++;
	arg1Construct := []string{lstutil.CHAINCODE_NAME, "invoke"}
	arg2Construct := []string{"a"+strconv.FormatInt(counter, 10), data, "counter", }

	_, _ = chaincode.Invoke(arg1Construct, arg2Construct)
}

func queryChaincode () (res1, res2 string){
	var qargA = []string{"a"+strconv.FormatInt(counter, 10)}
	qAPIArgs0 := []string{lstutil.CHAINCODE_NAME, "query"}
	A, _ := chaincode.Query(qAPIArgs0, qargA)
	Counter, _ := chaincode.Query(qAPIArgs0, []string{"counter"})
	return A,Counter
}

func main() {
	done := make(chan bool, 1)
	counter = 0;
	data = "Yh1WWZlw1gGd2qyMNaHqBCt4zuBrnT4cvZ5iMXRRM3YBMXLZmmvyVr0ybWfiX4N3UMliEVA0d1dfTxvKs0EnHAKQe4zcoGVLzMHd8jPQlR5ww3wHeSUGOutios16lxfuQTdnsFcxhXLiGwp83ahyBomdmJ3igAYTyYw2bwXqhBeL9fa6CTK43M2QjgFhQtlcpsh7XMcUWnjJhvMHAyH67Z8Ugke6U8GQMO5aF1Oph0B2HlIQUaHMq2i6wKN8ZXyx7CCPr7lKnIVWk4zn0MLZ16LstNErrmsGeo188Rdx5Yyw04TE2OSPSsaQSDO6KrDlHYnT2DahsrY3rt3WLfBZBrUGhr9orpigPxhKq1zzXdhwKEzZ0mi6tdPqSzMKna7O9STstf2aFdrnsoovOm8SwDoOiyqfT5fc0ifVZSytVNeKE1C1eHn8FztytU2itAl1yDYSfTZQv42tnVgDjWcLe2JR1FpfexVlcB8RUhSiyoThSIFHDBZg8xyULPmp4e6acOfKfW2BXh1IDtGR87nBWqmytTOZrPoXRPq2QXiUjZS2HflHJzB0giDbWEeoZoMeF11364Xzmo0iWsBw0TQ2cHapS4cR49IoEDWkC6AJgRaNb79s6vythxX9CqfMKxIpqYAbm3UAZRS7QU7MiZu2qG3xBIEegpTrkVNneprtlgh3uTSVZ2n2JTWgexMcpPsk0ILh10157SooK2P8F5RcOVrjfFoTGF3QJTC2jhuobG3PIXs5yBHdELe5yXSEUqUm2ioOGznORmVBkkaY4lP025SG1GNPnydEV9GdnMCPbrgg91UebkiZsBMM21TZFbUqP70FDAzMWZKHDkDKCPoO7b8EPXrz3qkyaIWBymSlLt6FNPcT3NkkTfg7wl4DZYDvXA2EYu0riJvaWon12KWt9aOoXig7Jh4wiaE1BgB3j5gsqKmUZTuU9op5IXSk92EIqB2zSM9XRp9W2I0yLX1KWGVkkv2OIsdTlDKIWQS9q1W8OFKuFKxbAEaQwhc7Q5Mm"
	// Setup the network based on the NetworkCredentials.json provided
	setupNetwork()
  //Deploy chaincode
  deployChaincode (done)

	// time to messure overall execution of the testcase
	defer timeTrack(time.Now(), "execution for LedgerStressOneCliOnePeer.go ")
        InvokeLoop()
}

//Invokes loop
func InvokeLoop() {
	curTime := time.Now();
	for i := 1;i<=20000;i++{
		if (i % 1000 == 0) {
			elapsed := time.Since(curTime)
			fmt.Println ("============== > Iteration#", counter," Time: ",elapsed);
			curTime = time.Now();
		}
		invokeChaincode();
	}
}
func getChainHeight()int{
	var urlStr string
	//Hardcoded since this is a single peer
	urlStr = "http://172.17.0.3:5000"
	height := chaincode.Monitor_ChainHeight(urlStr)
	fmt.Println("################ Chaincode Height on "+urlStr+" is : ", height)
	return height
}

func timeTrack(start time.Time, name string) {
	elapsed := time.Since(start)
	errTransactions := 0
        sleep(20)
	val1,val2 := queryChaincode ()
	fmt.Printf("\n########### After Query Vals A = %s \nB = %s", val1,val2)
	fmt.Printf("\n\n################# %s took %s \n\n", name, elapsed)

	height := getChainHeight()
	fmt.Println("############### Total Blocks #", height)
	for i:=1;i<height;i++{
		//fmt.Printf("\n============================== Current BLOCKS %d ==========================\n", i)
		nonHashData := chaincode.ChaincodeBlockTrxInfo("http://172.17.0.3:5000", i)
		length := len(nonHashData.TransactionResult)
		for j := 0;j<length;j++ {
			// Print Error info only when transatcion failed
			if (nonHashData.TransactionResult[j].ErrorCode > 0) {
				fmt.Printf("\n=============Block[%d] Trx#[%s] UUID [%d] ErrorCode [%d] Error: %s\n",i, counter, nonHashData.TransactionResult[j].Uuid, nonHashData.TransactionResult[j].ErrorCode, nonHashData.TransactionResult[j].Error)
				errTransactions++
			}
		}
	}

}
