
#-----------------------------------------------------------------------
# TEST OBJECTIVE : basic network setup, deploy, invoke and query on all
#    peers (default using REST interface) using chaincode addrecs,
#    and exercise and validate all chaincode APIs
# SETUP STEPS:
#   1. Set environment variables:
#      export TEST_NETWORK=""    or    export TEST_NETWORK=LOCAL
# TEST DETAILS (Optional):
#   1. Setup local docker network with security with 4 peer nodes
#   2. Deploy chaincode addrecs from
#      ../ledgerstresstest/example02_addRecordsToLedger/
#-----------------------------------------------------------------------

/* -----------------------------------------------------------------------------------------------------------------------------
    TEST coverage for Basic Functionality: Block, Blockchain, Chaincode, Network, Registrar, and Transactions

	Block           /chain/blocks/<block>   (get block chain stats data)
     x  chaincode.BlockStats                    calls peerrest.GetChainInfo(url + "/chain/blocks/" + strconv.Itoa(block))
        chaincode.ChaincodeBlockHash            calls peerrest.GetChainInfo(url + "/chain/blocks/" + strconv.Itoa(block))
        chaincode.ChaincodeBlockTrxInfo         calls peerrest.GetChainInfo(url + "/chain/blocks/" + strconv.Itoa(block))
        chaincode.GetBlockTrxInfoByHost calls prev func

	Blockchain      /chain                  (get block chain height)
     x  chaincode.GetChainStats                 calls peerrest.GetChainInfo(url + "/chain")
        chaincode.ChainStats                    calls peerrest.GetChainInfo(url + "/chain")
     x  chaincode.Monitor_ChainHeight           calls peerrest.GetChainInfo(url + "/chain")
     x  chaincode.GetChainHeight calls prev func

	Chaincode       /chaincode              (for all deploy, invoke, query commands)
     x  chaincode.changeState                   calls peerrest.PostChainAPI with  url + "/chaincode"

	Network         /network/peers
     x  chaincode.NetworkPeers                  calls peerrest.GetChainInfo(url + "/network/peers")

	Registrar       /registrar
	Registrar       /registrar/id
	Registrar       /registrar/id/ecert
	Registrar       /registrar/id/tcert
     x  chaincode.RegisterUsers                 calls chaincode.register calls peerrest.GetChainInfo(url + "/registrar"
     x  chaincode.UserRegister_Status           calls peerrest.GetChainInfo(url + "/registrar/" + username)
     x  chaincode.UserRegister_ecertDetail      calls peerrest.GetChainInfo(url + "/registrar/" + username + "/ecert")
                                                /tcert : no test exists yet

	Transactions    /transactions/<uuid>
     x  chaincode.Transaction_Detail            calls peerrest.GetChainInfo(url + "/transactions/" + txid)
        chaincode.GetChainTransactions          calls peerrest.GetChainInfo(url + "/transactions/" + txid)

   -----------------------------------------------------------------------------------------------------------------------------
 */



package main

import (
	"fmt"
	"../chaincode"
	"../peernetwork"
	"os"
	"bufio"
	//"strconv"
	"strings"
	"time"
	"../lstutil"
	"../chco2"
)

var f *os.File
var url string
var counter int64
var subTestsFailures int


func main() {
	subTestsFailures = 0
	lstutil.TESTNAME = "BasicFuncExistingNetworkLST"
	lstutil.InitLogger(lstutil.TESTNAME)

	var openFileErr error
        lstutil.SummaryFile, openFileErr = os.OpenFile(lstutil.OutputSummaryFileName, os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
        if openFileErr != nil {
                lstutil.Logger(fmt.Sprintf("error opening OutputSummaryFileName=<%s> openFileErr: %s", lstutil.OutputSummaryFileName, openFileErr))
                panic(fmt.Sprintf("error opening OutputSummaryFileName=<%s> openFileErr: %s", lstutil.OutputSummaryFileName, openFileErr))
        }
        defer lstutil.SummaryFile.Close()
        lstutil.Writer = bufio.NewWriter(lstutil.SummaryFile)

        fmt.Fprintln(lstutil.Writer, fmt.Sprintf("START %s =========", lstutil.TESTNAME))
        lstutil.Writer.Flush()
	lstutil.Logger("\nSTART " + lstutil.TESTNAME + " =========")

	defer lstutil.TimeTracker(time.Now())

	setupNetwork()  // establish chco2.MyNetwork, using networkcredentials

	lstutil.Logger("\n===== /registrar Registrar Test =====")
	lstutil.Logger("FirstUser=" + peernetwork.FirstUser)
	user_ip, user_port, user_name, err := peernetwork.PeerOfThisUser(chco2.MyNetwork, peernetwork.FirstUser)
	check(err)
	url = chaincode.GetURL(user_ip, user_port)
	userRegisterTest(url, user_name)

	lstutil.Logger("\n===== /network/peers Network Test =====")
	response, status := chaincode.NetworkPeers(url)
	myStr := "NetworkPeers Rest API TEST "
	if strings.Contains(status, "200") {
		myStr += "PASS. Successful "
	} else {
		subTestsFailures++
		myStr += "FAIL!!! Error "
	}
	myStr += fmt.Sprintf("NetworkPeers response body:\n%s\n", response)
	lstutil.Logger(myStr)

	lstutil.Logger("\n===== /chain Blockchain Test =====")
	response, status = chaincode.GetChainStats(url)
        if strings.Contains(status, "200") {
                lstutil.Logger("ChainStats Rest API TEST PASS.")
        } else {
                subTestsFailures++
                lstutil.Logger("ChainStats Rest API TEST FAIL!!!")
        }
	lstutil.Logger(fmt.Sprintf("  ChainStats response status: %s\n  ChainStats response body: %s\n", status, response))

	lstutil.Logger("\n===== /chaincode Deploy Test =====")
	counter = lstutil.DeployChaincode(chco2.MyNetwork)  // includes sleep 60 secs for Local network or 120 secs for External network
	lstutil.Logger(fmt.Sprintf("-----Deploy Test returned counter: %d", counter))

	queryCounterSuccess := lstutil.QueryAllHostsToGetCurrentCounter(chco2.MyNetwork, lstutil.TESTNAME, &counter)
	if !queryCounterSuccess {
		subTestsFailures++
		lstutil.Logger(fmt.Sprintf("BasicFuncExistingNetworkLST: WARNING: CANNOT find consensus in network for actual values; counter value will likely fail to match expected value"))
		// panic(errors.New("BasicFuncExistingNetworkLST: CANNOT find consensus in existing network"))
	}
	lstutil.Logger(fmt.Sprintf("-----BasicFuncExistingNetworkLST, AFTER deploy,QueryAllHosts retrieved counter value (and this is now the expected value): %d", counter))

        height := chaincode.Monitor_ChainHeight(url) // save the height, to be used below for validation in getHeight()

	queryDeploySuccess := lstutil.QueryAllHosts(chco2.MyNetwork, "DEPLOY", counter)
	if !queryDeploySuccess { subTestsFailures++ }

	lstutil.Logger("\n===== /chaincode Invoke Test =====")
	invRes := lstutil.InvokeChaincode(chco2.MyNetwork, &counter)  // increments counter inside
	height++
	time.Sleep(time.Duration(10 + chco2.NumberOfPeersInNetwork) * time.Second)
	queryInvokeSuccess := lstutil.QueryAllHosts(chco2.MyNetwork, "INVOKE", counter)
	if !queryInvokeSuccess { subTestsFailures++ }

	lstutil.Logger("\n===== /chain Blockchain Test =====")
	getHeight(chco2.MyNetwork, height)  // this validates height on all peers all match the expected height

	lstutil.Logger("\n===== /chain/blocks Block Test =====")
	blockNum := height - 1
	chaincode.BlockStats(url, blockNum)

	if len(chco2.MyNetwork.Peers) < 1 { panic("No peers in network; cannot run this test") }
	peername := chco2.MyNetwork.Peers[0].PeerDetails["name"]
	txList, _ := chaincode.GetBlockTrxInfoByHost(peername, blockNum)
	myStr = "\nGetBlocks API TEST "
	//if strings.Contains(txList.TransactionResult[0].Uuid, invRes) { 	// v0.5
	if txList != nil && strings.Contains(txList[0].Txid, invRes) {  // these should be equal, if the invoke transaction was successful
		myStr += fmt.Sprintf("PASS: Transaction Successfully stored in Block")
		myStr += fmt.Sprintf("\nCH_Block = %d, txid = %s, InvokeTransactionResult = %s\n", blockNum, txList[0].Txid, invRes)
		lstutil.Logger(myStr)
	} else {
		subTestsFailures++
		myStr += fmt.Sprintf("FAIL!!! Transaction NOT stored in Block")
		myStr += fmt.Sprintf("\nCH_Block = %d, txid = %s, InvokeTransactionResult = %s\n", blockNum, txList[0].Txid, invRes)
		lstutil.Logger(myStr)
		getBlockTxInfo(chco2.MyNetwork,0)
	}

	lstutil.Logger("\n===== /transactions Transactions Test =====")
	lstutil.Logger("  input url:  " + url)
	lstutil.Logger("  input invRes:  " + invRes)
	lstutil.Logger("  calling Transaction_Detail(url,invRes):  ")
	chaincode.Transaction_Detail(url, invRes)

	if subTestsFailures == 0 {
		myStr = "PASSED"
	} else {
        	myStr = fmt.Sprintf("FAILED (failed %d sub-tests)", subTestsFailures)
	}
	lstutil.FinalResultStr = fmt.Sprintf("FINAL RESULT %s %s", myStr, lstutil.TESTNAME)
	//FinalResultStr will be printed by TimeTracker along with the elapsed time
}

func setupNetwork() {

        lstutil.Logger("========= setupNetwork =========")

	// lstutil.Logger("Setup a new network of peers (after killing old ones) using local_fabric script")
	// peernetwork.SetupLocalNetwork(4, false)

	// When running BasicFunc test on local network, the local_fabric shell script creates
	// networkcredentials file. When running this with existing network, create it yourself by
	// putting the service_credentials from the Z network into serv_creds_file and executing
	//	"./update_z.py -b -f <serv_creds_file>"
	// to put the networkcredentials file in automation/ folder.
	// Note: you can skip calling GetNC_Local here if you first ensure the networkcredentials
	// file has already been copied to ../util/NetworkCredentials.json

	lstutil.Logger("----- Get existing Network Credentials ----- ")
        peernetwork.GetNC_Local()  // cp ../automation/networkcredentials ../util/NetworkCredentials.json

	lstutil.Logger("----- Connect to existing network - InitNetwork -----")
        chco2.MyNetwork = chaincode.InitNetwork()

	// override if the user set env var to indicate whether or not the network is LOCAL
	localNetworkType := strings.TrimSpace(strings.ToUpper(os.Getenv("TEST_NETWORK")))
	if localNetworkType != "" {
		chco2.LocalNetworkType = localNetworkType
		if localNetworkType == "LOCAL" {
			chco2.MyNetwork.IsLocal = true
			chaincode.SetNetworkLocality(chco2.MyNetwork,true)	// chco2 network copy
			chaincode.SetNetworkIsLocal(true)			// chaincode network copy
		} else {
			chco2.MyNetwork.IsLocal = false
			chaincode.SetNetworkLocality(chco2.MyNetwork,false)	// chco2 network copy
			chaincode.SetNetworkIsLocal(false)			// chaincode network copy
		}
	}

        lstutil.Logger("----- InitChainCodes -----")
        chaincode.InitChainCodes()
	time.Sleep(50 * time.Second)

        lstutil.Logger("----- RegisterUsers -----")
        if !chaincode.RegisterUsers() {
		lstutil.Logger("\nERROR: FAILED TO REGISTER one or more users in NetworkCredentials.json file\n")
		subTestsFailures++
        }

        //lstutil.Logger("----- RegisterCustomUsers -----")
        //if !chaincode.RegisterCustomUsers() {
	//	lstutil.Logger("\nERROR: FAILED TO REGISTER one or more CUSTOM users\n")
	//	subTestsFailures++
        //}
		

	time.Sleep(10 * time.Second)
	//peernetwork.PrintNetworkDetails(chco2.MyNetwork)
	peernetwork.PrintNetworkDetails()
	numPeers := peernetwork.GetNumberOfPeers(chco2.MyNetwork)

	if subTestsFailures == 0 {
		lstutil.Logger(fmt.Sprintf("Successfully connected to network with %d peers with pbft and security+privacy enabled\n", numPeers))
	}
}

// arg = a username that was already registered; this func confirms if it was successful
// and confirms user "ghostuserdoesnotexist" is not registered
// and confirms 
func userRegisterTest(url string, username string) {

	lstutil.Logger("\n----- /registrar Test -----")
	response, status := chaincode.UserRegister_Status(url, username)
	myStr := "RegisterUser API TEST "
	if strings.Contains(status, "200") && strings.Contains(response, username + " is already logged in") {
		myStr += fmt.Sprintf ("PASS: %s User Registration was already done successfully", username)
	} else {
		subTestsFailures++
		myStr += fmt.Sprintf ("FAIL!!! %s User Registration was NOT already done\n status = %s\n response = %s", username, status, response)
	}
	lstutil.Logger(myStr)
	time.Sleep(2 * time.Second)

	lstutil.Logger("\n----- RegisterUser Negative Test -----")
	response, status = chaincode.UserRegister_Status(url, "ghostuserdoesnotexist")
	if (strings.Contains(status, "200")) {
		subTestsFailures++
		lstutil.Logger(fmt.Sprintf("RegisterUser API Negative TEST FAIL!!! User <ghostuserdoesnotexist> was found in Registrar User List but it was never registered!\n status = %s\n response = %s\n", status, response))
	} else {
		if strings.Contains(status, "401") { // Unauthorized
			// Did not find the specified username, and no error occurred while trying;
			// this is a good expected result for our test.
			lstutil.Logger("RegisterUser API Negative TEST PASS: CONFIRMED that user <ghostuserdoesnotexist> is unregistered as expected")
		} else {
			// Did not find the specified username, and we encountered some other error while trying
			lstutil.Logger(fmt.Sprintf("RegisterUser API Negative TEST FAIL!!! ERROR while searching for non-existant user!\n status = %s\n response = %s\n", status, response))
		}
	}
	time.Sleep(2 * time.Second)

 /*
	lstutil.Logger("\n----- UserRegister_ecert Test -----")
	ecertUser := "lukas"
	response, status = chaincode.UserRegister_ecertDetail(url, ecertUser)
	myEcertStr := "\nUserRegister_ecert TEST "
	if strings.Contains(status, "200") && strings.Contains(response, ecertUser + " is already logged in") {
		myEcertStr += fmt.Sprintf ("PASS: %s ecert User Registration was already done successfully", ecertUser)
	} else {
		subTestsFailures++
		myEcertStr += fmt.Sprintf ("FAIL!!! %s ecert User Registration was NOT already done\n status = %s\n response = %s\n", username, status, response)
	}
	lstutil.Logger(myEcertStr)
	time.Sleep(2 * time.Second)
 */

	lstutil.Logger("\n----- UserRegister_ecert Negative Test -----")
	response, status = chaincode.UserRegister_ecertDetail(url, "ghostuserdoesnotexist")
	if ((strings.Contains(status, "200")) == false) {
		lstutil.Logger("UserRegister_ecert API Negative TEST PASS: CONFIRMED that user <ghostuserdoesnotexist> is unregistered as expected")
	} else {
		subTestsFailures++
		lstutil.Logger(fmt.Sprintf("UserRegister_ecert API Negative TEST FAIL!!! User <ghostuserdoesnotexist> was found in Registrar User List but it was never registered!\n status = %s\n response = %s\n", status, response))
	}
	time.Sleep(5 * time.Second)
}

func getHeight(mynetwork peernetwork.PeerNetwork, expectedToMatch int) {
        htVal, _ := chaincode.GetChainHeight(mynetwork.Peers[0].PeerDetails["name"])
	matches := 1
	numPeers := len(mynetwork.Peers)
	p := 0
	for p = 1 ; p < numPeers ; p++ {
        	ht, _ := chaincode.GetChainHeight(mynetwork.Peers[p].PeerDetails["name"])
		if ht == htVal && htVal != 0 {
			matches++ 
		} else {
			if htVal == 0 { htVal = ht }  // skip all nodes with invalid (zero) values until find one
		}
	}

	allMatchEachOther := false
	if p == matches { allMatchEachOther = true }

	consensusReached := false
	numRequired := numPeers - ((numPeers-1) / 3)
        if matches >= numRequired { consensusReached = true }

	consensusValueMatchesExpected := false
	if htVal == expectedToMatch { consensusValueMatchesExpected = true }

	myStr := fmt.Sprintf("CHAIN HEIGHT TEST ")
        if consensusValueMatchesExpected && consensusReached {
		if allMatchEachOther {
                	myStr += fmt.Sprintf("PASS : value %d matches expected value on all Peers\n", htVal)
        	} else {
                	myStr += fmt.Sprintf("PASS : value %d matches expected value on %d Peers (%d are required for consensus in this Network of %d Peers)\n", htVal, matches, numRequired, numPeers)
		}
        } else {
                subTestsFailures++
                myStr += fmt.Sprintf("FAIL : ")
		if !consensusReached {
                	myStr += fmt.Sprintf("Cannot reach consensus - only %d peers can agree. ", matches)
		}
		if !consensusValueMatchesExpected {
                	myStr += fmt.Sprintf("Value %d DOES NOT MATCH expected %d. ", htVal, expectedToMatch)
		}
        }
	lstutil.Logger(myStr)
}

// pass in 0 to get ALL blocks
func getBlockTxInfo(mynetwork peernetwork.PeerNetwork, blockNumber int) {
	errTransactions := 0
	if len(mynetwork.Peers) < 1 { panic("No peers in network to run this test") }
	peername := mynetwork.Peers[0].PeerDetails["name"]
	height, _ := chaincode.GetChainHeight(peername)
	lstutil.Logger(fmt.Sprintf("++++++++++ getBlockTxInfo(%d) Total Blocks # %d", blockNumber, height))

	for i := 1; i < height; i++ {
	    if blockNumber == 0 || blockNumber == i {
		lstutil.Logger(fmt.Sprintf("+++++ Current BLOCK %d +++++", i))
		txList, _ := chaincode.GetBlockTrxInfoByHost(peername, i)
		length := len(txList)
		for j := 0; j < length; j++ {
			lstutil.Logger(fmt.Sprintln("Block[%d] TX[%d] Txid [%d]", i, j, txList[j].Txid))
		}
	    }
	}
	if errTransactions > 0 {
		lstutil.Logger(fmt.Sprintf("\nTotal Blocks ERRORS # %d", errTransactions))
	}
}

func timeTrack(start time.Time, name string) {
	elapsed := time.Since(start)
	lstutil.Logger(fmt.Sprintf("%s , elapsed %s\n", name, elapsed))
}

func check(e error) {
	if e != nil {
		panic(e)
	}
}
