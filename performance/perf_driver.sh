#!/bin/bash

#
# usage: ./perf_driver.sh <user input json file> <chaincode path> <nLPARs>
# example: ./perf_driver.sh userInput-example02.json $GOPATH/src/github.com/chaincode_example02 2
#          ./perf_driver.sh userInput-artchaincode.json $GOPATH/src/github.com/artchaincode 1
#

userinput=$1
ccPath=$2
nLPARs=$3

echo "user input: $userinput, ccPath: $ccPath, nLPARs=$nLPARs"


#
# download certificate file
#
    echo "********************** downloading certificate.pem **********************"
    node perf-certificate.js $userinput $ccPath
    #sleep 5

#
# set up the start execution time
#
    tWait=$[nLPARs*4000+200000]
    tCurr=`date +%s%N | cut -b1-13`

    tStart=$[tCurr+tWait]
    #echo "timestamp: execution start= $tStart, current= $tCurr, wait= $tWait"

#
# execute performance test
#

for ((LPARid=0; LPARid<$nLPARs; LPARid++))
do
    tCurr=`date +%s%N | cut -b1-13`
	t1=$[tStart-tCurr]
    echo  "******************** sending LPAR $LPARid requests: now=$tCurr, starting time=$tStart, time to wait=$t1 ********************"
	node perf-main.js $LPARid $userinput $ccPath $tStart &
    sleep 2   # 2 seconds
done

exit
