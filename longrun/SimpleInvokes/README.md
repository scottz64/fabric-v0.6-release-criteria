# Logrun test program

This program will send multiple invokes (based on the threads configured) and runs for a long duration i.e., 72 hrs

### This is prettymuch WIP, will be updating with more programs

```
Make sure you have 4 peer network up and running and configure network details (IP and PORT) in config.json
also change duration if required

```

###Step1: Install dependent modules

`   npm install  `

or

make sure installed hfc@0.6.2

###Step2 : Run the application in the background

```
$node app.js &

Enrolled admin successfully

Enrolled JohnDoe successfully

Deploying chaincode ... It will take about 30 seconds to deploy 

[ Chaincode ID :  6f8aeae4bf2c6135be8fd722362185c7c8e81f21c6e8c685aaabcb38175f2b89 ]

Successfully deployed chaincode: request={"chaincodePath":"chaincode","fcn":"init","args":[]}, response={"uuid":"6f8aeae4bf2c6135be8fd722362185c7c8e81f21c6e8c685aaabcb38175f2b89","chaincodeID":"6f8aeae4bf2c6135be8fd722362185c7c8e81f21c6e8c685aaabcb38175f2b89"} 

completed chaincode invoke transaction: request={"chaincodeID":"6f8aeae4bf2c6135be8fd722362185c7c8e81f21c6e8c685aaabcb38175f2b89","fcn":"PostUser","args":["100","USER","Ashley Hart","TRD","Morrisville Parkway, #216, Morrisville, NC 27560","9198063535","ashley@itpeople.com","SUNTRUST","0001732345","0234678"]}, response={"result":"Tx 056ccb6f-8ac7-49be-aaf3-fd6e0dfe4f97 complete"}

ratnakar@ratnakar:~/go/src/github.com/hyperledger/fabric/perf-test$ node app.js 

chaincode already deployed, If not delete chaincodeID and keyValStore and recreate network

Get member JohnDoe

JohnDoe is available ... can create new users

completed chaincode invoke transaction: request={"chaincodeID":"6f8aeae4bf2c6135be8fd722362185c7c8e81f21c6e8c685aaabcb38175f2b89","fcn":"PostUser","args":["100","USER","Ashley Hart","TRD","Morrisville Parkway, #216, Morrisville, NC 27560","9198063535","ashley@itpeople.com","SUNTRUST","0001732345","0234678"]}, response={"result":"Tx 85ed895d-b994-4e23-8250-b5305277c2a0 complete"}
```

**Avoid deploy and user registration**

```
$ node app.js 

chaincode already deployed, If not delete chaincodeID and keyValStore and recreate network

Get member JohnDoe

JohnDoe is available ... can create new users

completed chaincode invoke transaction: request={"chaincodeID":"6f8aeae4bf2c6135be8fd722362185c7c8e81f21c6e8c685aaabcb38175f2b89","fcn":"PostUser","args":["100","USER","Ashley Hart","TRD","Morrisville Parkway, #216, Morrisville, NC 27560","9198063535","ashley@itpeople.com","SUNTRUST","0001732345","0234678"]}, response={"result":"Tx a820be9d-b568-42ea-bac3-8310bc5819e8 complete"}

```

###Troubleshoot

If you see the below error, which means you would have started a new network 

```

Failed to submit chaincode invoke transaction: request={"chaincodeID":"6f8aeae4bf2c6135be8fd722362185c7c8e81f21c6e8c685aaabcb38175f2b89","fcn":"invoke","args":["a","b","10"]},":{"_internal_repr":{}}},"msg":"Error: sql: no rows in result set"}

```

To solve the problem you need to clean crypto secret keys generated under keyValStore folder and also chaincodeID
Below command should fix that for you

`$ node app.js --clean --all`

and then start the node program by issueing the below command

`$ node app.js`
