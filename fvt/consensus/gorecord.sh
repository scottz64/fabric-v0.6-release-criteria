#!/bin/bash

##########################################################################################
# FUNCTIONS
##########################################################################################

##########################################################################################
# USE THIS _sigs() signal catcher/forwarder to pass signal to the child process.
# Write function _sigs(), or do it with one line:
# trap 'echo I am going down, so killing off my processes..; kill $!; exit' SIGHUP SIGINT SIGQUIT SIGTERM 

_sigs() { 
echo -e "\n=========== go run $testcase ABORTABORTABORTABORTABORTABORT `date` ==========" | tee -a $OUT | tee -a $SUMMARY
echo -e   "=========== SKIPPING any remaining testcases; caught a termination signal!"    | tee -a $OUT | tee -a $SUMMARY
kill -SIGINT "$child" 2>/dev/null
#kill        "$child" 2>/dev/null
exit
}


##########################################################################################
headerInfo() {
echo -e   "\n=========== GROUP START TIME ${STARTDATE}" | tee -a ${SUMMARY}
echo -e     "==========="
echo -e   "\nNote: Output is recorded to file ${OUT}"
echo -e   "\nNote: Brief test summaries are also written by tests themselves to file ${SUMMARY}"
set ${TESTNAMES}
echo -e   "\nPreparing to run these ${#} testcases:\n$(/bin/ls ${TESTNAMES})"
echo -e   "\nUsing test environment variables:\n"
LOCAL_FABRIC_SH=$GOPATH/src/github.com/hyperledger/fabric/vendor/obcsdk/automation/local_fabric.sh
grep "^IMAGE="            $LOCAL_FABRIC_SH
grep "^PEER_IMAGE="       $LOCAL_FABRIC_SH
grep "^MEMBERSRVC_IMAGE=" $LOCAL_FABRIC_SH
grep "^CONSENSUS="        $LOCAL_FABRIC_SH
grep "^PBFT"              $LOCAL_FABRIC_SH
awk '/^membersrvc_setup/,/^[}]/' $LOCAL_FABRIC_SH | awk '/name=PEER/,/peer node start/'
}
# Also, to ensure our chaincode test code uses same parameter settings as the peer network itself,
# user should check these when using pbft batch mode:
# 	PARAMETER 				DEFAULT		chco2.go CONST NAME
# 	--------- 				-------		-------------------
# 	CORE_PBFT_GENERAL_F 			1		NumberOfPeersOkToFail
# 	CORE_PBFT_GENERAL_N 			4		NumberOfPeersInNetwork
#       CORE_PBFT_GENERAL_K 			10		K
#	CORE_PBFT_GENERAL_LOGMULTIPLIER		4		logmultiplier
#	CORE_PBFT_GENERAL_BATCHSIZE 		500		Batchsize
#	CORE_PBFT_GENERAL_TIMEOUT_BATCH 	2s		batchtimeout
#       Note (may impact testcase duration): InvokesRequiredForCatchup = (K * batchsize * logmultiplier)


##########################################################################################
trailerInfo() {
echo -e "\n=========== GROUP END"
echo -e "${STATS_BEFORE_RUN_GROUP}"
echo -e "${STATS_AFTER_RUN_GROUP}"
}


##########################################################################################
runTests() {
for testcase in ${TESTNAMES}
do
	echo -e "\n\n----------- go run $testcase STARTSTARTSTARTSTARTSTARTSTART `date` -----------" 
	echo -e     "-----------"
	#ls -l $testcase	&
	go run $testcase	&
	# echo go run $testcase ... child PID = $! 
	child=$! 
	wait "$child"
	echo -e     "-----------"
	echo -e     "----------- go run $testcase FINISHFINISHFINISHFINISHFINISH `date` -----------" 
done
}


##########################################################################################
# BEGIN MAIN ROUTINE
# 
# Catch signals, process arguments, and define global variables:
#   TESTNAMES, OUT and SUMMARY output file names, STARTDATE, STATS_BEFORE_RUN_GROUP
##########################################################################################

trap _sigs SIGTERM SIGINT SIGHUP SIGQUIT SIGABRT

USAGE="usage:   ${0} <testname.go>..."
if [ ${#} -eq 0 ]
then
	echo -e "error:   no testnames provided"
	echo -e "$USAGE"
	exit
fi

# This looks for only the .go files, but it finds them in the current AND CHILD directories if there is
# a directory name that matches the arguments passed in. For example, if you execute: gorecord.sh CAT_11*
# and if you have file CAT_11.go and CAT_11 directory with .go files, then it will find CAT_11.go AND ALSO
# all *.go files inside CAT_11/.
#TESTNAMES=$(/bin/ls ${*} | grep "\.go$")
# So, for now, just make the user type their filenames by specifying .go
#TESTNAMES=$( grep "\.go$" ${*} )

TESTNAMES="${*}"
if  [ -z "${TESTNAMES}" ]
then
	echo -e "error:   no  <*.go>  testnames provided"
	echo -e "$USAGE"
	exit
fi
set ${TESTNAMES}
if [ ${#} -eq 1 ]
then
	OUT="GO_TEST__$(echo ${*} | tr -d ' ')__$(date | cut -c 4-80 | tr -d ' ')"
else
	OUT="GO_TEST__MULTI__$(date | cut -c 4-80 | tr -d ' ')"
fi

SUMMARY="GO_TESTS_SUMMARY"
STARTDATE="`date`"
STATS_BEFORE_RUN_GROUP=$(echo -e "=========== ${STARTDATE}, BEFORE RUN GROUP: BEGIN=`grep -c ^BEGIN ${SUMMARY}` , PASSED=`grep -c ^PASSED ${SUMMARY}` , FAILED=`grep -c ^FAILED ${SUMMARY}`")

# Print the header info, run the tests, and print the summary trailer info.

headerInfo   | tee -a ${OUT}

runTests     | tee -a ${OUT}

STATS_AFTER_RUN_GROUP=$(echo -e "=========== `date`, AFTER RUN GROUP : BEGIN=`grep -c ^BEGIN ${SUMMARY}` , PASSED=`grep -c ^PASSED ${SUMMARY}` , FAILED=`grep -c ^FAILED ${SUMMARY}`")

trailerInfo  | tee -a ${OUT} | tee -a ${SUMMARY}

