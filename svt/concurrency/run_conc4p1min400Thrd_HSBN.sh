#!/bin/bash

USAGE="Usage: 
      export COMMIT=<commit_level> 
      And copy your HSBN NetworkCredentials file to ../util/NetworkCredentials.json before running the test
      ${0}
"
   
echo -e "$USAGE"

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

#cp networkcredentials ../util/NetworkCredentials.json

cd ../ledgerstresstest/
GOTESTNAME=conc4p1min400Thrd
go run ${GOTESTNAME}.go | tee -a "GO_TEST__${GOTESTNAME}__$(date | cut -d' ' -f2-9 | sed 's/[ :]/_/g').log"

