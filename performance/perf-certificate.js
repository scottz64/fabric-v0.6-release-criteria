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
 //    node perf-cert.js userInput-bluemix.json $GOPATH/src/github.com/chaincode_example02
 
var hfc = require('hfc');
var util = require('util');
var fs = require('fs');
const https = require('https');


// input from userinput.json
//var LPARId = parseInt(process.argv[2]);
var uiFile = process.argv[2];
var uiContent = JSON.parse(fs.readFileSync(uiFile));
console.log('uiFile=', uiFile);

// sanity check: transaction type
var transType = uiContent.transType;
if ((transType.toUpperCase() != 'QUERY') && (transType.toUpperCase() != 'INVOKE') ){
    console.log('invalid transaction type: %s', transType);
    process.exit();
}


//if (LPARId<=9999) { pad_pid = ("000"+LPARId).slice(-4); }
//pad_pid = ("000"+LPARId).slice(-4);
//console.log('LPARId=%d, pad_pid=', LPARId, pad_pid);
//var svcFile = 'SCFiles/ServiceCredentials'+pad_pid+'.json';
var svcFile = uiContent.SCFile[0].ServiceCredentials;
console.log('certificate file address source:', svcFile);

//process.exit();
var ccPath = process.argv[3];
//console.log('ccPath: %s', ccPath);


// Read and process the credentials.json
var network;
try {
    network = JSON.parse(fs.readFileSync(svcFile, 'utf8'));
} catch (err) {
    console.log('%s is missing, Rerun once the file is available', svcFile);
    process.exit();
}


var certFile = ccPath + '/certificate.pem';
var certUrl = network.credentials.cert;
fs.access(certFile, (err) => {
	
    if (!err) {
        console.log("\nDeleting existing certificate ", certFile);
        fs.unlinkSync(certFile);
    }
    downloadCertificate();
});

function downloadCertificate() {
	file = fs.createWriteStream(certFile);
    https.get(certUrl, function(res) {
        console.log('\nDownloading certificate file, %s, from %s', certFile, certUrl);
		//console.log('statusCode:', res.statusCode);
        //console.log('headers:', res.headers);
		if (res.statusCode !== 200) {
			console.log('\ndownload certificate failed = %s, error code = %d', certFile, res.statusCode);
           return null;
        }
		
		res.pipe(file);
        file.on('finish', () => {
			console.log('\n %s downloaded successfully', certFile);
        }).on('error', (err) => { // Handle errors
			console.error('\nerror in downloading certificate error = %s', err);
			process.exit();
        });

    });
}

