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
var user;


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
var transMode = uiContent.transMode;
var nThread=0;
var nRequest=0;
var runDur=0;
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


// input: runDur
if (uiContent.runDur) {
    runDur = parseInt(uiContent.runDur);
} else {
    console.log('LPAR:id=%d:%d, duration: not found in the user input file, default to 60 sec', LPARid, pid);
    runDur = 60;
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
             LPARid, pid, nPeers, transType, runDur, tStart, nRequest, TCertBatchSize, ccType);

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
    // setMemberServicesUrl
    if ( bcHost == 'bluemix' ) {
        var cert = fs.readFileSync(certFile);
        chain.setMemberServicesUrl(ca_url, {
            pem: cert
        });
    } else {
        chain.setMemberServicesUrl(ca_url);
    }


    // getUser or enroll
    if (testChaincodeID != 0) {
        chain.getUser(users[0].username, function(err, member) {
            if (err) throw Error("Failed to register and enroll " + users[0].username + ": " + err);

            user = member;
            execTransMode(user);
        });
    } else {
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
                affiliation: users[0].affiliation
            };
            chain.registerAndEnroll(registrationRequest, function(err, user) {
                if (err) throw Error("pid=%d",pid," Failed to register and enroll " + enrollName + ": " + err);

		//console.log('LPAR:pid=%d:%d, Enrolled and registered %s successfully', LPARid, pid, enrollName);
                //begin transactions
		execTransMode(user);
            });
        });
    }
}



// transaction arguments
// transaction id
var keyStart
if ( ccType == 'auction' )
    keyStart = parseInt(uiContent.auctionKey);
else {
   keyStart = 0;
}
var trid = pid*1000000 + keyStart;
var tridq= pid*1000000 + keyStart;
console.log('LPAR:id=%d:%d, keyStart=%d trid=%d, tridq=%d', LPARid, pid, keyStart, trid, tridq);

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


function execTransMode(user) {

	tCurr = new Date().getTime();
	console.log('LPAR:id=%d:%d, execTransMode: tCurr= %d, tStart= %d, time to wait=%d', LPARid, pid, tCurr, tStart, tStart-tCurr);
	
	setTimeout(function() {
            if (transMode.toUpperCase() == 'SIMPLE') {
                execModeSimple(user);
            } else if (transMode.toUpperCase() == 'CONSTANT') {
                execModeConstant(user);
            } else if (transMode.toUpperCase() == 'MIX') {
                execModeMix(user);
            } else if (transMode.toUpperCase() == 'BURST') {
                execModeBurst(user);
            } else {
                // invalid transaction request
                console.log(util.format("LPAR:id=%d:%d, Transaction %j and/or mode %s invalid", LPARid, pid, transType, transMode));
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

function isExecDone(trType) {

    tCurr = new Date().getTime();
    if ( trType.toUpperCase() == 'INVOKE' ) {
        if ( nRequest > 0 ) {
            if ( (tr_s % (nRequest/5)) == 0) {
                console.log(util.format("LPAR:id=%d:%d, invokes sent: number=%d, elapsed time= %d",
                                         LPARid, pid, tr_s, tCurr-tLocal));
            }

            if ( tr_s >= nRequest ) {
                IDone = 1;
            }
        } else {
            if ( (tr_s % 1000 ) == 0) {
                console.log(util.format("LPAR:id=%d:%d, invokes sent: number=%d, elapsed time= %d",
                                         LPARid, pid, tr_s, tCurr-tLocal));
            }

            if ( tCurr >= tEnd ) {
                IDone = 1;
            }
        }
    } else if ( trType.toUpperCase() == 'QUERY' ) {
        if ( nRequest > 0 ) {
            if ( (tr_sq % (nRequest/5)) == 0) {
                console.log(util.format("LPAR:id=%d:%d, queries sent: number=%d, elapsed time= %d",
                                         LPARid, pid, tr_sq, tCurr-tLocal));
            }

            if ( tr_sq >= nRequest ) {
                QDone = 1;
            }
        } else {
            if ( (tr_sq % 1000 ) == 0) {
                console.log(util.format("LPAR:id=%d:%d, queries sent: number=%d, elapsed time= %d",
                                         LPARid, pid, tr_sq, tCurr-tLocal));
            }

            if ( tCurr >= tEnd ) {
                QDone = 1;
            }
        }
    }
}



//
// issue a chaincode invoke request
//
var buf;
var i = 0;
function SendSimple(pid, user, trType, callback) {

    if ( trType == 'INVOKE' ) {
        // Trigger the invoke transaction
        var requestLoc = invokeRequest;
        trid++;

        if (ccType == 'auction') {
            requestLoc.args[0] = trid.toString();

            // random payload: 1kb - 2kb
	    min = 512;
	    max = 1024;
	    r = Math.floor(Math.random() * (max - min)) + min;

	    buf = crypto.randomBytes(r);
	    requestLoc.args[4] = buf.toString('hex');
        }

        //console.log('request: ', request);
        var invokeTx = user.invoke(requestLoc);
        tr_s++;
        isExecDone('INVOKE');
//         console.log('LPAR:id=%d:%d, invoke: tCurr= %d', LPARid, pid, tCurr);

        // Print the invoke results
        invokeTx.on('submitted', function (results) {

            tr_rs++;

            if (IDone == 1) {
                console.log(util.format("SendInvoke:LPAR:id=%d:%d, Invoke test completed: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                     LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            } else {
                SendSimple(pid, user, trType, null);
            };

        });
        invokeTx.on('error', function (err) {
            // invoke failed
            tr_re++;
            console.log(util.format("LPAR:id=%d:%d, Failed to submit chaincode invoke transaction: number=%d, time= %d, elapsed= %d, error=%j",
                                             LPARid, pid, tr_re, tCurr, tCurr-tLocal, err));

            if (IDone == 1) {
                console.log(util.format("SendInvoke:LPAR:id=%d:%d, Invoke test completed: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d", 
                                         LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            } else {
                SendSimple(pid, user, trType, null);
            };
        });
    } else if ( trType == 'QUERY' ) {
        tridq++;
        var requestLoc = queryRequest;
        if ( ccType == 'auction' ) {
            requestLoc.args[0] = tridq.toString();
        }
	//console.log('request: ', request);
        var queryTx = user.query(requestLoc);
        tr_sq++;
        isExecDone('QUERY');

        // loop the query requests
        queryTx.on('complete', function (results) {
            // Query completed successfully
            tr_rsq++;

            if ( QDone == 1 ) {
//                console.log(util.format("LPAR:id=%d:%d, Successfully queried chaincode: value=%s, number=%d, time= %d, elapsed= %d",
//                                     LPARid, pid, results.result.toString(), tr_rsq, tCurr, tCurr-tLocal));
                console.log(util.format("SendQuery:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                     LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else {
                SendSimple(pid, user, trType, null);
            };

        });
        queryTx.on('error', function (err) {
            // Query failed
            tr_req++;
            console.log(util.format("LPAR:id=%d:%d, Failed to query chaincode: f/s= %d/%d, elapsed time= %d error=%j",
                                     LPARid, pid, tr_req, tr_rsq, tCurr-tLocal, err));

            if ( QDone == 1 ) {
                console.log(util.format("SendQuery:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else {
                SendSimple(pid, user, trType, null);
            };
        });
    }
};


function execModeSimple(user) {

        // init TcertBatchSize
        user.setTCertBatchSize(TCertBatchSize);

        console.log('LPAR:id=%d:%d, execModeSimple: %s', LPARid, pid, transType);
        // get time
        tLocal = new Date().getTime();

        // Start the transactions
       	    if ( nRequest == 0 ) {
                tEnd = tLocal + runDur * 1000;
                console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
            } else {
                console.log('LPAR:id=%d:%d, local time(ms) starting= %d', LPARid, pid, tLocal);
            }
            SendSimple(pid, user, transType.toUpperCase(), null);

}


// exec MIX
var IDone = 0;
var QDone = 0;
function SendMix(pid, user, mix, callback) {

//    tCurr = new Date().getTime();
//    console.log('tCurr=%d mix=%s', tCurr, mix);

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

        var invokeTx = user.invoke(requestLoc);
        tr_s++;
        isExecDone(mix.toUpperCase());

        // Print the invoke results
        invokeTx.on('submitted', function (results) {
            // Invoke completed successfully
            tr_rs++;

            if ( (IDone == 1) && (QDone == 1) ) {
                console.log(util.format("SendMix:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_s, tr_rs, tr_re, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else {
                setTimeout(function(){
                    SendMix(pid, user, 'query', null);
                },mixFreq);
            };
        });
        invokeTx.on('error', function (err) {
            // invoke failed
            tr_re++;
            console.log(util.format("LPAR:id=%d:%d, Failed to submit chaincode invoke transaction: number=%d, time= %d, elapsed= %d, error=%j",
                                     LPARid, pid, tr_re, tCurr, tCurr-tLocal, err));

            if ( (IDone == 1) && (QDone == 1) ) {
                console.log(util.format("SendMix:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_s, tr_rs, tr_re, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else {
                setTimeout(function(){
                    SendMix(pid, user, 'query', null);
                },mixFreq);
            };
        });
    } else if ( mix == 'query' ) {
        tridq++;
        var requestLoc = queryRequest;
        if (ccType == 'auction') {
            var t0 = pid*1000000+1;
            requestLoc.args[0] = t0.toString();
        }

        var queryTx = user.query(requestLoc);
        tr_sq++;
        isExecDone(mix.toUpperCase());

        // loop the query requests
        queryTx.on('complete', function (results) {
            // Query completed successfully
            tr_rsq++;

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
            console.log(util.format("LPAR:id=%d:%d, Failed to query chaincode: f/s= %d/%d, elapsed time= %d error=%j",
                                     LPARid, pid, tr_req, tr_rsq, tCurr-tLocal, err));

            if ( (IDone == 1) && (QDone == 1) ) {
                console.log(util.format("SendMix:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_s, tr_rs, tr_re, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            } else { 
                SendMix(pid, user, 'invoke', null) ;
            };
        });
    }
};

var mixFreq = 3000;
function execModeMix(user) {

        // init TcertBatchSize
        user.setTCertBatchSize(TCertBatchSize);
        if (uiContent.Mix.mixFreq) {
            mixFreq = parseInt(uiContent.Mix.mixFreq);
        } else {
            mixFreq = 3000;
        }

	console.log('LPAR:id=%d:%d, Mix mixFreq: %s ms', LPARid, pid, mixFreq);

        // get time
        tLocal = new Date().getTime();

        // Start transactions
  	if ( nRequest == 0 ) {
            tEnd = tLocal + runDur * 1000;
            console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
        } else {
            console.log('LPAR:id=%d:%d, local time(ms) starting= %d', LPARid, pid, tLocal);
        }
        SendMix(pid, user, 'invoke', null);
}

// Burst traffic
// Burst traffic vars
var burstFreq0;
var burstDur0;
var burstFreq1;
var burstDur1;
var tDur=[];
var tFreq=[];
var tUpd0;
var tUpd1;
var Freq;

function SendBurst(pid, user, trType, callback) {

    tCurr = new Date().getTime();

    // set up burst traffic duration and frequency
    if ( tCurr < tUpd0 ) {
        Freq = tFreq[0];
    } else if ( tCurr < tUpd1 ) {
        Freq = tFreq[1];
    } else {
        tUpd0 = tCurr + tDur[0];
        tUpd1 = tUpd0 + tDur[1];
        Freq = tFreq[0];
    }
//    console.log ('LPAR:id=%d:%d trType=%s, tCurr=%d tUpd0=%d, tUpd1=%d, Freq=%d', LPARid, pid, trType, tCurr, tUpd0, tUpd1, Freq);

    // start transaction
    if ( trType == 'INVOKE' ) {
        // Trigger the invoke transaction
        var requestLoc = invokeRequest;
	trid++;

        if (ccType == 'auction') {
            requestLoc.args[0] = trid.toString();

	    // random payload: 1kb - 2kb
	    min = 512;
	    max = 1024;
	    //min = 5120;
	    //max = 256000;
	    r = Math.floor(Math.random() * (max - min)) + min;
	    //r = 512;

	    buf = crypto.randomBytes(r);
	    requestLoc.args[4] = buf.toString('hex');
        }

        var invokeTx = user.invoke(requestLoc);
        tr_s++;
        isExecDone(trType);

        // schedule invoke
        if ( IDone != 1 ) {
            setTimeout(function() {
                SendBurst(pid, user, trType, null);
            }, Freq);
        }

        // Print the invoke results
        invokeTx.on('submitted', function (results) {
            // Invoke completed successfully
            tr_rs++;

            if ( IDone == 1 ) {
                console.log(util.format("SendBurst:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            };
        });
        invokeTx.on('error', function (err) {
            // invoke failed
            tr_re++;
            console.log(util.format("LPAR:id=%d:%d, Failed to submit chaincode invoke transaction: number=%d, time= %d, elapsed= %d, error=%j",
                                     LPARid, pid, tr_re, tCurr, tCurr-tLocal, err));

            if ( IDone == 1 ) {
                console.log(util.format("SendBurst:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            };
        });
    } else if ( trType == 'QUERY' ) {
        tridq++;
        var requestLoc = queryRequest;
        if (ccType == 'auction') {
            var t0 = pid*1000000+1;
            requestLoc.args[0] = t0.toString();
        }
        //console.log('request: ', request);
        var queryTx = user.query(requestLoc);
        tr_sq++;
        isExecDone(trType);

        // schedule query
        if ( QDone != 1 ) {
            setTimeout(function() {
                SendBurst(pid, user, trType, null);
            }, Freq);
        }

        // loop the query requests
        queryTx.on('complete', function (results) {
            // Query completed successfully
            tr_rsq++;

            if ( QDone == 1 ) {
                console.log(util.format("SendBurst:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            };
        });
        queryTx.on('error', function (err) {
            // Query failed
            tr_req++;
            console.log(util.format("LPAR:id=%d:%d, Failed to query chaincode: f/s= %d/%d, elapsed time= %d error=%j",
                                     LPARid, pid, tr_req, tr_rsq, tCurr-tLocal, err));

            if ( QDone == 1 ) {
                console.log(util.format("SendBurst:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            };
        });
    }
};


function execModeBurst(user) {

    // init TcertBatchSize
    user.setTCertBatchSize(TCertBatchSize);
    burstFreq0 = parseInt(uiContent.Burst.burstFreq0);
    burstDur0 = parseInt(uiContent.Burst.burstDur0);
    burstFreq1 = parseInt(uiContent.Burst.burstFreq1);
    burstDur1 = parseInt(uiContent.Burst.burstDur1);
    tFreq = [burstFreq0, burstFreq1];
    tDur  = [burstDur0, burstDur1];

    console.log('LPAR:id=%d:%d, Burst setting: tDur =',LPARid, pid, tDur);
    console.log('LPAR:id=%d:%d, Burst setting: tFreq=',LPARid, pid, tFreq);

    // get time
    tLocal = new Date().getTime();

    tUpd0 = tLocal+tDur[0];
    tUpd1 = tLocal+tDur[1];
    Freq = tFreq[0];

    // Start transactions
    if ( nRequest == 0 ) {
        tEnd = tLocal + runDur * 1000;
        console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
    } else {
        tEnd = tLocal + runDur * 1000;
        console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
    }
    SendBurst(pid, user, transType.toUpperCase(), null);
}


// fix rate
var recHist;
var constFreq;
var ofile;
function SendConstant(pid, user, trType, callback) {

//    tCurr = new Date().getTime();
//    console.log('tCurr=%d mix=%s', tCurr, mix);

    tCurr = new Date().getTime();
    //console.log('LPAR:id=%d:%d, SendConstant: trType=%s, timestamp=%d', LPARid, pid, trType, tCurr);

    if ( trType == 'INVOKE' ) {
        // Trigger the invoke transaction
        var requestLoc = invokeRequest;
	trid++;

        if (ccType == 'auction') {
            requestLoc.args[0] = trid.toString();

	    // random payload: 1kb - 2kb
	    min = 512;
	    max = 1024;
	    //min = 5120;
	    //max = 256000;
	    r = Math.floor(Math.random() * (max - min)) + min;
	    //r = 512;

	    buf = crypto.randomBytes(r);
	    requestLoc.args[4] = buf.toString('hex');
        }

        var invokeTx = user.invoke(requestLoc);
	tr_s++;

        // output
        if ( recHist == 'HIST' ) {
            buff = LPARid +':'+ pid + ' ' + trType[0] + ':' + tr_s + ' Failed:' + tr_re + ' time:'+ tCurr + '\n';
            fs.appendFile(ofile, buff, function(err) {
                if (err) {
                   return console.log(err);
                }
            })
        }

            isExecDone(trType);

            if ( IDone != 1 ) {
                setTimeout(function(){
                    SendConstant(pid, user, trType, null);
                },constFreq);
            };

        // Print the invoke results
        invokeTx.on('submitted', function (results) {
            // Invoke completed successfully
            tr_rs++;
            if ( IDone == 1 ) {
                console.log(util.format("SendConstant:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            }
        });
        invokeTx.on('error', function (err) {
            // invoke failed
            tr_re++;
            console.log(util.format("LPAR:id=%d:%d, Failed to submit chaincode invoke transaction: number=%d, time= %d, elapsed= %d, error=%j",
                                     LPARid, pid, tr_re, tCurr, tCurr-tLocal, err));
            if ( IDone == 1 ) {
                console.log(util.format("SendConstant:LPAR:id=%d:%d, Invoke: total= %d submitted= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_s, tr_rs, tr_re, tLocal, tCurr, tCurr-tLocal));
            }
        });
    } else if ( trType == 'QUERY' ) {
        tridq++;
        var requestLoc = queryRequest;
        if (ccType == 'auction') {
            var t0 = pid*1000000+1;
            requestLoc.args[0] = t0.toString();
        }

        var queryTx = user.query(requestLoc);
        tr_sq++;

        // output
        if ( recHist == 'HIST' ) {
            buff = LPARid +':'+ pid + ' ' + trType[0] + ':' + tr_sq + ' Failed:' + tr_req + ' time:'+ tCurr + '\n';
            fs.appendFile(ofile, buff, function(err) {
                if (err) {
                   return console.log(err);
                }
            })
        }

            isExecDone(trType);

            if ( QDone != 1 ) {
                setTimeout(function(){
                    SendConstant(pid, user, trType, null);
                },constFreq);
            };
        // loop the query requests
        queryTx.on('complete', function (results) {
            // Query completed successfully
            tr_rsq++;
            if ( QDone == 1 ) {
                console.log(util.format("SendConstant:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            }
        });
        queryTx.on('error', function (err) {
            // Query failed
            tr_req++;
            if ( QDone == 1 ) {
                console.log(util.format("SendConstant:LPAR:id=%d:%d, Query: total= %d completed= %d failed= %d time(ms): starting= %d ending= %d elapsed= %d",
                                         LPARid, pid, tr_sq, tr_rsq, tr_req, tLocal, tCurr, tCurr-tLocal));
            }
        });
    }
};

function execModeConstant(user) {

        // init TcertBatchSize
        user.setTCertBatchSize(TCertBatchSize);

        if (uiContent.Constant.recHist) {
            recHist = uiContent.Constant.recHist.toUpperCase();
        }

        if (uiContent.Constant.constFreq) {
            constFreq = parseInt(uiContent.Constant.constFreq);
        } else {
            constFreq = 1000;
        }

        ofile = 'ConstantResults'+LPARid+'.txt';
        //var ConstantFile = fs.createWriteStream('ConstantResults.txt');
        console.log('LPAR:id=%d:%d, Constant Freq: %d ms', LPARid, pid, constFreq);

        // get time
        tLocal = new Date().getTime();

        // Start transactions
        if ( nRequest == 0 ) {
            tEnd = tLocal + runDur * 1000;
            console.log('LPAR:id=%d:%d, transactions start= %d, ending= %d', LPARid, pid, tLocal, tEnd);
        } else {
            console.log('LPAR:id=%d:%d, local time(ms) starting= %d', LPARid, pid, tLocal);
        }
        SendConstant(pid, user, transType.toUpperCase(), null);
}
