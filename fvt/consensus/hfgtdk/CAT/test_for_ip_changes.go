package main

// 
// INSTRUCTIONS:
// 
// 1. Change chco2.CurrentTestName, to set this test name = this filename
// 2. Edit to add your test steps at the bottom.
// 3. go build setupTest.go
// 4. go run setupTest.go  - or better yet, to save all results use script:  gorecord.sh setupTest.go
// 
// 
// SETUP STEPS included already:
// -----------------------------
// Default Setup: 4 peer node network with security CA node using local docker containers.
// (To change network characteristics and tuning parameters, change consts in file ../chco2/chco2.go)
// 
// SETUP 1: Deploy chaincode_example02 with A=1000000, B=1000000 as initial args.
// SETUP 2: Send INVOKES (moving 1 from A to B) once on each peer node.
// SETUP 3: Query all peers to validate values of A, B, and chainheight.
// 


import (
	"os"
	"os/exec"
	"time"
	"bufio"
	"../chco2"
	"fmt"
	"strconv"
	// "bufio"
	// "log"
	"../peernetwork"
)

var osFile *os.File

func main() {

	//=======================================================================================
	// SET THE TESTNAME:  set the filename/testname here, to display in output results.
	//=======================================================================================

	chco2.CurrentTestName = "CAT_ip_debug.go"


	//=======================================================================================
	// Getting started: output file, test timing, setup/init, and start & confirm the network
	//=======================================================================================

	if (chco2.Verbose) { fmt.Println("Welcome to test " + chco2.CurrentTestName) }

	chco2.RanToCompletion = false
	startTime := time.Now()
	_, err := os.Stat(chco2.OutputSummaryFileName)	// Stat returns *FileInfo. It will return an error if there is no file.
	if err != nil {
		if os.IsNotExist(err) {
			// File simply does not exist. Create the *File.
			osFile, err = os.Create(chco2.OutputSummaryFileName)
			chco2.Check(err)
		} else {
			chco2.Check(err)  // some other error; panic and exit.
		}
	} else {
		// open the existing file
		osFile, err = os.OpenFile(chco2.OutputSummaryFileName, os.O_RDWR|os.O_APPEND, 0666)
		chco2.Check(err)
	}
	defer osFile.Close()
chco2.Writer = bufio.NewWriter(osFile)

	// When main() ends, print the test PASS/FAIL line, with elapsed time, to outfile and to stdout
	defer chco2.TimeTrack(startTime, chco2.CurrentTestName)

	// Initialize everything, and start the network: deploy, invoke once on each peer, and query all peers to confirm
	chco2.Setup( chco2.CurrentTestName, startTime )


	//=======================================================================================
	// 
	// OPTIONAL OVERRIDES:
	// 	Tune these booleans to control verbosity and test strictness.
	// 	These booleans are initialized inside chco2.Setup(), as follows.
	// 
	//	Note: Set AllRunningNodesMustMatch to false when need merely enough peers for consensus
	// 	to match results, especially when test involves stopping or pausing peer nodes.
	// 	OR, set it true (default) when all active running peers must match (e.g. at init
	// 	time, or after sending enough invokes after a node outage to guarantee that all
	// 	peers are caught up, in sync, with matching values for chainheight, A & B.
	// 
	//	Simply uncomment any lines here for this testcase to override
	//	the default values, as defined in ../chco2/chco2.go
	// 
	// 	chco2.Verbose = true			// See also: "verbose" in ../chaincode/const.go
	// 	chco2.Stop_on_error = true
	// 	chco2.EnforceQueryTestsPass = false
	//	chco2.EnforceChainHeightTestsPass = false
	//	chco2.AllRunningNodesMustMatch = false 	// Note: chco2 inits to true, but sets this false when restart a peer node
	//	chco2.CHsMustMatchExpected = true	// not fully implemented and working, so leave this false for most TCs
	//	chco2.QsMustMatchExpected = false 	// Note: until #2148 is solved, you may need to set false here if testcase has complicated multiple stops/restarts
	//	chco2.DefaultInvokesPerPeer = 1		//  1 = default. Uncomment and change this here to override for this testcase.
	//	chco2.TransPerSecRate = 20		// 20 = default. Uncomment and change this here to override for this testcase.


	//=======================================================================================
	// 
	// chco2. API available function calls in ../chco2/chco2.go:
	// 
	//	DeployNew(A int, B int)
	//	Invokes(totalInvokes int)
	//	InvokeOnEachPeer(numInvokesPerPeer int)
	//	InvokeOnThisPeer(totalInvokes int, peerNum int)
	//	QueryAllPeers(stepName string)
	//	StopPeers(peerNums []int)
	//	RestartPeers(peerNums []int)
	//	QueryMatch(currA int, currB int)
	//	SleepTimeSeconds(secs int) time.Duration
	//	SleepTimeMinutes(minutes int) time.Duration
	//	CatchUpAndConfirm()
	// To be implemented soon:
	//	WaitAndConfirm()
	//	PausePeers(peerNums []int)
	//	UnpausePeers(peerNums []int)
	// 
	// Example usages:
	// 
	// chco2.DeployNew( 9000, 1000 )
	// chco2.Invokes( chco2.InvokesRequiredForCatchUp )
	// chco2.InvokeOnEachPeer( chco2.DefaultInvokesPerPeer )
	// InvokeOnThisPeer( 100, 0 )
	// chco2.StopPeers( []int{ 99 } )
	// chco2.QueryAllPeers( "STEP 6, after STOP PEERs " + strconv.Itoa(99) )
	// chco2.RestartPeers( []int{ j, k } )
	// chco2.QueryAllPeers( "STEP 9, after RESTART PEERs " + strconv.Itoa(j) + ", " + strconv.Itoa(k) )
	// if (chco2.Verbose) { fmt.Println("Sleep extra 120 secs") }
	// time.Sleep(chco2.SleepTimeSeconds(120))
	// time.Sleep(chco2.SleepTimeMinutes(2))
	// 
	//=======================================================================================


	//=======================================================================================
	// DEFINE MAIN TESTCASE STEPS HERE
	// 

	// CAT_ip_debug.go

	//chaincode.DisplayPeerIp(chco2.MyNetwork, -1)
	displayPeerIp(-1)

	numCycles := 1
	for i:=1; i <= numCycles; i++ {
		for peerNum :=0; peerNum < chco2.NumberOfPeersInNetwork; peerNum++ {
			chco2.StopPeers( []int{ peerNum } )
			chco2.Invokes( chco2.InvokesRequiredForCatchUp )
			if (chco2.Verbose) { fmt.Println("Sleep extra 30 secs") }
			time.Sleep(chco2.SleepTimeSeconds(30))
			chco2.QueryAllPeers( "STEP 3, cycle " + strconv.Itoa(i) + "/" + strconv.Itoa(numCycles) + " after STOP PEER " + strconv.Itoa(peerNum) + " and Invokes" )
			chco2.RestartPeers( []int{ peerNum } )

			//chaincode.DisplayPeerIp( chco2.MyNetwork, peerNum )
			displayPeerIp( peerNum )

			chco2.Invokes( chco2.InvokesRequiredForCatchUp )
			if (chco2.Verbose) { fmt.Println("Sleep extra 30 secs") }
			time.Sleep(chco2.SleepTimeSeconds(30))
			chco2.QueryAllPeers( "STEP 6, cycle " + strconv.Itoa(i) + "/" + strconv.Itoa(numCycles) + " after RESTART and Invokes " )

			//chco2.DeployNew(10000*i+1000*peerNum,10000*i+1000*peerNum)
			//chco2.QueryAllPeers( "STEP 8, cycle " + strconv.Itoa(i) + "/" + strconv.Itoa(numCycles) + " after REDEPLOY new values" )

			chco2.DeployNew(1000000,1000000)
			if (chco2.Verbose) { fmt.Println("Sleep extra 30 secs") }
			time.Sleep(chco2.SleepTimeSeconds(30))
			chco2.QueryAllPeers( "STEP 8, cycle " + strconv.Itoa(i) + "/" + strconv.Itoa(numCycles) + " after REDEPLOY same init values" )

			chco2.Invokes( chco2.InvokesRequiredForCatchUp )
			if (chco2.Verbose) { fmt.Println("Sleep extra 30 secs") }
			time.Sleep(chco2.SleepTimeSeconds(30))
			chco2.QueryAllPeers( "STEP 10, cycle " + strconv.Itoa(i) + "/" + strconv.Itoa(numCycles) + " after Invoke on each peer" )
		}
	}

	// chco2.Invokes(1000)				// OPTIONAL. Number could vary, based on the testcase.
	// chco2.AllRunningNodesMustMatch = true    	// OPTIONAL. Depends on testcase details and objectives.
	// chco2.QueryAllPeers( "STEP FINAL, after 1000 invokes")

	chco2.CatchUpAndConfirm()

	chco2.RanToCompletion = true	// DO NOT MOVE OR CHANGE THIS. It must remain last.
}

func displayPeerIp(selectPeer int) {
	for peerNum := 0; peerNum < chco2.NumberOfPeersInNetwork; peerNum++ {
	    if selectPeer < 0 || selectPeer == peerNum {
                cmd_str := "docker inspect --format '{{.NetworkSettings.IPAddress}}' " + peernetwork.PeerName(peerNum)
                //fmt.Println("--------------- displayPeerIp: To display IP Address of peer, executing command:  ", cmd_str)
                fmt.Printf(fmt.Sprintf("--------------- displayPeerIp: docker inspect IP Address of peer %s = ", peernetwork.PeerName(peerNum)))
                var shellCmd *exec.Cmd
                shellCmd = exec.Command("/bin/sh", "-c", cmd_str)
                shellCmd.Stdout = os.Stdout
                shellCmd.Stderr = os.Stderr
                cmderr := shellCmd.Run()
                if (cmderr != nil) { fmt.Println("--------------- displayPeerIp: exec.Command err: ", cmderr) }
	    }
	}
}
