/**
 * Copyright 2016 IBM
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
/**
 * Licensed Materials - Property of IBM
 * © Copyright IBM Corp. 2016
 */
 
 // usage:
 //    node perf-main.js $LPARid $userinput $ccPath $tStart
 // example
 //    node perf-main.js 1 userInput-example02.json $GOPATH/src/github.com/chaincode_example02 1474310524632
 
var hfc = require('hfc');
var util = require('util');
var fs = require('fs');
const https = require('https');
const child_process = require('child_process');
var os = require('os');
console.log('perf-main: nCPUs=', os.cpus().length);


// input: userinput json file
var LPARid = parseInt(process.argv[2]);
var uiFile = process.argv[3];
var uiContent = JSON.parse(fs.readFileSync(uiFile));

var svcFile = uiContent.SCFile[LPARid].ServiceCredentials;
var ccPath = process.argv[4];
var tStart = parseInt(process.argv[5]);
var bcHost = process.argv[6];
console.log('LPAR=%d, svcFile:%s, ccPath:%s, bcHost:%s', LPARid, svcFile, ccPath, bcHost);

process.env['GOPATH'] = __dirname;
var chaincodeIDPath = __dirname + "/chaincodeID";

// Create a client blockchin.
var chainName = 'targetChain'+LPARid;
var chain = hfc.newChain(chainName);
//console.log('LPAR=%d, chain name ', LPARid, chainName);

// vars
var nThread=0;
var nRequest=0;
var rDur=0;
var t_end=0;
var testChaincodeID;
var ccType=uiContent.ccType;

// sanity check: transaction type
var transType = uiContent.transType;
if ((transType.toUpperCase() != 'QUERY') && (transType.toUpperCase() != 'INVOKE') && (transType.toUpperCase() != 'MIX')){
    console.log('LPAR=%d, invalid transaction type : %s', LPARid, transType);
    process.exit();
}
console.log('LPAR=%d, executing test: %s', LPARid, transType);

// input: nThread
if (uiContent.nThread) {
    nThread = parseInt(uiContent.nThread);
} else {
    console.log('LPAR=%d, nThread: cannot find in the user input file, default to 4', LPARid);
    nThread = 4;
}


// input: nRequest
if (uiContent.nRequest) {
    nRequest = parseInt(uiContent.nRequest);
} else {
    console.log('LPAR=%d, nRequest: not found in the user input file, default to 100', LPARid);
    nRequest = 100;
}


// input: rDur
if ( nRequest == 0 ) {
    if (uiContent.runDur) {
        rDur = parseInt(uiContent.runDur);
    } else {
        console.log('LPAR=%d, rDur: cannot find in the user input file, default to = 60 sec', LPARid);
        rDur = 60;
    }
}

// input: nPeers
if (uiContent.nPeers) {
    nPeers = parseInt(uiContent.nPeers);
} else {
    console.log('LPAR=%d, nPeers: not found in the user input file, default to 4', LPARid);
    nPeers = 4;
}

console.log('LPAR=%d, Peers=%d, Threads=%d, duration=%d sec, request=%d, ccType=%s', LPARid, nPeers, nThread, rDur, nRequest, ccType);

// Configure the KeyValStore which is used to store sensitive keys.
// This data needs to be located or accessible any time the users enrollmentID
// perform any functions on the blockchain.  The users are not usable without
// this data.
// Please ensure you have a /tmp directory prior to placing the keys there.
// If running on windows or mac please review the path setting.
//var keydir = '/tmp/keyValStore'+ LPARid;
var keydir = __dirname + '/keyValStore' + LPARid;
chain.setKeyValStore(hfc.newFileKeyValStore(keydir));
//console.log('LPAR=%d, keydir=%s', LPARid, keydir);

// Creating an environment variable for ciphersuites
process.env['GRPC_SSL_CIPHER_SUITES'] = 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES256-GCM-SHA384';


// Read and process the credentials.json
var network;
try {
    network = JSON.parse(fs.readFileSync(svcFile, 'utf8'));
} catch (err) {
    console.log('%s is missing, Rerun once the file is available', svcFile);
    process.exit();
}

var peers = network.credentials.peers;
var users = network.credentials.users;

// Determining if we are running on a startup or HSBN network based on the url
// of the discovery host name.  The HSBN will contain the string zone.
var isHSBN = peers[0].discovery_host.indexOf('zone') >= 0 ? true : false;
console.log('LPAR=%d, isHSBN:', LPARid, isHSBN);

var peerAddress = [];
var network_id = Object.keys(network.credentials.ca);
var ca_url = "grpc://" + network.credentials.ca[network_id].discovery_host + ":" + network.credentials.ca[network_id].discovery_port;
console.log('LPAR=%d, ca_url: %s', LPARid, ca_url);

if (!isHSBN) {
    //HSBN uses RSA generated keys
    chain.setECDSAModeForGRPC(true);
}


if ( bcHost == 'bluemix' ) {
    var certFile = ccPath + '/certificate.pem';
    var certUrl = network.credentials.cert;
}

setTimeout(function(){
    enrollAndRegisterUsers();
},1000);


function enrollAndRegisterUsers() {
    if ( bcHost == 'bluemix' ) {
        var cert = fs.readFileSync(certFile);
        chain.setMemberServicesUrl(ca_url, {
            pem: cert
        });

        // Adding all the peers to blockchain
        // this adds high availability for the client
        for (var i = 0; i < peers.length; i++) {
            chain.addPeer("grpcs://" + peers[i].discovery_host + ":" + peers[i].discovery_port, {
                pem: cert
            });
        }
    } else {
        chain.setMemberServicesUrl(ca_url);

        // Adding all the peers to blockchain
        // this adds high availability for the client
        for (var i = 0; i < peers.length; i++) {
            chain.addPeer("grpc://" + peers[i].discovery_host + ":" + peers[i].discovery_port);
        }
    }

    // Enroll a 'admin' who is already registered because it is
    // listed in fabric/membersrvc/membersrvc.yaml with it's one time password.
    //console.log('username=%s, secret=%s', users[0].username, users[0].secret);
    chain.enroll(users[0].username, users[0].secret, function(err, admin) {
        if (err) throw Error("\nLPAR=%d, ERROR: failed to enroll admin : %s", LPARid, err);

        console.log("\nLPAR=%d, Enrolled admin successfully", LPARid);

        // Set this user as the chain's registrar which is authorized to register other users.
        chain.setRegistrar(admin);

        var enrollName = "JohnDoe"; //creating a new user		
        var registrationRequest = {
            enrollmentID: enrollName,
            affiliation: "bank_a"
        };
        chain.registerAndEnroll(registrationRequest, function(err, user) {
            if (err) throw Error('LPAR=%d, Failed to register and enroll %s: %s', LPARid, enrollName, err);

            console.log('LPAR=%d, Enrolled and registered %s successfully', LPARid, enrollName);

            //setting timers for fabric waits
            chain.setDeployWaitTime(120);
            chain.setInvokeWaitTime(20);
            console.log('LPAR=%d, Deploying chaincode ...', LPARid)
            deployChaincode(user);
        });
    });
}

var testChaincodePath = uiContent.deploy.chaincodePath;
var testDeployArgs = uiContent.deploy.args.split(",");

function deployChaincode(user) {
    // Construct the deploy request
if ( bcHost == 'bluemix' ) {
    var deployRequest = {
	// chaincode path
	chaincodePath: testChaincodePath,
        // Function to trigger
        fcn: uiContent.deploy.fcn,
        // Arguments to the initializing function
        //args: ["a", "100", "b", "200"],
	args: testDeployArgs,
        // the location where the startup and HSBN store the certificates
        certificatePath: isHSBN ? "/root/" : "/certs/blockchain-cert.pem"
    };
} else {
    var deployRequest = {
	chaincodePath: testChaincodePath,
        fcn: uiContent.deploy.fcn,
	args: testDeployArgs
    };
}
    //deployRequest.chaincodePath = "github.com/chaincode_example02/";
	//deployRequest.chaincodePath = testChaincodePath;

    // Trigger the deploy transaction
    var deployTx = user.deploy(deployRequest);

    // Print the deploy results
    deployTx.on('complete', function(results) {
        // Deploy request completed successfully
        testChaincodeID = results.chaincodeID;
        //console.log('\nChaincode ID : ' + testChaincodeID);
        console.log(util.format("\nLPAR=%d, Successfully deployed chaincode: request=%j, response=%j", LPARid, deployRequest, results));
        //invokeOnUser(user);
		execTransactions(user);
    });

    deployTx.on('error', function(err) {
        // Deploy request failed
        console.log(util.format("\nLPAR=%d, Failed to deploy chaincode: request=%j, error=%j", LPARid, deployRequest, err));
    });
}


function execTransactions(user) {

        // init vars
        t_start = new Date().getTime();
        console.log('starting time (ms) =', t_start);

        // Start the transactions
        for (var i = 0; i < nThread; i++) {
	    var workerProcess = child_process.spawn('node', ['./perf-execRequest.js', LPARid, i, testChaincodeID, tStart, uiFile, bcHost ]);

/*
            if ( transType.toUpperCase() == 'MIX' ){
		    var workerProcess = child_process.spawn('node', ['./perf-execRequest-m1.js', LPARid, i, testChaincodeID, tStart, uiFile ]);
		    //var workerProcess = child_process.spawn('node', ['./perf-execRequest-mix.js', LPARid, i, testChaincodeID, tStart, uiFile ]);
		    //var workerProcess = child_process.spawn('node', ['./perf-execRequest.js', LPARid, i, testChaincodeID, tStart, uiFile, certFile ]);
		    //var workerProcess = child_process.spawn('node', ['./perf-execRequest-rate.js', LPARid, i, testChaincodeID, tStart, uiFile, certFile ]);
            } else {
		    var workerProcess = child_process.spawn('node', ['./perf-execRequest.js', LPARid, i, testChaincodeID, tStart, uiFile ]);
            }
*/

            workerProcess.stdout.on('data', function (data) {
               console.log('stdout: ' + data);
            });

            workerProcess.stderr.on('data', function (data) {
               console.log('stderr: ' + data);
            });

            workerProcess.on('close', function (code) {
               //console.log('child process exited with code ' + code);
            });

        }

}
