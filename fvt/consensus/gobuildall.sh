#!/bin/bash

CURRPWD=`pwd`
cd ../chco2/
go build chco2.go
cd $CURRPWD

# for (( peer_id=1; $peer_id<"$NUM_PEERS"; peer_id++ ))
for name in $( /bin/ls  | grep \.go$ )
do
  go build $name
done

# for name in ${*} {
#   echo $name
# }
# go build testtemplate.go

