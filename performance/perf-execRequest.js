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

 //APIs
//var hfc = require('../..');
var hfc = require('hfc');
var util = require('util');
var fs = require('fs');
const crypto = require('crypto');

// input vars
var LPARid = parseInt(process.argv[2]);
var pid = parseInt(process.argv[3]);
var testChaincodeID = process.argv[4];
var tStart = parseInt(process.argv[5]);
var uiFile = process.argv[6];
var bcHost = process.argv[7];
//var certFile = process.argv[7];


process.env['GOPATH'] = __dirname;
var chaincodeIDPath = __dirname + "/chaincodeID";

// input: userinput json file
var uiContent = JSON.parse(fs.readFileSync(uiFile));
var svcFile = uiContent.SCFile[LPARid].ServiceCredentials;


// Read and process the service credentials
var network;
try {
    network = JSON.parse(fs.readFileSync(svcFile, 'utf8'));
} catch (err) {
    console.log('LPAR:id=%d:%d, ServiceCredentials.json is missing, Rerun once the file is available', LPARid, pid);
    process.exit();
}

var peers = network.credentials.peers;
var users = network.credentials.users;


// Determining if we are running on a starter or HSBN network based on the url
// of the discovery host name.  The HSBN will contain the string zone.
var isHSBN = peers[0].discovery_host.indexOf('zone') >= 0 ? true : false;
//console.log('LPAR:id=%d:%d, isHSBN:', LPARid, pid, isHSBN);
var peerAddress = [];
var network_id = Object.keys(network.credentials.ca);
var ca_url = "grpc://" + network.credentials.ca[network_id].discovery_host + ":" + network.credentials.ca[network_id].discovery_port;


/*
if (uiContent.DEBUG == "off" ) 
{
   var console = { log: function() {} }; 
}
*/

var transType = uiContent.transType;
var nThread=0;
var nRequest=0;
var rDur=0;
var tEnd=0;
var nPeers=0;
var TCertBatchSize=200;
var ccType;

// sanity check input transType
if ((transType.toUpperCase() != 'QUERY') && (transType.toUpperCase() != 'INVOKE') && (transType.toUpperCase() != 'MIX')){
    console.log('LPAR:id=%d:%d, process exit: invalid transaction requestion: %s', LPARid, pid, transType);
    process.exit();
}

// input: nThread
if (uiContent.nThread) {
    nThread = parseInt(uiContent.nThread);
} else {
    console.log('LPAR:id=%d:%d, nThread: not found in the user input file, set to default value 4', LPARid, pid);
    nThread = 4;
}


// input: nRequest
if (uiContent.nRequest) {
    nRequest = parseInt(uiContent.nRequest);
} else {
    console.log('LPAR:id=%d:%d, , nRequest: not found in the user input file, set to default value 100', LPARid, pid);
    nRequest = 100;
}


// input: rDur
if ( nRequest == 0 ) {
    if (uiContent.runDur) {
        rDur = parseInt(uiContent.runDur);
    } else {
        console.log('LPAR:id=%d:%d, duration: not found in the user input file, default to 60 sec', LPARid, pid);
        rDur = 60;
    }
}


// input: nPeers
if (uiContent.nPeers) {
    nPeers = parseInt(uiContent.nPeers);
} else {
    console.log('LPAR:id=%d:%d, , nRequest: not found in the user input file, default to 4', LPARid, pid);
    nPeers = 4;
}


// input: TCertBatchSize
if (uiContent.TCertBatchSize) {
    TCertBatchSize = parseInt(uiContent.TCertBatchSize);
} else {
    console.log('LPAR:id=%d:%d, TCertBatchSize: not found in the user input file, default to 200', LPARid, pid);
    TCertBatchSize = 200;
}

if (uiContent.ccType) {
    ccType = uiContent.ccType;
} else {
    console.log('LPAR=%d, ccType: not found in the user input file, default to others', LPARid);
    ccType = 'others';
}


console.log('LPAR:id=%d:%d, nPeers=%d, transaction=%s, duration=%d sec, time to start=%d, request #=%d, TCertBatchSize=%d, ccType=',
             LPARid, pid, nPeers, transType, rDur, tStart, nRequest, TCertBatchSize, ccType);

// Create a client blockchin.
var chainName = 'targetChain'+LPARid;
var chain = hfc.newChain(chainName);
//console.log('LPAR:id=%d:%d, chain name=%s ', LPARid, pid, chainName);

//setECDSAModeForGRPC
if (!isHSBN) {
    //HSBN uses RSA generated keys
    chain.setECDSAModeForGRPC(true)
}

//
// Set the directory for the local file-based key value store, point to the
// address of the membership service, and add an associated peer node.
var keydir = __dirname + '/keyValStore' + LPARid;
//console.log('LPAR:id=%d:%d,keydir: %s', LPARid, pid, keydir);
chain.setKeyValStore(hfc.newFileKeyValStore(keydir));
    if ( bcHost == 'bluemix' ) {
        var cert = fs.readFileSync(certFile);
        chain.setMemberServicesUrl(ca_url, {
            pem: cert
        });

	// Add peer to blockchain
	var idx = pid%nPeers;
	chain.addPeer("grpcs://" + peers[idx].discovery_host + ":" + peers[idx].discovery_port, {
            pem: cert
        });
    } else {
        chain.setMemberServicesUrl(ca_url);

	// Add peer to blockchain
	var idx = pid%nPeers;
	chain.addPeer("grpc://" + peers[idx].discovery_host + ":" + peers[idx].discovery_port);
    }


// local var for query/invoke test
    var tr_s = 0;      // transactions count: sent
    var tr_rs = 0;     // transactions count: received successfully
    var tr_re = 0;     // transactions count: received error
    var tLocal;
    var tCurr;
    var tr_sq = 0;      // transactions count: sent
    var tr_rsq = 0;     // transactions count: received successfully
    var tr_req = 0;     // transactions count: received error


// Configure test users
setTimeout(function(){
    enrollAndRegisterUsers();
},1000);

// Enroll "admin" which is already registered because it is
// listed in fabric/membersrvc/membersrvc.yaml with it's one time password.
function enrollAndRegisterUsers() {
    if ( bcHost == 'bluemix' ) {
        var cert = fs.readFileSync(certFile);
        chain.setMemberServicesUrl(ca_url, {
            pem: cert
        });
    } else {
        chain.setMemberServicesUrl(ca_url);
    }


    // Enroll a 'admin' who is already registered because it is
    // listed in fabric/membersrvc/membersrvc.yaml with it's one time password.
    chain.enroll(users[0].username, users[0].secret, function(err, admin) {
        if (err) throw Error("\nERROR: failed to enroll admin : %s", err);

        //console.log("\nLPAR:id=%d:%d, Enrolled admin sucecssfully", LPARid, pid);

        // Set this user as the chain's registrar which is authorized to register other users.
        chain.setRegistrar(admin);

        var enrollName = "JohnDoe_"+LPARid+"_"+pid; //creating a new user		
        var registrationRequest = {
            enrollmentID: enrollName,
            affiliation: "bank_a"
        };
        chain.registerAndEnroll(registrationRequest, function(err, user) {
            if (err) throw Error("pid=%d",pid," Failed to register and enroll " + enrollName + ": " + err);

		//console.log('LPAR:pid=%d:%d, Enrolled and registered %s successfully', LPARid, pid, enrollName);
            //begin transactions
		execTransaction(user);
        });
    });
}



// transaction arguments
// transaction id
var trid = pid*1000000;
var tridq= pid*1000000;
//var testQueryArgs = uiContent.query.args.split(",");
var testQueryArgs = [];
for (i=0; i<uiContent.query.args.length; i++) {
	testQueryArgs.push(uiContent.query.args[i]);
}
//var testInvokeArgs = uiContent.invoke.args.split(",");
var testInvokeArgs = [];
for (i=0; i<uiContent.invoke.args.length; i++) {
	testInvokeArgs.push(uiContent.invoke.args[i]);
}


function execTransaction(user) {

	tCurr = new Date().getTime();
	console.log('LPAR:id=%d:%d, execTransaction: tCurr= %d, tStart= %d, time to wait=%d', LPARid, pid, tCurr, tStart, tStart-tCurr);
	
	setTimeout(function() {
        if (transType.toUpperCase() == 'QUERY') {
            execQuery(user);
        } else if (transType.toUpperCase() == 'INVOKE') {
            execInvoke(user);
        } else if (transType.toUpperCase() == 'MIX') {
            execMix(user);
        } else {
            // invalid transaction request
            console.log(util.format("LPAR:id=%d:%d, Transaction %j invalid", LPARid, pid, transType));
            process.exit(1);
        }
	}, tStart-tCurr);
}


//
// Create and issue a chaincode query request by the test user, who was
// registered and enrolled in the UT above. Query an existing chaincode
// state variable with a transaction certificate batch size of 1.
//
        // Construct the invoke request
        var invokeRequest = {
            // Name (hash) required for invoke
            chaincodeID: testChaincodeID,
            // Function to trigger
            fcn: uiContent.invoke.fcn,
            // Parameters for the invoke function
            args: testInvokeArgs
        };

        // Construct the query request
        var queryRequest = {
            // Name (hash) required for query
            chaincodeID: testChaincodeID,
            // Function to trigger
            fcn: uiContent.query.fcn,
            // Existing state variable to retrieve
            args: testQueryArgs
            //args: ["a"]
        };

// send query transaction
function SendQuery(pid, user, request, callback) {

    tridq++;
    if ( ccType == 'auction' ) {
        request.args[0] = trid.toString();
    }
	//console.log('request: ', request);
    var queryTx = user.query(request);
    tr_sq++;

    // loop the query requests
    queryTx.on('complete', function (results) {
        // Query completed successfully
        tr_rsq++;

        tCurr = new Date().getTime();
        if ( nRequest > 0 ) {
            if ( ((tr_rsq+tr_req) % (nRequest/5)) == 0) {
                console.log(util.format("LPAR:id=%d:%d, Successfully queried chaincode: value=%s, number=%d, time= %d, elapsed= %d",
                                         LPARid, pid, results.result.toString(), tr_rsq, tCurr, tCurr-tLocal));
            }

            if ( (tr_rsq+tr_req) >= nRequest ) {
                QDone = 1;
            }
        } else {
            if ( ((tr_rsq+tr_req) % 1000 ) == 0) {
                console.log(util.format("LPAR:id=%d:%d, Successfully queried chaincode: value=%s, number=%d, time= %d, elapsed= %d",
                                         LPARid, pid, results.result.toString(), tr_rsq, tCurr, tCurr-tLocal));
            }

            if ( tCurr >= tEnd ) {
                QDone = 1;
            }
        }

        if ( QDone == 1 ) {
            console.log(util.format("SendQuery:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                     LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
        } else {
            SendQuery(pid, user, request, null) 
        };

    });
    queryTx.on('error', function (err) {
            // Query failed
            tr_req++;
            tCurr = new Date().getTime();
            console.log(util.format("LPAR:id=%d:%d, Failed to query chaincode: f/s= %d/%d, elapsed time= %d error=%j",
                                     LPARid, pid, tr_req, tr_rsq, tCurr-tLocal, err));
            if ( nRequest > 0 ) {
                if ( (tr_rsq+tr_req) >= nRequest ) {
                    QDone = 1;
                }
            } else if ( tCurr >= tEnd ) {
                QDone = 1;
            }

            if ( QDone == 1 ) {
                console.log(util.format("SendQuery:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else {
                SendQuery(pid, user, request, null) 
            };
    });
}

function execQuery(user) {

        // init TcertBatchSize
        user.setTCertBatchSize(TCertBatchSize);

        // get time
        tLocal = new Date().getTime();

        if ( nRequest == 0 ) {
            tEnd = tLocal + rDur * 1000;
            console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
            SendQuery(pid, user, queryRequest, null);
        } else {
            console.log('LPAR:id=%d:%d, local time(ms) starting= %d', LPARid, pid, tLocal);
            SendQuery(pid, user, queryRequest, null);
        }

}


//
// issue a chaincode invoke request
//
var buf;
var i = 0;
function SendInvoke(pid, user, request, callback) {

    // Trigger the invoke transaction
    var requestLoc = invokeRequest;
    trid++;

    if (ccType == 'auction') {
        request.args[0] = trid.toString();
	
	// random payload: 1kb - 2kb
	min = 512;
	max = 1024;
	r = Math.floor(Math.random() * (max - min)) + min;
	//r = 512;
		
	buf = crypto.randomBytes(r);
	request.args[4] = buf.toString('hex');
    }
	
	//console.log('request: ', request);
    var invokeTx = user.invoke(request);
	tr_s++;

    // Print the invoke results
    invokeTx.on('submitted', function (results) {

            tr_rs++;
            tCurr = new Date().getTime();
            if ( nRequest > 0 ) {
                if ( (tr_rs % (nRequest/5)) == 0) {
                    console.log("LPAR:id=%d:%d, Successfully submitted chaincode invoke transaction: number=%d, time= %d, elapsed= %d",
			             LPARid, pid, tr_rs, tCurr, tCurr-tLocal);
                }

                if ( (tr_rs+tr_re) >= nRequest ) {
                    IDone = 1;
                }
            } else {
                if ( (tr_rs % 1000 ) == 0) {
                    console.log("LPAR:id=%d:%d, Successfully completed chaincode invoke transaction: number=%d, time= %d, elapsed= %d",
                                             LPARid, pid, tr_rs, tCurr, tCurr-tLocal);
                }

                if ( tCurr >= tEnd ) {
                    IDone = 1;
                }
            }

            if (IDone == 1) {
                console.log(util.format("SendInvoke:LPAR:id=%d:%d, Invoke test completed: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                     LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            } else {
                SendInvoke(pid, user, request, null) 
            };

    });
    invokeTx.on('error', function (err) {
            // invoke failed
            tr_re++;
            tCurr = new Date().getTime();
            console.log(util.format("LPAR:id=%d:%d, Failed to submit chaincode invoke transaction: number=%d, time= %d, elapsed= %d, error=%j",
                                             LPARid, pid, tr_re, tCurr, tCurr-tLocal, err));
            if ( nRequest > 0 ) {
                if ( (tr_rs+tr_re) >= nRequest ) {
                    IDone = 1;
                }
            } else if ( tCurr >= tEnd ) {
                    IDone = 1;
            }

            if (IDone == 1) {
                console.log(util.format("SendInvoke:LPAR:id=%d:%d, Invoke test completed: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                         LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            } else {
                SendInvoke(pid, user, request, null) 
            };
    });
};


function execInvoke(user) {

        // init TcertBatchSize
        user.setTCertBatchSize(TCertBatchSize);
		
	console.log('invoke:',invokeRequest);

        // get time
        tLocal = new Date().getTime();

        // Start the invoke transactions
       	    if ( nRequest == 0 ) {
                tEnd = tLocal + rDur * 1000;
                console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
                SendInvoke(pid, user, invokeRequest, null);
            } else {
                console.log('LPAR:id=%d:%d, local time(ms) starting= %d', LPARid, pid, tLocal);
                SendInvoke(pid, user, invokeRequest, null);
            }

}


// exec MIX
var IDone = 0;
var QDone = 0;
function SendMix(pid, user, mix, callback) {

    if ( mix == 'invoke' ) {
        // Trigger the invoke transaction
        var requestLoc = invokeRequest;
	trid++;

        if (ccType == 'auction') {
            requestLoc.args[0] = trid.toString();

	    // random payload: 1kb - 2kb
	    //min = 512;
	    //max = 1024;
	    min = 5120;
	    max = 256000;
	    r = Math.floor(Math.random() * (max - min)) + min;
	    //r = 512;

	    buf = crypto.randomBytes(r);
	    requestLoc.args[4] = buf.toString('hex');
        }


        //console.log('request: ', request);
        var invokeTx = user.invoke(requestLoc);
	tr_s++;

        // Print the invoke results
        invokeTx.on('submitted', function (results) {
//        invokeTx.on('complete', function (results) {
            // Invoke completed successfully
            tr_rs++;
	    tCurr = new Date().getTime();
            if ( nRequest > 0 ) {
                if ( (tr_rs % (nRequest/5)) == 0) {
                    console.log("LPAR:id=%d:%d, Successfully completed chaincode invoke transaction: number=%d, time= %d, elapsed= %d",
			                     LPARid, pid, tr_rs, tCurr, tCurr-tLocal);
                }

                if ( (tr_rs+tr_re) >= nRequest ) { 
                    IDone = 1;
                }
            } else {
                if ( (tr_rs % 1000 ) == 0) {
                    console.log("LPAR:id=%d:%d, Successfully completed chaincode invoke transaction: number=%d, time= %d, elapsed= %d",
			                     LPARid, pid, tr_rs, tCurr, tCurr-tLocal);
                }

                if ( tCurr >= tEnd ) { 
                    IDone = 1;
                }
            }

            if ( (IDone == 1) && (QDone == 1) ) {
                console.log(util.format("SendMix:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                         LPARid, pid, tr_s, tr_rs, tr_re, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else { 
                setTimeout(function(){
                    SendMix(pid, user, 'query', null) 
                },nFreq);
            };
        });
        invokeTx.on('error', function (err) {
            // invoke failed
            tr_re++;
            tCurr = new Date().getTime();
            console.log(util.format("LPAR:id=%d:%d, Failed to submit chaincode invoke transaction: number=%d, time= %d, elapsed= %d, error=%j",
		                             LPARid, pid, tr_re, tCurr, tCurr-tLocal, err));
            if ( nRequest > 0 ) {
                if ( (tr_rs+tr_re) >= nRequest ) { 
                    IDone = 1;
                }
            } else if ( tCurr >= tEnd ) { 
                    IDone = 1;
            }

            if ( (IDone == 1) && (QDone == 1) ) {
                console.log(util.format("SendMix:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                         LPARid, pid, tr_s, tr_rs, tr_re, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else { 
                setTimeout(function(){
                    SendMix(pid, user, 'query', null) 
                },nFreq);
            };
        });
    } else if ( mix == 'query' ) {
        tridq++;
        var t0 = pid*1000000+1;
        var requestLoc = queryRequest;
        if (ccType == 'auction') {
            requestLoc.args[0] = t0.toString();
        }
        //console.log('request: ', request);
        var queryTx = user.query(requestLoc);
        tr_sq++;

        // loop the query requests
        queryTx.on('complete', function (results) {
            // Query completed successfully
            tr_rsq++;

            if ( nRequest > 0 ) {
                if ( ((tr_rsq+tr_req) % (nRequest/5)) == 0) {
                    tCurr = new Date().getTime();
                    console.log(util.format("LPAR:id=%d:%d, Successfully queried chaincode: value=%s, tridq=%d, number=%d, time= %d, elapsed= %d", 
                                         LPARid, pid, results.result.toString(), tridq, tr_rsq, tCurr, tCurr-tLocal));
                }

                if ( (tr_rs+tr_re) >= nRequest ) { 
                    QDone = 1;
                }
            } else if ( tCurr >= tEnd ) { 
                QDone = 1;
            }

            if ( (IDone == 1) && (QDone == 1) ) {
                console.log(util.format("SendMix:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                         LPARid, pid, tr_s, tr_rs, tr_re, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else { 
                SendMix(pid, user, 'invoke', null); 
            };
        });
        queryTx.on('error', function (err) {
            // Query failed
            tr_req++;
            tCurr = new Date().getTime();
		    console.log(util.format("LPAR:id=%d:%d, Failed to query chaincode: f/s= %d/%d, elapsed time= %d error=%j",
		                             LPARid, pid, tr_req, tr_rsq, tCurr-tLocal, err));
            if ( nRequest > 0 ) {
                if ( (tr_rs+tr_re) >= nRequest ) { 
                    QDone = 1;
                }
            } else if ( tCurr >= tEnd ) { 
                QDone = 1;
            }

            if ( (IDone == 1) && (QDone == 1) ) {
                console.log(util.format("SendMix:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                         LPARid, pid, tr_s, tr_rs, tr_re, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else { 
                SendMix(pid, user, 'invoke', null) ;
            };
        });
    }
};

var nFreq = 3000;
function execMix(user) {

        // init TcertBatchSize
        user.setTCertBatchSize(TCertBatchSize);
        if (uiContent.nFreq) {
            nFreq = parseInt(uiContent.nFreq);
        } else {
            nFreq = 3000;
        }

	console.log('Mix nFreq:',nFreq);
	console.log('invoke:',invokeRequest);

        // get time
        tLocal = new Date().getTime();

        // Start transactions
  	if ( nRequest == 0 ) {
            tEnd = tLocal + rDur * 1000;
            console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
            SendMix(pid, user, 'invoke', null);
        } else {
            console.log('LPAR:id=%d:%d, local time(ms) starting= %d', LPARid, pid, tLocal);
            SendMix(pid, user, 'invoke', null);
        }
}
