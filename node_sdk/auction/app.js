'use strict';
var hfc = require('hfc')
var SN = require('./auction-NS.js').SN;
var EU = require('./auction-MS.js').EU;

try {
  console.log("Before calling SetupNetwork from app.js")
  SN()
  console.log("Before enrolling users")
  EU()
} catch (e) {
    console.log(e);
}
