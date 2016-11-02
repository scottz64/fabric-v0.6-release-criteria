#Performance Node SDK - Hyperledger Fabric


The performance Node SDK uses [Hyperledger Fabric Client (HFC) SDK](http://hyperledger-fabric.readthedocs.io/en/latest/Setup/NodeSDK-setup/) to interact with a [Hyperledger fabric](https://github.com/hyperledger/fabric) network.


#Installation

1. download all scripts (1 bash shell script and 3 js scripts) and userInput json files into the local working directory
1. create a sub directory, SCFiles, under the working directory
1. add Service Credentials file for each LPAR to the SCFiles directory
1. modify userInput.json according to the desired test and the Service Credentials files


#Usages

	./perf_driver.sh <user input json file> <chaincode path> <nLPARs> <bcHost>


* user input json file: the json file contains all user specified parameters for the test, see below for description

* chaincode path: the path to the chaincode, this path is in src directory under current working directory, see example below

* nLPARs: number of LPARs

* bcHost: location of the network.  For the local network (bcHost=local), no certificate to be used.  For bluemix network (bcHost=bluemix), the certificate will be downloaded from the address specified in the service credential file.

###Examples


* ./perf_driver.sh userInput-example02.json src/chaincode_example02 1 bluemix

The above command will execute chaincode example02 on 1 LPAR based on the setting of userInput-example02.json with the bluemix network



* ./perf_driver.sh userInput-auction.json src/auction 2 local

The above command will execute chaincode auction on 2 LPARs based on the setting of userInput-example02.json with the local network


#Scripts

* perf_driver.sh: the performance driver
* perf-certificate.js: the Node js to download certificate.
* perf-main.js: the performance main js
* perf-execRequest.js: A Node js executing transaction requests


#User Input File


    {
        "transMode": "Simple",
        "transType": "Query",
	    "nPeers": "4",
        "nThread": "4",
        "nRequest": "0",
        "runDur": "600",
        "Burst": {
            "burstFreq0":  "500",
            "burstDur0":  "3000",
            "burstFreq1": "2000",
            "burstDur1": "10000"
        },
        "Mix": {
            "mixFreq": "2000"
        },
        "Constant": {
            "recHIST": "HIST",
            "constFreq": "1000"
        },
	    "TCertBatchSize": "200",
        "ccType": "general",
        "ccOptions": {
            "keyStart": "5000",
            "payLoadMin": "1024",
            "payLoadMax": "2048"
        },
        "deploy": {
            "chaincodePath": "github.com/chaincode_example02",
            "fcn": "init",
            "args": ["a","100","b","200"]
        },
        "query": {
            "fcn": "query",
            "args": ["a"]
        },
        "invoke": {
            "fcn": "invoke",
            "args": ["a","b","1"]
        },   
	    "SCFile": [
	        {"ServiceCredentials":"SCFiles/ServiceCredentials0000.json"},
		    {"ServiceCredentials":"SCFiles/ServiceCredentials0001.json"},
	 	    {"ServiceCredentials":"SCFiles/ServiceCredentials0002.json"},
		    {"ServiceCredentials":"SCFiles/ServiceCredentials0003.json"}
	    ]
    }
    
where:

* **transMode**: transaction mode

 * Simple: one transaction type and rate only, the subsequent transaction is sent when the response, success or failure, of the previous transaction is received

 * Burst: various traffic rates

 * Mix: mix invoke and query transactions

 * Constant: the transactions are sent by the specified rate, constFreq, regardless the response

* **transType**: transaction type

 * Invoke: invokes transaction

 * Query: query transaction

* **nPeer**: number of peers, this number has to match with the peer netwrok, default is 4

* **nThread**: number of threads for the test, default is 4

* **nRequest**: number of transaction requests for each thread

* **runDur**: run duration in seconds when nRequest is 0

* **Burst**: the frequencies and duration for Burst transaction mode traffic. Currently, two transaction rates are supported. The traffic will issue one transaction every burstFreq0 ms for burstDur0 ms, then one transaction every burstFreq1 ms for burstDur1 ms, then the pattern repeats. These parameters are valid only if the transMode is set to Burst.

  * burstFreq0: frequency in ms for the first transaction rate

  * burstDur0:  duration in ms for the first transaction rate

  * burstFreq1: frequency in ms for the second transaction rate

  * burstDur1:  duration in ms for the second transaction rate
    

* **Mix**: each invoke is followed by a query on every thread. This parameter is valid only the transMode is set to Mix.
  
  * mixFreq: frequency in ms for the transaction rate. This value should be set based on the characteristics of the chaincode to avoid the failure of the immediate query.

* **Constant**: the transactions are sent at the specified rate. This parameter is valid only the transMode is set to Constant.
  
  * recHist: This parameter indicates if brief history of the run will be saved.  If this parameter is set to HIST, then the output is saved into a file, namely ConstantResults.txt, under the current working directory.  Otherwise, no history is saved.

  * constFreq: frequency in ms for the transaction rate.

* **TCertBatchSize**: TCert batch size, default is 200

* **ccType**: chaincode type

  * auction: The first argument in the query and invoke request is incremented by 1 for every transaction.  And, the invoke payload is made of a random string with various size between payLoadMin and payLoadMax defined in ccOptions.

  * general: The arguments of transaction request are taken from the user input json file without any changes.

* **ccOptions**: chaincode options
  * keyStart: the starting transaction key index, this is used when the ccType is auction which requires a unique key for each invoke.

  * payLoadMin: minimum size in bytes of the payload. The payload is made of random string with various size between payLoadMin and payLoadMax.

  * payLoadMax: maximum size in bytes of the payload

* **deploy**: deploy contents

* **query**: query contents

* **invoke**e contents

* **SCFile**: the service credentials list, one per LPAR


#Service Credentials

The service credentials for each LPAR can be either downloaded or created by copy and paste from Bluemix if the network is on bluemix.  For the local network, user will need to create a json file similar to the config-local.json in SCFiles directory. 

#Chaincodes

The following chaincodes are tested and supported:

* example02

* auction chaincode



#Transaction Execution

All threads will execute the same transaction concurrently. Two types of executions are supported.

* By transaction number:

Each thread executes the specified number of transactions specified by nRequest in the user input file.
    
* By run time duration:

Each thread executes the same transaction concurrently for the specified time duration specified by runDur in the user input file, note that nRequest must be 0.

#Key Store

The private keys and certificates for authenticated users are required for performing any transactions on the blockchain. These information are stored in keyValStore directory under current working directory. The directory name is made of keyValStore followed by each LPAR Index, such as keyValStore0, keyValStore1 etc.

Whenever the network is reset, the content of the keyValStore need to be deleted.


#Chaincode ID
After chaincode is deployed, its chaincode ID is saved in <chaincode path>/chaincodeID to be used for the subsequent test to save repeated deployment.

Whenever the network is reset, this file needs to be deleted for the new deployment.


#Output

The output includes LPAR id, thread id, transaction type, total transactions, completed transactions, failed transactions, starting time, ending time, and elapsed time.

The following is an example of queries test output. The test contains 4 threads on one LPAR.  The output shows that LPAR 0 thread 2 executed 272 queries with no failure in 60008 ms, LPAR 0 thread 3 executed 288 queries with no failure in 60008 ms etc. 

    stdout: LPAR:id=0:2, Query test completed: total= 272 completed= 272 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187415 elapsed= 60008

    stdout: LPAR:id=0:3, Query test completed: total= 288 completed= 288 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187415 elapsed= 60008

    stdout: LPAR:id=0:0, Query test completed: total= 272 completed= 272 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187563 elapsed= 60156

    stdout: LPAR:id=0:1, Query test completed: total= 270 completed= 270 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187593 elapsed= 60186


