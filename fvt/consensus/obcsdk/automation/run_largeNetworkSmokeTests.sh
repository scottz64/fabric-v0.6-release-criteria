#!/bin/bash

SUMMARY="GO_TESTS_SUMMARY.log"
touch $SUMMARY
echo -e "Starting $0 , time now: `date`" | tee -a ${SUMMARY}

USAGE="Usage:  ${0}"
#echo -e "$USAGE"

echo -e "Reminder: you may set and export environment variables to specify network configure parameters."
echo -e "Refer to '../automation/go_record.sh' for details and for the default values."
echo -e "Default COMMIT=e4a9b47, private images built in v0.6 with more than 10 users"

# This commit in v0.6 in mid Oct 2016, built by Ramesh, contains more users. Later images should include his fix merged into fabric.
: ${COMMIT=e4a9b47}

# USE THIS _sigs() signal catcher/forwarder to pass signal to the child process.
trap 'echo $0 Received termination signal.; kill $! 2>/dev/null; exit' SIGHUP SIGINT SIGQUIT SIGTERM SIGABRT

export TEST_EXISTING_NETWORK=FALSE
export CORE_PBFT_GENERAL_BATCHSIZE=500

cd ../CAT

export CORE_PBFT_GENERAL_N=10
export CORE_PBFT_GENERAL_F=3
echo -e "CORE_PBFT_GENERAL_N=$CORE_PBFT_GENERAL_N"| tee -a ${SUMMARY}
echo -e "CORE_PBFT_GENERAL_F=$CORE_PBFT_GENERAL_F"| tee -a ${SUMMARY}
../automation/go_record.sh CAT_100*.go CRT_504_Npeers_Sf_S_R_Rf.go

export CORE_PBFT_GENERAL_N=10
export CORE_PBFT_GENERAL_F=1
echo -e "CORE_PBFT_GENERAL_N=$CORE_PBFT_GENERAL_N"| tee -a ${SUMMARY}
echo -e "CORE_PBFT_GENERAL_F=$CORE_PBFT_GENERAL_F"| tee -a ${SUMMARY}
../automation/go_record.sh CRT_504_Npeers_Sf_S_R_Rf.go

export CORE_PBFT_GENERAL_N=16
export CORE_PBFT_GENERAL_F=5
echo -e "CORE_PBFT_GENERAL_N=$CORE_PBFT_GENERAL_N"| tee -a ${SUMMARY}
echo -e "CORE_PBFT_GENERAL_F=$CORE_PBFT_GENERAL_F"| tee -a ${SUMMARY}
../automation/go_record.sh CAT_100*.go CRT_504_Npeers_Sf_S_R_Rf.go

export CORE_PBFT_GENERAL_N=16
export CORE_PBFT_GENERAL_F=2
echo -e "CORE_PBFT_GENERAL_N=$CORE_PBFT_GENERAL_N"| tee -a ${SUMMARY}
echo -e "CORE_PBFT_GENERAL_F=$CORE_PBFT_GENERAL_F"| tee -a ${SUMMARY}
../automation/go_record.sh CRT_504_Npeers_Sf_S_R_Rf.go

export CORE_PBFT_GENERAL_N=32
export CORE_PBFT_GENERAL_F=10
echo -e "CORE_PBFT_GENERAL_N=$CORE_PBFT_GENERAL_N"| tee -a ${SUMMARY}
echo -e "CORE_PBFT_GENERAL_F=$CORE_PBFT_GENERAL_F"| tee -a ${SUMMARY}
../automation/go_record.sh CAT_100*.go CRT_504_Npeers_Sf_S_R_Rf.go

echo -e "End of $0 , time now: `date`" | tee -a ${SUMMARY}
