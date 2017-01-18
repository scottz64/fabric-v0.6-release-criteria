'use strict';
var fs = require('fs');
var hfc = require('hfc');
var myJson = require("./auction-NS.json");

var chain = hfc.newChain("testChain");
exports.chain = chain

exports.SN = function SetupNetwork(cb) {

   //for(var myKey in myJson) {
     //console.log("key:"+myKey+", value:"+myJson[myKey]);
   //}

   console.log("Before getting NS JSON properties")
   if (myJson.hasOwnProperty('MemberServices_URL')){
     chain.setMemberServicesUrl(myJson['MemberServices_URL']);
     //chain.setMemberServicesUrl(myJson['MemberServices_URL'], {pem:certFile});
     console.log("Member Services URL set successfully from JSON.")
   }else{
     console.log("Memeber Services URL not found in auction.json")
     throw Error("Memeber Services URL not found in auction.json");
   }

   if (myJson.hasOwnProperty('Peer0_URL')){
      //chain.addPeer(myJson['Peer0_URL'], {pem:certFile, hostnameOverride:'tlsca'});
      chain.addPeer(myJson['Peer0_URL']);
      console.log("Peer0 URL set successfully.")
   }else {
     console.log("PEER0 URL not found in auction.json")
     process.exit(1);
   }


   if (myJson.hasOwnProperty('Peer1_URL')){
      //chain.addPeer(myJson['Peer0_URL'], {pem:certFile, hostnameOverride:'tlsca'});
      chain.addPeer(myJson['Peer1_URL']);
      console.log("Peer1 URL set successfully.")
   }else {
     console.log("PEER1 URL not found in auction.json")
     process.exit(1);
   }

   if (myJson.hasOwnProperty('Peer2_URL')){
      //chain.addPeer(myJson['Peer0_URL'], {pem:certFile, hostnameOverride:'tlsca'});
      chain.addPeer(myJson['Peer2_URL']);
      console.log("Peer2 URL set successfully.")
   }else {
     console.log("PEER2 URL not found in auction.json")
     process.exit(1);
   }

   if (myJson.hasOwnProperty('Peer3_URL')){
      //chain.addPeer(myJson['Peer0_URL'], {pem:certFile, hostnameOverride:'tlsca'});
      chain.addPeer(myJson['Peer3_URL']);
      console.log("Peer3 URL set successfully.")
   }else {
     console.log("PEER3 URL not found in auction.json")
     process.exit(1);
   }

   if (myJson.hasOwnProperty('KeyVal_Store')){
     chain.setKeyValStore(hfc.newFileKeyValStore((myJson['KeyVal_Store'])));
     console.log("KeyVal Store set successfully.")

   }else{
     console.log("KeyVal Store not found in auction.json")
     process.exit(1);
   }

   console.log("initializing devMode to false...");
   chain.setDevMode(false);
}
