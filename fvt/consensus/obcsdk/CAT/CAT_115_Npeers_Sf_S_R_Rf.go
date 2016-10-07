package main

// This test may require manual inspection of results, to be sure consensus stops when appropriate.
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
	"time"
	"bufio"
	"../chco2"
	"fmt"
	//"strings"
	//"errors"
	"strconv"
	// "bufio"
	// "log"
)

var osFile *os.File

func main() {

	//=======================================================================================
	// SET THE TESTNAME:  set the filename/testname here, to display in output results.
	//=======================================================================================

	chco2.CurrentTestName = "CAT_115_Npeers_Sf_S_R_Rf"


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
	//	chco2.Verbose = true			// See also: "verbose" in ../chaincode/const.go
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
	//	WaitAndConfirm()
	// To be implemented soon:
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
	// if (chco2.Verbose) { fmt.Println("Sleep extra 60 secs") } time.Sleep(chco2.SleepTimeSeconds(60))
	// time.Sleep(chco2.SleepTimeMinutes(1))
	// 
	//=======================================================================================


	//=======================================================================================
	// DEFINE MAIN TESTCASE STEPS HERE
	// 
	// CAT_115_Npeers_Sf_S_R_Rf
	// Stop "f" peers
	// Stop one more peer; consensus should stop
	// Restart one peer; consensus should resume
	// Restart all the remaining "f" stopped peers; consensus should continue, and
	//   they should all participate and keep getting closer to the correct counter
	// 
	// Recall these key values: 
	// chco2.NumberOfPeersInNetwork = 				N, as set by envvar CORE_PBFT_GENERAL_N
	// chco2.NumberOfPeersOkToFail =				f, as set by envvar CORE_PBFT_GENERAL_F (or defaults to maxf)
	// chco2.MaxNumberOfPeersThatCanFailWhileStillHaveConsensus =	maxf, the max possible value of f, as defined by (N-1)/3
	// chco2.MinNumberOfPeersNeededForConsensus =			2*maxf+1
	// chco2.NumberOfPeersNeededForConsensus =			2*f+1

	fmt.Println("Values of N, F, maxF: ", chco2.NumberOfPeersInNetwork, chco2.NumberOfPeersOkToFail, chco2.MaxNumberOfPeersThatCanFailWhileStillHaveConsensus )
	if chco2.NumberOfPeersOkToFail < chco2.MaxNumberOfPeersThatCanFailWhileStillHaveConsensus {
		fmt.Println(fmt.Sprintf("Notice: this test will stop F+1 nodes, because envvar CORE_PBFT_GENERAL_F was set by the user to a value < max_possible_F"))
	}

	// make a slice and populate with the first "f" peer numbers, 0..(f-1)
	var fPeers []int
	fPeers = make([]int, chco2.NumberOfPeersOkToFail)
	peerNum := 0
	for peerNum = 0; peerNum < chco2.NumberOfPeersOkToFail; peerNum++ { fPeers[peerNum] = peerNum }

	numInvokes := chco2.NumberOfPeersInNetwork

	chco2.StopPeers( fPeers )
	chco2.Invokes( numInvokes )
	if (chco2.Verbose) { fmt.Println("Sleep extra 10 secs") }
	time.Sleep(chco2.SleepTimeSeconds(10))
	chco2.QueryAllPeers( "STEP 3, after stopping F=" + strconv.Itoa(chco2.NumberOfPeersOkToFail) + " / " + strconv.Itoa(chco2.NumberOfPeersInNetwork) + " peers in network" )

	chco2.StopPeers( []int{ peerNum } )
	chco2.Invokes( numInvokes )
	if (chco2.Verbose) { fmt.Println("Sleep extra 10 secs") }
	time.Sleep(chco2.SleepTimeSeconds(10))
	chco2.QueryAllPeers( "STEP 6, after stopping one more peer - should HALT consensus network progress" )

	chco2.AllRunningNodesMustMatch = true    
	chco2.RestartPeers( []int{ peerNum } )
	chco2.Invokes( numInvokes )
	if (chco2.Verbose) { fmt.Println("Sleep extra 60 secs") }
	time.Sleep(chco2.SleepTimeSeconds(60))
	chco2.QueryAllPeers( "STEP 9, after restarting one peer - should RESUME consensus network progress" )

	chco2.AllRunningNodesMustMatch = false
	chco2.RestartPeers( fPeers )
	chco2.Invokes( numInvokes )
	if (chco2.Verbose) { fmt.Println("Sleep extra 60 secs") }
	time.Sleep(chco2.SleepTimeSeconds(60))
	chco2.QueryAllPeers( "STEP 12, after restarting all F stopped peers" )

	chco2.Invokes( chco2.InvokesRequiredForCatchUp )
	if (chco2.Verbose) { fmt.Println("Sleep extra 10 secs") }
	time.Sleep(chco2.SleepTimeSeconds(20))
	chco2.QueryAllPeers( "STEP 14, after more invokes" )

	chco2.Invokes( chco2.InvokesRequiredForCatchUp )
	if (chco2.Verbose) { fmt.Println("Sleep extra 10 secs") }
	time.Sleep(chco2.SleepTimeSeconds(20))
	chco2.QueryAllPeers( "STEP 16, after more invokes" )

	chco2.Invokes( chco2.InvokesRequiredForCatchUp )
	if (chco2.Verbose) { fmt.Println("Sleep extra 10 secs") }
	time.Sleep(chco2.SleepTimeSeconds(20))
	chco2.QueryAllPeers( "STEP 16, after more invokes" )

	chco2.CatchUpAndConfirm()

	chco2.RanToCompletion = true	// DO NOT MOVE OR CHANGE THIS. It must remain last.
}

