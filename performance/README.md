#Performance Node SDK - Hyperledger Fabric


The performance Node SDK requires Hyperledger Fabric Client (HFC) SDK to interact with a Hyperledger Fabric network, see
[Node SDK Install](http://hyperledger-fabric.readthedocs.io/en/latest/Setup/NodeSDK-setup/)
for Node SDK installation.


#Installation

    1. download all scripts (1 bash shell script and 3 js scripts) and userInput json files into the local working directory
    2. create a sub directory, SCFiles, under the working directory
    3. add Service Credentials file for each LPAR to the SCFiles directory
    4. modify userInput.json according to the desired test and the Service Credentials files


#Usages

	./perf_driver.sh <user input json file> <chaincode path> <nLPARs>

    user input json file: the json file contains all user specified parameters for the test, see below for detailed description
    chaincode path: the path to the chaincode
    nLPARs: number of LPARs

###Examples


######./perf_driver.sh userInput-example02.json $GOPATH/src/github.com/chaincode_example02 1

The above command will execute chaincode example02 on 1 LPAR based on the setting of userInput-example02.json. 



######./perf_driver.sh userInput-auction.json $GOPATH/src/github.com/auction 2

The above command will execute chaincode auction on 2 LPARs based on the setting of userInput-example02.json.


#Scripts

    perf_driver.sh: the performance driver
    perf-certificate.js: the Node js to download certificate.
    perf-main.js: the performance main js
    perf-execRequest.js: A Node js executing transaction requests


#User Input File


    {
        "transType": "Query",
	    "nPeers": "4",
        "nThread": "4",
        "nRequest": "0",
        "runDur": "600",
	    "TCertBatchSize": "200",
        "ccName": "general",
        "deploy": {
            "chaincodePath": "github.com/chaincode_example02",
            "fcn": "init",
            "args": "a,100,b,200"
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

    transType: transaction type: Invoke or Query
    nPeer: number of peers, this number has to match with the peer netwrok, default is 4
    nThread: number of threads for the test, default is 4
    nRequest: number of transaction requests for each thread
    runDur: run duration in seconds when nRequest is 0
    TCertBatchSize: TCert batch size, default is 200
    ccName: name of the chaincode, 
        auction: The first argument in the query and invoke request is incremented by 1 for every transaction.  And, the invoke payload is made of a random string with a random size between 1KB to 2KB.  This will make all invoke trnasactions different. 
        general: The arguments of transaction request are taken from the user input json file without any changes.
    deploy: deploy contents
    query: query contents
    invoke: invoke contants
    SCFile: the list of service credentials for each LPAR.


#Service Credentials

The service credentials for each LPAR can be either downloaded or created by copy and paste from Bluemix network.

#Chaincodes

The following chaincodes are supported:

    example02
    auction chaincode

#Traffic Patterns

The following is the list of supported traffic patterns:

###simple:

The subsequent transaction is executed after the result, regardless it completed or failed, of the previous one is received.


#Transaction Execution

All threads execute the same transaction concurrently. Two types of executions are supported.

###By number:

Each thread executes the specified number of transactions specified by nRequest in the user input file.
    
###By run time duration:

Each thread executes the same transaction concurrently for the specified time duration specified by runDur in the user input file, note that nRequest must be 0.


#Output

The output includes LPAR id, thread id, transaction type, total transactions, completed transactions, failed transactions, starting time, ending time, and elapsed time.

The following is an example of queries test output. The test contains 4 threads on one LPAR.  The output shows that LPAR 0 thread 2 executed 272 queries with no failure in 60008 ms, LPAR 0 thread 3 executed 288 queries with no failure in 60008 ms etc. 

    stdout: LPAR:id=0:2, Query test completed: total= 272 completed= 272 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187415 elapsed= 60008

    stdout: LPAR:id=0:3, Query test completed: total= 288 completed= 288 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187415 elapsed= 60008

    stdout: LPAR:id=0:0, Query test completed: total= 272 completed= 272 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187563 elapsed= 60156

    stdout: LPAR:id=0:1, Query test completed: total= 270 completed= 270 failed= 0 time(ms): starting= 1473881127407 ending= 1473881187593 elapsed= 60186


