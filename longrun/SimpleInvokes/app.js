// Include the package from npm:
var hfc = require('hfc');
var util = require('util');
var fs = require('fs');


var config = JSON.parse(fs.readFileSync('config.json', 'utf8'));
var nTrans = 0;
var nFailed = 0;
var tStamp = 0;
var oFile = fs.createWriteStream('results.log');
var buff;


// Create a client chain.
var chain = hfc.newChain(config.chainName);

// Configure the KeyValStore which is used to store sensitive keys
// as so it is important to secure this storage.
var keyValStorePath = config.KeyValStore;
chain.setKeyValStore(hfc.newFileKeyValStore(keyValStorePath));

chain.setMemberServicesUrl(config.ca.ca_url);
for (var i = 0; i < config.peers.length; i++) {
    chain.addPeer(config.peers[i].peer_url);
}

var duration = parseInt(config.duration);
process.env['GOPATH'] = __dirname;
var chaincodeIDPath = __dirname + "/chaincodeID";
var deployerName = config.users[1].username;
var testChaincodeID;
var deployer;
if (process.argv.length == 4) {
    if (process.argv[2] == "--clean") {
        if (process.argv[3] == "chaincode" && fs.existsSync(chaincodeIDPath)) {
            fs.unlinkSync(chaincodeIDPath);
            console.log("Deleted chaincode ID , Ready to deploy chaincode ");
        } else if (process.argv[3] == "all") {
            if (fs.existsSync(chaincodeIDPath)) {
                fs.unlinkSync(chaincodeIDPath);
                console.log("Deleted the chaincode ID ...");
            }
            try {
                deleteDir(keyValStorePath);
                console.log("Deleted crypto keys , Create new network and Deploy chaincode ... ");
            } catch (err) {
                console.log(err);
            }
        }
    } else {
        console.log("Invalid arguments");
        console.log("USAGE: node app.js --clean [chaincode|all]");
        process.exit();
    }
    console.log("USAGE: node app.js");
    process.exit();
} else if (process.argv.length > 2) {
    console.log("Invalid arguments");
    console.log("USAGE: node app.js [--clean [chaincode|all]]");
    process.exit(2)
}

init();

function init() {
    // TODO: This is for testing purpose
    //duration = 10;
    var ms = duration * 60 * 1000 ;
    setTimeout(function() {
        console.log("Exiting the program ......");
        fs.appendFile('results.log', "\n ##### Completed " + duration + " hours, EXITING PROGRAM ###", function(err) {
            if (err) {
                return console.log(err);
            }
        });
        process.exit(2);
    }, ms);
    //Avoid enroll and deploy if chaincode already deployed
    if (!fileExists(chaincodeIDPath)) {
        registerAndEnrollUsers();
    } else {
        // Read chaincodeID and use this for sub sequent Invokes/Queries
        testChaincodeID = fs.readFileSync(chaincodeIDPath, 'utf8');
        console.log("\nchaincode already deployed, If not delete chaincodeID and keyValStore and recreate network");
        console.log("\nGet member %s", deployerName);
        chain.getUser(deployerName, function(err, member) {
            if (err) throw Error("Failed to register and enroll " + deployerName + ": " + err);
            deployer = member;
            console.log("\n%s is available ... can create new users\n", deployerName);
            invoke();
        });
    }
}

function registerAndEnrollUsers() {
    // Enroll "admin" which is already registered because it is
    // listed in fabric/membersrvc/membersrvc.yaml with it's one time password.
    chain.enroll(config.users[0].username, config.users[0].secret, function(err, admin) {
        if (err) throw Error(util.format("ERROR: failed to register %j, Error : %j \n", config.users[0].username, err));
        // Set this user as the chain's registrar which is authorized to register other users.
        chain.setRegistrar(admin);

        console.log("\nEnrolled %s successfully\n", config.users[0].username);

        // registrationRequest
        var registrationRequest = {
            enrollmentID: deployerName,
            affiliation: config.users[1].affiliation
        };
        chain.registerAndEnroll(registrationRequest, function(err, user) {
            if (err) throw Error(" Failed to register and enroll " + deployerName + ": " + err);
            deployer = user;
            console.log("Enrolled %s successfully\n", deployerName);
            //chain.setDeployWaitTime(config.deployWaitTime);
            deployChaincode();
        });
    });
}

function deployChaincode() {
    console.log(util.format("Deploying chaincode ... It will take about %j seconds to deploy \n", chain.getDeployWaitTime()))
    var args = getArgs(config.deployRequest);
    // Construct the deploy request
    var deployRequest = {
        chaincodePath: config.deployRequest.chaincodePath,
        // Function to trigger
        fcn: config.deployRequest.functionName,
        // Arguments to the initializing function
        args: args
    };

    // Trigger the deploy transaction
    var deployTx = deployer.deploy(deployRequest);

    // Print the deploy results
    deployTx.on('complete', function(results) {
        // Deploy request completed successfully
        testChaincodeID = results.chaincodeID;
        console.log(util.format("[ Chaincode ID : ", testChaincodeID + " ]\n"));
        console.log(util.format("Successfully deployed chaincode: request=%j, response=%j \n", deployRequest, results));
        fs.writeFileSync(chaincodeIDPath, testChaincodeID);

        invoke();
    });
    deployTx.on('error', function(err) {
        // Deploy request failed
        console.log(util.format("Failed to deploy chaincode: request=%j, error=%j \n", deployRequest, err));
    });
}


function invoke() {
    var args = getArgs(config.invokeRequest);
    // Construct the invoke request
    var invokeRequest = {
        // Name (hash) required for invoke
        chaincodeID: testChaincodeID,
        // Function to trigger
        fcn: config.invokeRequest.functionName,
        // Parameters for the invoke function
        args: args
    };

    // Trigger the invoke transaction
    var invokeTx = deployer.invoke(invokeRequest);

    nTrans++;
    tStamp = new Date().getTime();
    buff = 'tran#:' + nTrans + ' Failed:' + nFailed + ' time:' + tStamp + '\n';

    fs.appendFile('results.log', buff, function(err) {
        if (err) {
            return console.log(err);
        }
    })


    invokeTx.on('submitted', function(results) {
        // Invoke transaction completed?
        console.log(util.format("completed chaincode invoke submission: request=%j, response=%j\n", invokeRequest, results));
        setTimeout(function() {
            invoke();
        }, 1000);
    });
    invokeTx.on('error', function(err) {
        nFailed++;
        // Invoke transaction submission failed
        console.log(util.format("Failed to submit chaincode invoke transaction: request=%j, error=%j\n", invokeRequest, err));
        invoke();
    });
}


function fileExists(filePath) {
    try {
        return fs.statSync(filePath).isFile();
    } catch (err) {
        return false;
    }
}

function deleteDir(path) {
    try {
        if (fs.existsSync(path)) {
            fs.readdirSync(path).forEach(function(file, index) {
                fs.unlinkSync(path + "/" + file);
            });
            fs.rmdirSync(path);
        }
    } catch (err) {
        return err;
    }
};

function getArgs(request) {
    var args = [];
    for (var i = 0; i < request.args.length; i++) {
        args.push(request.args[i]);
    }
    return args;
}
