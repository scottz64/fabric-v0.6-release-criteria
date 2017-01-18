
/*
Copyright IBM Corp. 2016 All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

		 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Modified by Ratnakar Asara, and Scott Zwierzynski.

*/

package main

import (
	"errors"
	"fmt"
	"strconv"
	"github.com/hyperledger/fabric/core/chaincode/shim"
)

type Chaincode_example02_addrecs struct {
}

func (t *Chaincode_example02_addrecs) Init(stub shim.ChaincodeStubInterface, function string, args []string) ([]byte, error) {
	var A, B string    // Entities for the Deploy/Init
	var Bval int
	var err error

	if len(args) != 4 {
		return nil, errors.New("Incorrect number of arguments. Expecting 4")
	}

	// Initialize the chaincode
	A = args[0]      // "a" // and every invoke will use a different key, e.g. a1, a2, ...
	Aval := args[1]  // DATA, a FixedString, or possibly a RandomString depending on the testcase
	B = args[2]      // "b" - which represents the ledger counter/height
	Bval, err = strconv.Atoi(args[3])    // cntr value integer. if A is "a0", then Bval should be 0
	if err != nil {
		return nil, errors.New("Cannot convert b to integer; Expecting string version of b, the ledger counter index")
	}
	fmt.Printf("Aval (INIT DATA STRING) = %s, Bval (INIT counter value) = %d\n", Aval, Bval)

	// Write the state to the ledger
	err = stub.PutState(A, []byte(Aval))    // "a" , DATA
	if err != nil {
		return nil, err
	}

	err = stub.PutState(B, []byte(strconv.Itoa(Bval)))  // "b" , the ledger counter value (typically zero, but could be anything, for the Deploy/Init)
	if err != nil {
		return nil, err
	}

	return nil, nil
}

// Transaction makes payment of X units from A to B
func (t *Chaincode_example02_addrecs) Invoke(stub shim.ChaincodeStubInterface, function string, args []string) ([]byte, error) {
	if function == "delete" {
		// Deletes an entity from its state
		return t.delete(stub, args)
	}

	var A, B, Aval string
	var Bval int
	var err error

	if len(args) != 3 {
		return nil, errors.New("Incorrect number of arguments. Expecting 3")
	}

	A = args[0]	// the key, "aN" ("a1" or "a2" or whatever, where N = the cntr value, the top of the ledger stack)
	Aval = args[1]	// DATA, a FixedString, or a RandomString, depending on the testcase, to put on the ledger
	B = args[2]	// "b", the ledger counter/height, which is string representation of "N" (i.e. numerical part of the key aN)

	Bvalbytes, err := stub.GetState(B)
	if err != nil {
		return nil, errors.New(fmt.Sprintf("Failed to get state for b (%s), the specified ledger counter/height", B))
	}
	if Bvalbytes == nil {
		return nil, errors.New(fmt.Sprintf("Cannot find b (%s)",B))
	}
	Bval, _ = strconv.Atoi(string(Bvalbytes))

	// Perform the execution
	Bval = Bval + 1
	fmt.Printf("Aval (DATA) = %s, Bval (B, the ledger counter++ value) = %d\n", Aval, Bval)

	// Write the state back to the ledger
	err = stub.PutState(A, []byte(Aval))     // aN, DATA
	if err != nil {
		return nil, err
	}

	err = stub.PutState(B, []byte(strconv.Itoa(Bval)))   // "b", incremented_counter_value
	if err != nil {
		return nil, err
	}

	return nil, nil
}

// Deletes an entity from state
func (t *Chaincode_example02_addrecs) delete(stub shim.ChaincodeStubInterface, args []string) ([]byte, error) {
	if len(args) != 1 {
		return nil, errors.New("Incorrect number of arguments. Expecting 1")
	}

	A := args[0]

	// Delete the key from the state in ledger
	err := stub.DelState(A)
	if err != nil {
		return nil, errors.New("Failed to delete state")
	}

	return nil, nil
}

// Query callback representing the query of a chaincode
func (t *Chaincode_example02_addrecs) Query(stub shim.ChaincodeStubInterface, function string, args []string) ([]byte, error) {
	if function != "query" {
		return nil, errors.New("Invalid query function name. Expecting \"query\"")
	}
	var key string // This is the key to search for: a (deployment value), aN (DATA value stored at that counter index), or b (ledger counter)
	var err error

	if len(args) != 1 {
		return nil, errors.New("Incorrect number of arguments. Expecting one arg - variable key name (a, aN, or b) to query")
	}

	key = args[0]

	// Get the state from the ledger
	keyvalbytes, err := stub.GetState(key)
	if err != nil {
		jsonResp := "{\"Error\":\"Failed to get state for " + key + "\"}"
		return nil, errors.New(jsonResp)
	}

	if keyvalbytes == nil {
		jsonResp := "{\"Error\":\"Nil amount for " + key + "\"}"
		return nil, errors.New(jsonResp)
	}

	jsonResp := "{\"Name\":\"" + key + "\",\"Amount\":\"" + string(keyvalbytes) + "\"}"
	fmt.Printf("Query Response:%s\n", jsonResp)
	return keyvalbytes, nil
}

func main() {
	self := &Chaincode_example02_addrecs{}
	err := shim.Start(self) // Our one instance implements both Transactions and Queries interfaces
	if err != nil {
		fmt.Printf("Error starting chaincode_example02_addrecs chaincode: %s", err)
	}
}
