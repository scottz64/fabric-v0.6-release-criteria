'use strict';
var hfc = require('hfc')
var util = require('util');
var crypto = require('crypto');

var AuctionChainCalls = require('./auction-CC.js').ACC;
var UsersJson = require("./auction-Users-CC.json");
var NS = require('./auction-NS.js');
var myChain = NS.chain;

var chain, chaincodeID;
var mrseller;
var mrsellerAppCert
var devMode

var adminName, adminSecret, user1Name, user1Secret
exports.EU = function EnrollUsers(cb) {

  console.log("before enrolling registrar")
  if (UsersJson.hasOwnProperty('Admin_Name')){
    adminName = UsersJson['Admin_Name'];
  }else{
    console.log("admin user not found in json")
    throw Error(err)
  }

  myChain.getUser(adminName, function (err, userAdmin) {
      if (err) {
          throw Error(err)
      }
      if (UsersJson.hasOwnProperty('Admin_Secret')){
        adminSecret = UsersJson['Admin_Secret'];
      }else{
        console.log("admin secret not found in json")
        throw Error(err)
      }


      // Enroll the WebAppAdmin user with the certificate authority using
      // the one time password hard coded inside the membersrvc.yaml.
      myChain.enroll(adminName, adminSecret, function (err, admin) {
          if (err) {
            throw Error("Failed to enroll admin", err)
          }
          console.log("Enrolled successfully WebAppAdmin")
          myChain.setRegistrar(admin);
          console.log("Successfully set WebAppAdmin as Registrar")
        })

      if (UsersJson.hasOwnProperty('User1_Name')){
        user1Name = UsersJson['User1_Name'];
      }else{
        console.log("user1 not found in json")
        throw Error(err)
      }

      if (UsersJson.hasOwnProperty('User1_Secret')){
        user1Secret = UsersJson['User1_Secret'];
      }else{
        console.log("user1 secret not found json")
        throw Error(err)
      }

      console.log("name %s, secret %s", user1Name, user1Secret)
        myChain.getUser(user1Name, function (err, user100) {
          if (err) {
              fail(t, "get mrseller", err);
              // Exit program after a failure
              throw Error(err)
          }
          console.log("Found %s in yaml file", user1Name)
          if (user100.isEnrolled()) {
            console.log("%s is already enrolled", user1Name)
          }
          console.log("Enrolling mrseller....")


          myChain.enroll(user1Name, user1Secret, function (err, user) {
            if (err) {
              console.log("Failed enrolling mr seller.");
              throw Error (err)
            }

            console.log("Enrolled alice, getting userCert")
            mrseller = user
            mrseller.getUserCert(null, function (err, userCert) {
              if (err) {
                console.log("Failed getting Application certificate for alice.");
                throw Error(err)
              }
              var mrsellerAppCert = userCert;
              console.log("Got userCert")
              AuctionChainCalls(mrseller)
            })

         })
       })
     })
  }
