#!/bin/bash

# ------------------------------------------------------------------
#
# TITLE : Total Transactions executed on a Network
#
# AUTHOR: Ratnakar Asara
#
# VERSION: 0.1
#
# DESCRIPTION:
#          The purpose of this script is to get the total number of 
# transactions executed (Includes both success and failure transactions)
# on a network based on the IP and PORT provided (defaults to localhost)
#
# DEPENDENCY:
#	Download and Install JQ: https://goo.gl/DsDskg
#
# USAGE:
#	QuickTrxCalci.sh [OPTIONS]
#
# OPTIONS:
#       -http://127.0.0.1:7050 - Provide the http://IP:HOST
#
# SAMPLE :l
#	./QuickTrxCalci.sh http://127.0.0.1:7050
#
#       Gives output with total transactions (includes both successful and 
# failure transaction) executed on 127.0.0.1 (localhost) with Port 7050
# ------------------------------------------------------------------

IP_PORT=$1
: ${IP_PORT:="http://127.0.0.1:7050"}

TOTAL_BLOCKS=$(curl -ks $IP_PORT/chain | jq '.height')

if test -z $TOTAL_BLOCKS ; then
	echo
	echo "Looks like IP and/or PORT are Invalid or May be Network is bad ??"
	echo
	echo "##### Sorry can't help, Please check your network and come back #####"
	echo
	exit 1
else
	echo
	echo "Chain height on $IP_PORT is $TOTAL_BLOCKS"
fi

if test "$TOTAL_BLOCKS" -le 1 ; then
	echo
	echo "... All you have got is a genesis block, no transactions available yet ..."
	echo
	echo "################### Exiting ###################"
	echo
	exit 1
fi
TOTAL_TXN=0
for (( i=1; $i<$TOTAL_BLOCKS; i++ ))
do
 TXN_COUNT=$(curl -ks $IP_PORT/chain/blocks/$i | jq "." | grep txid | wc -l )
 ##TODO: Redirect info for later postmartem purposes
 #curl -ks $IP_PORT/chain/blocks/$i | jq "."
 TOTAL_TXN=` expr $TOTAL_TXN + $TXN_COUNT`
done

echo
echo "Total Transactions made $TOTAL_TXN"
echo
echo
