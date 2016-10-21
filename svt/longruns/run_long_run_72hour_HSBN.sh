#!/bin/bash

USAGE="Usage: 
      export COMMIT=<commit_level> 
      ${0}"
   
echo -e "$USAGE "

# USE THIS _sigs() signal catcher/forwarder to pass signal to the child process.
trap 'echo $0 Received termination signal.; kill $! 2>/dev/null; exit' SIGHUP SIGINT SIGQUIT SIGTERM SIGABRT

cd ../../fvt/consensus/obcsdk/automation/

PRE_COMMIT="$COMMIT"
source ./ENVVARS_Z
if [ "$PRE_COMMIT" != "" ]
then
  COMMIT="$PRE_COMMIT"
fi
echo -e "COMMIT=$COMMIT"
export COMMIT
export TEST_NET_COMM_PROTOCOL=HTTP

# comment out; do not run script to start a network here, since network should be running already!
#./local_fabric_gerrit.sh -n 4 -s -c $COMMIT 

#cp ../util/NetworkCredentials.json.HSBN_NISHI ../util/NetworkCredentials.json
echo -e "Make sure you copied HSBN network credentials JSON file to util folder ../util/NetworkCredentials.json before running this test"

cd ../ledgerstresstest/
GOTESTNAME=LongRun72hrAuto
go run ${GOTESTNAME}.go | tee -a "GO_TEST__${GOTESTNAME}__$(date | cut -c 4-80 | tr -d ' ').log"

