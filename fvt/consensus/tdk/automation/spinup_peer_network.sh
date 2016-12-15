#!/bin/bash
# ------------------------------------------------------------------
# TITLE : Spinup local peer network
# AUTHOR: Ramesh Thoomu & Barry Mosakowski
# VERSION: 1.0

# DESCRIPTION:
# The purpose of this script is to spinup peers in local machine using docker.
# Peers launches on tested peer and membersrvc docker images and latest hyperledger/fabric
# base image. Script pulls these images from rameshthoomu docker hub account. Take the
# latest commit of peer and membersrvc from rameshthoomu docker hub account.

# Pre-condition: Install docker in your local machine and start docker daemon

## USAGE:
# spinup_peer_network.sh [OPTIONS]

# OPTIONS:
#       -n   - Number of peers to launch
#       -s   - Enable Security and Privacy
#       -c   - Specific commit
#       -l   - Logging detail level
#       -m   - Consensus mode
#       -b   - Set batch size, useful when using consensus pbft mode of batch
#       -f   - Number of tolerated faulty peers, when using pbft for consensus, maximum (n-1)/3
#       -?|-h - Prints Usage
#
# SAMPLE :
#       ./spinup_peer_network -n 4 -s -c x86_64-0.6.0-SNAPSHOT-f3c9a45 -l debug -m pbft -b 1000
# ------------------------------------------------------------------

ARCH=`uname -m`

echo "ARCH value is" $ARCH

if [ $ARCH = "ppc64le" ]
then

    PEER_IMAGE=hyperledger/fabric-peer-ppc64le
    MEMBERSRVC_IMAGE=hyperledger/fabric-membersrvc-ppc64le
    docker pull hyperledger/fabric-ppc64le-baseimage
fi


if [ "$ARCH" == "x86_64" ]
then
#    PEER_IMAGE=hyperledger/fabric-peer
#    MEMBERSRVC_IMAGE=hyperledger/fabric-membersrvc
    PEER_IMAGE=rameshthoomu/peer
    MEMBERSRVC_IMAGE=rameshthoomu/membersrvc
    docker pull rameshthoomu/baseimage:v0.6
    docker tag rameshthoomu/baseimage:v0.6 hyperledger/fabric-baseimage

fi


if [ "$ARCH" == "s390x" ]
then
    PEER_IMAGE=hyperledger/fabric-peer-s390x
    MEMBERSRVC_IMAGE=hyperledger/fabric-membersrvc-s390x
    docker pull hyperledger/fabric-s390x-baseimage
fi

REST_PORT=7050
USE_PORT=30000
CA_PORT=7054
PEER_gRPC=7051
EVENT_PORT=40000
PBFT_MODE=batch
WORKDIR=$(pwd)

# Membersrvc
membersrvc_setup()
{
curl -L https://raw.githubusercontent.com/hyperledger/fabric/master/membersrvc/membersrvc.yaml -o membersrvc.yaml
local NUM_PEERS=$1
local IP=$2
local PORT=$3
echo "--------> Starting membersrvc Server"

docker run -d --name=caserver -p $CA_PORT:$CA_PORT --volume=/var/run/docker.sock:/var/run/docker.sock -p 50052:7051 -it $MEMBERSRVC_IMAGE:$COMMIT membersrvc

sleep 10

CA_CONTAINERID=$(docker ps | awk '{print $1}' | awk 'NR==2')
CA_IP_ADDRESS=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $CA_CONTAINERID)

echo "--------> Starting hyperledger PEER0"

docker run -d --name=PEER0 -it \
                -e CORE_VM_ENDPOINT="http://$IP:$PORT" \
                -e CORE_PEER_ID="vp0" \
                -e CORE_SECURITY_ENABLED=true \
                -e CORE_SECURITY_PRIVACY=true \
                -e CORE_PEER_ADDRESSAUTODETECT=true -p $REST_PORT:7050 -p `expr $USE_PORT + 1`:$PEER_gRPC -p `expr $EVENT_PORT + 1`:7053 \
                -e CORE_PEER_PKI_ECA_PADDR=$CA_IP_ADDRESS:$CA_PORT \
                -e CORE_PEER_PKI_TCA_PADDR=$CA_IP_ADDRESS:$CA_PORT \
                -e CORE_PEER_PKI_TLSCA_PADDR=$CA_IP_ADDRESS:$CA_PORT \
                -e CORE_PEER_LISTENADDRESS=0.0.0.0:$PEER_gRPC \
                -e CORE_PEER_VALIDATOR_CONSENSUS_PLUGIN=$CONSENSUS_MODE \
                -e CORE_PBFT_GENERAL_MODE=$PBFT_MODE \
                -e CORE_PBFT_GENERAL_N=$NUM_PEERS \
                -e CORE_PBFT_GENERAL_F=$F \
                -e CORE_PBFT_GENERAL_BATCHSIZE=$PBFT_BATCHSIZE \
                -e CORE_PBFT_GENERAL_TIMEOUT_REQUEST=10s \
                -e CORE_PEER_LOGGING_LEVEL=$PEER_LOG \
                -e CORE_LOGGING_LEVEL=$PEER_LOG \
                -e CORE_VM_DOCKER_TLS_ENABLED=false \
                --volume=/var/run/docker.sock:/var/run/docker.sock \
                -e CORE_PEER_PROFILE_ENABLED=true \
                -e CORE_SECURITY_ENROLLID=test_vp0 \
                -e CORE_SECURITY_ENROLLSECRET=MwYpmSRjupbT $PEER_IMAGE:$COMMIT peer node start

CONTAINERID=$(docker ps | awk '{print $1}' | awk 'NR==2')
echo $CONTAINERID
PEER_IP_ADDRESS=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $CONTAINERID)
echo $PEER_IP_ADDRESS
for (( peer_id=1; $peer_id<"$NUM_PEERS"; peer_id++ ))
do
# Storing USER_NAME and SECRET_KEY Values from membersrvc.yaml file: Supports maximum 10 peers

USER_NAME=$(awk '/users:/,/^[^ ]/' membersrvc.yaml | egrep "test_vp$((peer_id)):" | cut -d ":" -f 1 | tr -d " ")
echo $USER_NAME
SECRET_KEY=$(awk '/users:/,/^[^ ]/' membersrvc.yaml | egrep "test_vp$((peer_id)):" | cut -d ":" -f 2 | cut -d " " -f 3)
echo $SECRET_KEY
REST_PORT=`expr $REST_PORT + 10`
USE_PORT=`expr $USE_PORT + 2`
EVENT_PORT=`expr $EVENT_PORT + 2`

echo "--------> Starting hyperledger PEER$peer_id <-----------"
docker run  -d --name=PEER$peer_id -it \
                -e CORE_VM_ENDPOINT="http://$IP:$PORT" \
                -e CORE_PEER_ID="vp"$peer_id \
                -e CORE_SECURITY_ENABLED=true \
                -e CORE_SECURITY_PRIVACY=true \
                -e CORE_PEER_ADDRESSAUTODETECT=true -p $REST_PORT:7050 -p `expr $USE_PORT + 1`:$PEER_gRPC -p `expr $EVENT_PORT + 1`:7053 \
                -e CORE_PEER_DISCOVERY_ROOTNODE=$PEER_IP_ADDRESS:$PEER_gRPC \
                -e CORE_PEER_PKI_ECA_PADDR=$CA_IP_ADDRESS:$CA_PORT \
                -e CORE_PEER_PKI_TCA_PADDR=$CA_IP_ADDRESS:$CA_PORT \
                -e CORE_PEER_PKI_TLSCA_PADDR=$CA_IP_ADDRESS:$CA_PORT \
                -e CORE_PEER_LISTENADDRESS=0.0.0.0:$PEER_gRPC \
                -e CORE_PEER_VALIDATOR_CONSENSUS_PLUGIN=$CONSENSUS_MODE \
                -e CORE_PBFT_GENERAL_MODE=$PBFT_MODE \
                -e CORE_PBFT_GENERAL_N=$NUM_PEERS \
                -e CORE_PBFT_GENERAL_F=$F \
                -e CORE_PBFT_GENERAL_BATCHSIZE=$PBFT_BATCHSIZE \
                -e CORE_PBFT_GENERAL_TIMEOUT_REQUEST=10s \
                -e CORE_PEER_LOGGING_LEVEL=$PEER_LOG \
                -e CORE_LOGGING_LEVEL=$PEER_LOG \
                --volume=/var/run/docker.sock:/var/run/docker.sock \
                -e CORE_VM_DOCKER_TLS_ENABLED=false \
                -e CORE_PEER_PROFILE_ENABLED=true \
                -e CORE_SECURITY_ENROLLID=$USER_NAME \
                -e CORE_SECURITY_ENROLLSECRET=$SECRET_KEY $PEER_IMAGE:$COMMIT peer node start
done
}
# Peer Setup without security and privacy
peer_setup()

{

    local  NUM_PEERS=$1
    local  IP=$2
    local  PORT=$3
echo "--------> Starting hyperledger PEER0 <-----------"
docker run -d  -it --name=PEER0 \
                -e CORE_VM_ENDPOINT="http://$IP:$PORT" \
                -e CORE_PEER_ID="vp0" \
                -p $REST_PORT:7050 -p `expr $USE_PORT + 1`:$PEER_gRPC -p `expr $EVENT_PORT + 1`:7053 \
                -e CORE_PEER_ADDRESSAUTODETECT=true \
                -e CORE_PEER_LISTENADDRESS=0.0.0.0:$PEER_gRPC \
                -e CORE_PEER_LOGGING_LEVEL=$PEER_LOG \
                -e CORE_LOGGING_LEVEL=$PEER_LOG \
                --volume=/var/run/docker.sock:/var/run/docker.sock \
                -e CORE_VM_DOCKER_TLS_ENABLED=false $PEER_IMAGE:$COMMIT peer node start

CONTAINERID=$(docker ps | awk 'NR>1 && $NF!~/caserv/ {print $1}')
PEER_IP_ADDRESS=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $CONTAINERID)

for (( peer_id=1; peer_id<"$NUM_PEERS"; peer_id++ ))
do
echo "--------> Starting hyperledger PEER$peer_id <------------"
REST_PORT=`expr $REST_PORT + 10`
USE_PORT=`expr $USE_PORT + 2`
EVENT_PORT=`expr $EVENT_PORT + 2`

docker run -d -it --name=PEER$peer_id \
                -e CORE_VM_ENDPOINT="http://$IP:$PORT" \
                -e CORE_PEER_ID="vp"$peer_id \
                -p $REST_PORT:7050 -p `expr $USE_PORT + 1`:$PEER_gRPC -p `expr $EVENT_PORT + 1`:7053 \
                -e CORE_PEER_DISCOVERY_ROOTNODE=$PEER_IP_ADDRESS:$PEER_gRPC \
                -e CORE_PEER_ADDRESSAUTODETECT=true \
                -e CORE_PEER_ADDRESS=$IP:`expr $USE_PORT + 1` \
                -e CORE_PEER_LISTENADDRESS=0.0.0.0:$PEER_gRPC \
                -e CORE_PEER_LOGGING_LEVEL=$PEER_LOG \
                -e CORE_LOGGING_LEVEL=$PEER_LOG \
                --volume=/var/run/docker.sock:/var/run/docker.sock \
                -e CORE_VM_DOCKER_TLS_ENABLED=false $PEER_IMAGE:$COMMIT peer node start
done
}

function usage()
{
        echo "USAGE :  spinup_peer_network -n <number of Peers> -s <for enabling security and privacy> -c <commit number> -l <logging level> -m <consensus mode> -f <faulty peers tolerated> -b <batchsize>"
        echo "ex: ./spinup_peer_network -n 4 -s -c x86_64-0.6.0-SNAPSHOT-f3c9a45 -l debug -m pbft -f 1 -b 500"
}

while getopts "\?hsn:c:l:m:b:f:" option; do
  case "$option" in
     s)   SECURITY="Y"     ;;
     n)   NUM_PEERS="$OPTARG" ;;
     c)   COMMIT="$OPTARG"  ;;
     l)   PEER_LOG="$OPTARG" ;;
     m)   CONSENSUS_MODE="$OPTARG" ;;
     b)   PBFT_BATCHSIZE="$OPTARG" ;;
     f)   F="$OPTARG" ;;
   \?|h)  usage
          exit 1
          ;;
  esac
done


#let's clean house

#kill all running containers and LOGFILES...Yet to implement Log rotate logic

# Docker is not perfect; first we need to unpause any paused containers, before we can kill them.
docker ps -aq -f status=paused | xargs docker unpause  1>/dev/null 2>&1

docker kill $(docker ps -q) 1>/dev/null 2>&1
docker ps -aq -f status=exited | xargs docker rm 1>/dev/null 2>&1
rm -f LOGFILE_*
docker rm -f $(docker ps -aq)
rm -rf /var/hyperledger/*

# echo "--------> Setting default Arg values that were not specified on the command line"
: ${SECURITY:="N"}
: ${NUM_PEERS="4"}
: ${COMMIT="latest"}
: ${PEER_LOG="debug"}
: ${CONSENSUS_MODE="pbft"}
: ${PBFT_BATCHSIZE="500"}
: ${F:=$((($NUM_PEERS-1)/3))} # set F default to max possible F value (N-1)/3 here when F was not specified in the command line
SECURITY=$(echo $SECURITY | tr a-z A-Z)

echo "Number of PEERS (N): $NUM_PEERS"
if [ $NUM_PEERS -le 0 ] ; then
        echo "Must enter valid number of PEERS"
        exit 1
fi

echo "Number of Faulty Peers Tolerated (F): $F"
if [ $NUM_PEERS -le $F ] ; then
        echo "Warning: F should be <= (N-1)/3 for pbft, and certainly must be less than N. Test proceeding anyways to see what the code does with it..."
fi

echo "Is Security and Privacy enabled: $SECURITY"


echo "--------> Pulling Base Docker Images from Docker Hub"


if [ "$SECURITY" == "Y" ] ; then
        echo "--------> Fetching IP address"
        IP="$(ifconfig docker0 | grep "inet" | awk '{print $2}' | cut -d ':' -f 2)"
        echo "Docker0 interface IP Address $IP"
        echo "--------> Fetching PORT number"
        PORT="$(sudo netstat -tunlp | grep docker | awk '{print $4'} | cut -d ":" -f 4)"
        echo "PORT NUMBER IS $PORT"
        echo "--------> Calling membersrvc_setup function"
        membersrvc_setup $NUM_PEERS $IP $PORT

else

        IP="$(ifconfig docker0 | grep "inet" | awk '{print $2}' | cut -d ':' -f 2)"
        echo "Docker0 interface IP Address $IP"
        PORT="$(sudo netstat -tunlp | grep docker | awk '{print $4'} | cut -d ":" -f 4)"
        echo "PORT NUMBER IS $PORT"
        echo "--------> Calling CORE PEER function"
        peer_setup $NUM_PEERS $IP $PORT
fi

echo "--------> Printing list of Docker Containers"
CONTAINERS=$(docker ps | awk 'NR>1 && $NF!~/caserv/ {print $1}')
echo CONTAINERS: $CONTAINERS
NUM_CONTAINERS=$(echo $CONTAINERS | awk '{FS=" "}; {print NF}')
echo NUM_CONTAINERS: $NUM_CONTAINERS
if [ $NUM_CONTAINERS -lt $NUM_PEERS ]
then
    echo "ERROR: NOT ALL THE CONTAINERS ARE RUNNING!!! Displaying debug info..."
    echo "docker ps -a" 
    docker ps -a
fi

# Printing Log files
for (( container_id=1; $container_id<="$((NUM_CONTAINERS))"; container_id++ ))
do
        CONTAINER_ID=$(echo $CONTAINERS | awk -v con_id=$container_id '{print $con_id}')
        CONTAINER_NAME=$(docker inspect --format '{{.Name}}' $CONTAINER_ID |  sed 's/\///')
        docker logs -f $CONTAINER_ID > "LOGFILE_$CONTAINER_NAME"_"$CONTAINER_ID" &
done

# Writing Peer data into a file for Go TDK

cd $WORKDIR
echo "creating networkcredentials file"
touch networkcredentials
echo "{" > $WORKDIR/networkcredentials
echo "   \"PeerData\" :  [" >> $WORKDIR/networkcredentials
echo " "
echo "PeerData : "

echo "----------> Printing Container ID's with IP Address and PORT numbers"
REST_PORT=7050

for (( container_id=$NUM_CONTAINERS; $container_id>=1; container_id-- ))
do

        CONTAINER_ID=$(echo $CONTAINERS | awk -v con_id=$container_id '{print $con_id}')
        CONTAINER_NAME=$(docker inspect --format '{{.Name}}' $CONTAINER_ID |  sed 's/\///')
        echo "Container ID $CONTAINER_ID   Peer Name: $CONTAINER_NAME"
        CONTAINER_NAME=$(docker inspect --format '{{.Name}}' $CONTAINER_ID |  sed 's/\///')
        peer_http_ip=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $CONTAINER_ID)
        api_host=$peer_http_ip
        api_port=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "7050/tcp") 0).HostPort}}' $CONTAINER_ID)
        echo "   { \"name\" : \"$CONTAINER_NAME\", \"api-host\" : \"$api_host\", \"api-port\" : \"$REST_PORT\" } , " >> $WORKDIR/networkcredentials

        echo " REST_EndPoint : $api_host:$api_port"
        api_port_grpc=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "7051/tcp") 0).HostPort}}' $CONTAINER_ID)
        echo " GRPC_EndPoint : $api_host:$api_port_grpc"
        api_port_event=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "7053/tcp") 0).HostPort}}' $CONTAINER_ID)
        echo " EVENT_EndPoint : $api_host:$api_port_event"
        echo " "

done
        sed  -i '$s/,[[:blank:]]*$//' $WORKDIR/networkcredentials

        echo "   ],"  >> $WORKDIR/networkcredentials

# Writing UserData into a file for go TDK
if [ "$SECURITY" == "Y" ] ; then

echo "   \"UserData\" :  [" >> $WORKDIR/networkcredentials

        echo " "

echo "Client Credentials : "
echo " "
        for ((i=0; i<=$NUM_CONTAINERS-1;i++))
        do
        CLIENT_USER=$(awk '/users:/,/^[^ #]/' membersrvc.yaml | egrep "test_user$((i)):" | cut -d ":" -f 1 | tr -d " ")
        CLIENT_SECRET_KEY=$(awk '/users:/,/^[^ #]/' membersrvc.yaml | egrep "test_user$((i)):" | cut -d ":" -f 2 | cut -d " " -f 3)
        echo "username: $CLIENT_USER  secretkey : $CLIENT_SECRET_KEY"
        echo "   { \"username\" : \"$CLIENT_USER\", \"secret\" : \"$CLIENT_SECRET_KEY\" } , " >> $WORKDIR/networkcredentials

done

        sed  -i '$s/,[[:blank:]]*$//' $WORKDIR/networkcredentials

        echo "   ],"  >> $WORKDIR/networkcredentials
fi
# Writing PeerGrpc Data into networkcredential file for go TDK

if [ "$SECURITY" == "Y" ] ; then

echo "   \"EventPorts\" :  [" >> $WORKDIR/networkcredentials
        echo " "
for (( container_id=$NUM_CONTAINERS; $container_id>=1; container_id-- ))
do

        CONTAINER_ID=$(echo $CONTAINERS | awk -v con_id=$container_id '{print $con_id}')
        CONTAINER_NAME=$(docker inspect --format '{{.Name}}' $CONTAINER_ID |  sed 's/\///')
        peer_http_ip=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $CONTAINER_ID)
        api_host=$peer_http_ip
        api_port_event=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "7053/tcp") 0).HostPort}}' $CONTAINER_ID)
        echo "   { \"api-host\" : \"$api_host\", \"api-port-event\" : \"$api_port_event\" } , " >> $WORKDIR/networkcredentials
done
        sed  -i '$s/,[[:blank:]]*$//' $WORKDIR/networkcredentials

        echo "   ],"  >> $WORKDIR/networkcredentials
fi
# Writing Grpc details into networkcredential file for go TDK
echo "   \"PeerGrpc\" :  [" >> $WORKDIR/networkcredentials
        echo " "

for (( container_id=$NUM_CONTAINERS; $container_id>=1; container_id-- ))
do

        CONTAINER_ID=$(echo $CONTAINERS | awk -v con_id=$container_id '{print $con_id}')
        CONTAINER_NAME=$(docker inspect --format '{{.Name}}' $CONTAINER_ID |  sed 's/\///')
        peer_http_ip=$(docker inspect --format '{{.NetworkSettings.IPAddress}}' $CONTAINER_ID)
        api_host=$peer_http_ip
        api_port_grpc=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "7051/tcp") 0).HostPort}}' $CONTAINER_ID)
        echo "   { \"api-host\" : \"$api_host\", \"api-port\" : \"$api_port_grpc\" } , " >> $WORKDIR/networkcredentials
done
        sed  -i '$s/,[[:blank:]]*$//' $WORKDIR/networkcredentials

        echo "   ],"  >> $WORKDIR/networkcredentials

        echo " \"Name\": \"spinup_peer_network\" " >> $WORKDIR/networkcredentials
        echo "} "  >> $WORKDIR/networkcredentials
