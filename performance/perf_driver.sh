#!/bin/bash

#
# usage: ./perf_driver.sh <user input json file> <chaincode path> <nLPARs>
# example: ./perf_driver.sh userInput-example02.json $GOPATH/src/github.com/chaincode_example02 2 bluemix
#          ./perf_driver.sh userInput-artchaincode.json $GOPATH/src/github.com/artchaincode 1 local
#

userinput=$1
ccPath=$2
nLPARs=$3
bcHost=$4

echo "user input: $userinput, ccPath: $ccPath, nLPARs=$nLPARs bcHost=$bcHost"

CWD=$PWD
echo "current directory: $CWD"
# clone vendor
if [ -d $ccPath/vendor/github.com/hyperledger/fabric ]; then
    echo 'vendor dir exists'
else
    echo 'get vendor ...'
    mkdir $ccPath/vendor
    mkdir $ccPath/vendor/github.com
    mkdir $ccPath/vendor/github.com/hyperledger
    cd $ccPath/vendor/github.com/hyperledger
    git clone https://github.com/hyperledger/fabric.git
    cd $CWD
fi

echo "pwd= $PWD"

#
# download certificate file
#
if [ $bcHost = "bluemix" ]
then

    echo "********************** downloading certificate.pem **********************"
    node perf-certificate.js $userinput $ccPath
    #sleep 5
    echo "bcHost $bcHost"
fi

#
# set up the start execution time
#
    #tWait=$[nLPARs*4000+200000]
    tWait=$[nLPARs*4000+150000]
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
	node perf-main.js $LPARid $userinput $ccPath $tStart $bcHost &
    sleep 2   # 2 seconds
done

exit
