#u/bin/bash

USAGE="Usage: 
      export COMMIT=<commit_level> 
      ${0}"
   
echo -e "$USAGE "

# USE THIS _sigs() signal catcher/forwarder to pass signal to the child process.
trap 'echo $0 Received termination signal.; kill $! 2>/dev/null; exit' SIGHUP SIGINT SIGQUIT SIGTERM SIGABRT

cd ../../fvt/consensus/obcsdk/automation/

./local_fabric_gerrit.sh -n 4 -s -c $COMMIT 

cd ../ledgerstresstest/
go run LongRun72hr.go

