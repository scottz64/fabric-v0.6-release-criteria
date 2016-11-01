Feature (behave) tests are testing for the behavior of a feature and what the expected results should look like. 

# Summary of Tests
The tests executed in this suite cover the following general areas. Most of the networks utilized in these tests are 4 peer networks.
* basic fabric API functionality including:
	* deploy (chaincode)
	* invoke (chaincode)
	* query (chaincode)
	* block height (chain)
	* number of peers in a network (network/peers)
	* committing of transactions to a peer's ledger (transactions)
* "large" network configuration (16 peers)
* consensus (stopping and starting peers)
	* stopping chaincode and ensuring it is restarted with a query/invoke
* peer upgrade with in place data (on a separate container/partition)
	* both fallback and upgrade on a commit level

# Prerequisites
You must have the following installed:
* python
* behave
* docker
* docker-compose

You should also clone the following repository
* hyperledger-fabric (https://gerrit.hyperledger.org/r/fabric)

```sh
$ sudo apt-get install python-setuptools python-dev build-essential
$ sudo easy_install pip
$ sudo pip install behave
$ sudo pip install google
$ sudo pip install protobuf
$ sudo pip install grpc
$ sudo pip install gevent
$ sudo pip install grpcio
$ sudo pip install pyyaml
```

# Environments
This version of the fabric-based behave tests have been modified such that tests can both be executed locally as well as on a remote network that has already been setup with fabric.

## Local Network (Default)
There are different options when using the behave tool. Feel free to explore the different options that are available when executing the tests. (http://pythonhosted.org/behave/behave.html)

### Setup
The only setup that is needed before executing the behave tests is to make sure that the peer and membersrvc build images are in the correct location. Ensure that the hyperledger-fabric repository is present in your environment and that you have a symlink to the correct location such that the behave tests can execute the tests correctly. Be sure to enter the correct paths when setting the symlink.

```sh
$ git clone <hyperledger-fabric>
$ ln -s path/to/hyperledger/fabric/build path/to/release-criteria/behave/build
```

### Execution
The most basic execution when executing all of the available tests in the behave/tests/ directory is to simply type:
```sh
$ behave
```

## Smoke Tests
There are a handful of behave test scenarios that can be used as smoke tests to verify the very basic functionality of the network. 

### Setup
The setup for the smoke test suite is the same as the default local run. Be sure that the hyperledger-fabric repository is present in your environment and that you have a symlink to the correct location such that the behave tests can execute the tests correctly.

### Execution
These sanity tests are tagged as "smoke" and can be executed as follows:
```sh
$ behave --tags=smoke
```

## Established Remote Network
There are times when one may want to be sure that an existing network is working correctly. There are certain behave tests that can be used in order to test for basic functionality as well as basic consensus. There tests are marked using the "scat" tag. Since this is an established network, the network can not be setup and torned down between test execution. As such, the tests are executed while keeping that in mind.

### Setup
When setting up a "Bring Your Own Network"(BYON) be sure to include a networkcredentials file in the bddtests directory containing json, that consists of atleast the following information:

```
{
   "UserData": [
      {"peer": "vp0", "username": "user0", "secret": "1499234092"}, 
      {"peer": "vp1", "username": "user1", "secret": "dc026591fe"}, 
      {"peer": "vp2", "username": "user2", "secret": "8b0f8c71d2"}, 
      {"peer": "vp3", "username": "user3", "secret": "b051bf2dec"}
   ], 
   "PeerData": [
      {"port":"20000","host":"10.1.0.13","api-host":"10.1.0.13:20000","name":"vp0","user":"user0"},
      {"port":"20100","host":"10.1.0.13","api-host":"10.1.0.13:20100","name":"vp1","user":"user1"},
      {"port":"20200","host":"10.1.0.13","api-host":"10.1.0.13:20200","name":"vp2","user":"user2"},
      {"port":"20300","host":"10.1.0.13","api-host":"10.1.0.13:20300","name":"vp3","user":"user3"}
   ], 
   "PeerGrpc" :  [
     { "api-host" : "10.1.0.13", "api-port" : "20001" } , 
     { "api-host" : "10.1.0.13", "api-port" : "20101" } , 
     { "api-host" : "10.1.0.13", "api-port" : "20201" } , 
     { "api-host" : "10.1.0.13", "api-port" : "20301" } 
   ],
 "Name": "LP-36" 
} 
```

### Execution
Since we have a set network, we cannot test both https and http network setups. Assuming the remote hosts are using https:
```sh
$ behave -D tls=true -D remote-ip=10.1.0.13 --tags=scat
```

# Helpful scripts
Generating the networkcredentials file for use in the tests
For zACI environment outside of BlueMix:
```sh
$ python update_z.py -f <zACI network file name>
```

For X86 BlueMix environment:
```sh
$ python update_z.py -b -f <BlueMix X86 file name>
```

