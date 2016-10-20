#!/bin/bash

USAGE="Usage: 
      export COMMIT=<commit_level> 
      ${0}"
   
echo -e "$USAGE "

# USE THIS _sigs() signal catcher/forwarder to pass signal to the child process.
trap 'echo $0 Received termination signal.; kill $! 2>/dev/null; exit' SIGHUP SIGINT SIGQUIT SIGTERM SIGABRT

cd ../../fvt/consensus/obcsdk/automation/

PRE_COMMIT="$COMMIT"
source ./ENVVARS_LOCAL
if [ "$PRE_COMMIT" != "" ]
then
  COMMIT="$PRE_COMMIT"
fi
echo -e "COMMIT=$COMMIT"
export COMMIT

#./local_fabric_gerrit.sh -n 4 -s -c $COMMIT 

./spinup_peer_network.sh -n 4 -s -c $COMMIT -l error  -m pbft -b 1000
cp networkcredentials ../util/NetworkCredentials.json

cd ../ledgerstresstest/
GOTESTNAME=LongRun72hr
go run ${GOTESTNAME}.go | tee -a "GO_TEST__${GOTESTNAME}__$(date | cut -c 4-80 | tr -d ' ')"

