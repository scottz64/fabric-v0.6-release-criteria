#
# Copyright IBM Corp. 2016 All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os, os.path
import re
import time
import copy
from behave import *
from datetime import datetime, timedelta
import base64

import json

import bdd_compose_util, bdd_test_util, bdd_request_util, bdd_remote_util
from bdd_json_util import getAttributeFromJSON
from bdd_test_util import bdd_log

import sys, yaml
import subprocess

JSONRPC_VERSION = "2.0"

@given(u'we compose "{composeYamlFile}"')
def step_impl(context, composeYamlFile):
    context.compose_yaml = composeYamlFile
    if not context.byon:
        fileArgsToDockerCompose = bdd_compose_util.getDockerComposeFileArgsFromYamlFile(context.compose_yaml)
        context.compose_output, context.compose_error, context.compose_returncode = \
            bdd_test_util.cli_call(["docker-compose"] + fileArgsToDockerCompose + ["up","--force-recreate", "-d"], expect_success=True)
        assert context.compose_returncode == 0, "docker-compose failed to bring up {0}".format(composeYamlFile)

    bdd_compose_util.parseComposeOutput(context)

    if not context.byon:
        timeoutSeconds = 30
        assert bdd_compose_util.allContainersAreReadyWithinTimeout(context, timeoutSeconds), \
            "Containers did not come up within {} seconds, aborting".format(timeoutSeconds)

    context.containerAliasMap = bdd_compose_util.mapAliasesToContainers(context)
    context.containerNameMap = bdd_compose_util.mapContainerNamesToContainers(context)

@when(u'requesting "{path}" from "{containerAlias}"')
def step_impl(context, path, containerAlias):
    context.response = bdd_request_util.httpGetToContainerAlias(context, \
        containerAlias, path)

@then(u'I should get a JSON response containing "{attribute}" attribute')
def step_impl(context, attribute):
    getAttributeFromJSON(attribute, context.response.json())

@then(u'I should get a JSON response containing no "{attribute}" attribute')
def step_impl(context, attribute):
    try:
        getAttributeFromJSON(attribute, context.response.json())
        assert None, "Attribute found in response (%s)" %(attribute)
    except AssertionError:
        bdd_log("Attribute not found as was expected.")

def formatStringToCompare(value):
    # double quotes are replaced by simple quotes because is not possible escape double quotes in the attribute parameters.
    return str(value).replace("\"", "'")

def checkHeight(context, foundValue, expectedValue):
    if context.byon:
        assert (foundValue >= int(expectedValue)), "For attribute height, expected equal or greater than (%s), instead found (%s)" % (expectedValue, foundValue)
    elif expectedValue == 'previous':
        bdd_log("Stored height: {}".format(context.height))
        assert (foundValue == context.height), "For attribute height, expected (%s), instead found (%s)" % (context.height, foundValue)
    else:
        assert (formatStringToCompare(foundValue) == expectedValue), "For attribute height, expected (%s), instead found (%s)" % (expectedValue, foundValue)

@then(u'I should get a JSON response with "{attribute}" = "{expectedValue}"')
def step_impl(context, attribute, expectedValue):
    foundValue = getAttributeFromJSON(attribute, context.response.json())
    if attribute == 'height':
        checkHeight(context, foundValue, expectedValue)
    else:
        assert (formatStringToCompare(foundValue) == expectedValue), "For attribute %s, expected (%s), instead found (%s)" % (attribute, expectedValue, foundValue)
    # Set the new value of the attribute
    setattr(context, attribute, foundValue)

@then(u'I should get a JSON response with "{attribute}" > "{expectedValue}"')
def step_impl(context, attribute, expectedValue):
    foundValue = getAttributeFromJSON(attribute, context.response.json())
    if expectedValue == 'previous':
        prev_value = getattr(context, attribute)
        bdd_log("Stored value: {}".format(prev_value))
        assert (foundValue > prev_value), "For attribute %s, expected greater than (%s), instead found (%s)" % (attribute, prev_value, foundValue)
    else:
        assert (formatStringToCompare(foundValue) > expectedValue), "For attribute %s, expected greater than (%s), instead found (%s)" % (attribute, expectedValue, foundValue)
    # Set the new value of the attribute
    setattr(context, attribute, foundValue)

@then(u'I should get a JSON response with array "{attribute}" contains "{expectedValue}" elements')
def step_impl(context, attribute, expectedValue):
    foundValue = getAttributeFromJSON(attribute, context.response.json())
    assert (len(foundValue) == int(expectedValue)), "For attribute %s, expected array of size (%s), instead found (%s)" % (attribute, expectedValue, len(foundValue))

@given(u'I wait "{seconds}" seconds')
def step_impl(context, seconds):
    time.sleep(float(seconds))

@when(u'I wait "{seconds}" seconds')
def step_impl(context, seconds):
    time.sleep(float(seconds))

@then(u'I wait "{seconds}" seconds')
def step_impl(context, seconds):
    time.sleep(float(seconds))

@when(u'I deploy lang chaincode "{chaincodePath}" of "{chainLang}" with ctor "{ctor}" to "{containerAlias}"')
def step_impl(context, chaincodePath, chainLang, ctor, containerAlias):
    bdd_log("Printing chaincode language " + chainLang)

    chaincode = {
        "path": chaincodePath,
        "language": chainLang,
        "constructor": ctor,
        "args": getArgsFromContext(context),
    }

    if context.byon:
        context = login(context, containerAlias)
        chaincode["secureContext"] = get_primary_user(context)[0]
    #elif 'userName' in context:
    elif hasattr(context, 'userName'):
        chaincode["secureContext"] = context.userName

    container = context.containerAliasMap[containerAlias]
    deployChainCodeToContainer(context, chaincode, container)

def getArgsFromContext(context):
    args = []

    #if 'table' in context:
    if hasattr(context, 'table'):
       # There is ctor arguments
       args = context.table[0].cells

    return args

def get_primary_user(context):
    for user in context.user_creds:
        if user['peer'] == 'vp0':
            return (user['username'], user['secret'])
    return (context.user_creds[0]['username'], context.user_creds[0]['secret'])

@when(u'I deploy chaincode "{chaincodePath}" with ctor "{ctor}" to "{containerAlias}"')
def step_impl(context, chaincodePath, ctor, containerAlias):
    chaincode = {
        "path": chaincodePath,
        "language": "GOLANG",
        "constructor": ctor,
        "args": getArgsFromContext(context),
    }

    if context.byon:
        context = login(context, containerAlias)
        chaincode["secureContext"] = get_primary_user(context)[0]
    #elif 'userName' in context:
    elif hasattr(context, 'userName'):
        chaincode["secureContext"] = context.userName

    container = context.containerAliasMap[containerAlias]
    deployChainCodeToContainer(context, chaincode, container)

@when(u'I deploy chaincode with name "{chaincodeName}" and with ctor "{ctor}" to "{containerAlias}"')
def step_impl(context, chaincodeName, ctor, containerAlias):
    chaincode = {
        "name": chaincodeName,
        "language": "GOLANG",
        "constructor": ctor,
        "args": getArgsFromContext(context),
    }

    if context.byon:
        context = login(context, containerAlias)
        chaincode["secureContext"] = get_primary_user(context)[0]
    #elif 'userName' in context:
    elif hasattr(context, 'userName'):
        chaincode["secureContext"] = context.userName

    container = context.containerAliasMap[containerAlias]
    deployChainCodeToContainer(context, chaincode, container)
    time.sleep(2.0) # After #2068 implemented change this to only apply after a successful ping

def deployChainCodeToContainer(context, chaincode, container):
    chaincodeSpec = createChaincodeSpec(context, chaincode)

    chaincodeOpPayload = createChaincodeOpPayload("deploy", chaincodeSpec)
    context.response = bdd_request_util.httpPostToContainer(context, \
        container, "/chaincode", chaincodeOpPayload)

    chaincodeName = context.response.json()['result']['message']
    chaincodeSpec['chaincodeID']['name'] = chaincodeName
    context.chaincodeSpec = chaincodeSpec
    bdd_log(json.dumps(chaincodeSpec, indent=4))
    bdd_log("")

def createChaincodeSpec(context, chaincode):
    chaincode = validateChaincodeDictionary(chaincode)
    args = prepend(chaincode["constructor"], chaincode["args"])
    # Create a ChaincodeSpec structure
    chaincodeSpec = {
        "type": getChaincodeTypeValue(chaincode["language"]),
        "chaincodeID": {
            "path" : chaincode["path"],
            "name" : chaincode["name"]
        },
        "ctorMsg":  {
            "args" : args
        },
    }

    if context.byon:
        chaincodeSpec["secureContext"] = get_primary_user(context)[0]
    #elif 'userName' in context:
    elif hasattr(context, 'userName'):
        chaincodeSpec["secureContext"] = context.userName

    #if 'metadata' in context:
    if hasattr(context, 'metadata'):
        chaincodeSpec["metadata"] = context.metadata

    return chaincodeSpec

def validateChaincodeDictionary(chaincode):
    chaincodeFields = ["path", "name", "language", "constructor", "args"]

    for field in chaincodeFields:
        if field not in chaincode:
            chaincode[field] = ""

    return chaincode

def getChaincodeTypeValue(chainLang):
    if chainLang == "GOLANG":
        return 1
    elif chainLang =="JAVA":
        return 4
    elif chainLang == "NODE":
        return 2
    elif chainLang == "CAR":
        return 3
    elif chainLang == "UNDEFINED":
        return 0
    return 1

def get_primary_user(context):
    for user in context.user_creds:
        if user['peer'] == 'vp0':
            return (user['username'], user['secret'])
    return (context.user_creds[0]['username'], context.user_creds[0]['secret'])

@when(u'I mock deploy chaincode with name "{chaincodeName}"')
def step_impl(context, chaincodeName):
    chaincode = {
        "name": chaincodeName,
        "language": "GOLANG"
    }

    context.chaincodeSpec = createChaincodeSpec(context, chaincode)

@then(u'I should have received a chaincode name')
def step_impl(context):
    #if 'chaincodeSpec' in context:
    if hasattr(context, 'chaincodeSpec'):
        assert context.chaincodeSpec['chaincodeID']['name'] != ""
        # Set the current transactionID to the name passed back
        context.transactionID = context.chaincodeSpec['chaincodeID']['name']
    #elif 'grpcChaincodeSpec' in context:
    elif hasattr(context, 'grpcChaincodeSpec'):
        assert context.grpcChaincodeSpec.chaincodeID.name != ""
        # Set the current transactionID to the name passed back
        context.transactionID = context.grpcChaincodeSpec.chaincodeID.name
    else:
        fail('chaincodeSpec not in context')

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" on "{containerAlias}" with "{idGenAlg}"')
def step_impl(context, chaincodeName, functionName, containerAlias, idGenAlg):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    invokeChaincode(context, "invoke", functionName, containerAlias, idGenAlg)

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" on "{containerAlias}" "{times}" times')
def step_impl(context, chaincodeName, functionName, containerAlias, times):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"

    resp = bdd_request_util.httpGetToContainerAlias(context, containerAlias, "/chain")
    context.chainheight = getAttributeFromJSON("height", resp.json())
    context.txcount = times
    for i in range(int(times)):
        invokeChaincode(context, "invoke", functionName, containerAlias)
        #time.sleep(1)

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" with attributes "{attrs}" on "{containerAlias}"')
def step_impl(context, chaincodeName, functionName, attrs, containerAlias):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    assert attrs, "attrs were not specified"
    invokeChaincode(context, "invoke", functionName, containerAlias, None, attrs.split(","))

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" on "{containerAlias}"')
def step_impl(context, chaincodeName, functionName, containerAlias):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    invokeChaincode(context, "invoke", functionName, containerAlias)

@when(u'I invoke master chaincode "{chaincodeName}" function name "{functionName}" on "{containerAlias}"')
def step_impl(context, chaincodeName, functionName, containerAlias):
    container = context.containerAliasMap[containerAlias]
    invokeMasterChaincode(context, "invoke", chaincodeName, functionName, container)

@then(u'I should have received a transactionID')
def step_impl(context):
    assert 'transactionID' in context, 'transactionID not found in context'
    assert context.transactionID != ""
    pass

@when(u'I unconditionally query chaincode "{chaincodeName}" function name "{functionName}" on "{containerAlias}"')
def step_impl(context, chaincodeName, functionName, containerAlias):
    invokeChaincode(context, "query", functionName, containerAlias)

@when(u'I query chaincode "{chaincodeName}" function name "{functionName}" on "{containerAlias}"')
def step_impl(context, chaincodeName, functionName, containerAlias):
    invokeChaincode(context, "query", functionName, containerAlias)

def createChaincodeOpPayload(method, chaincodeSpec):
    chaincodeOpPayload = {
        "jsonrpc": JSONRPC_VERSION,
        "method" : method,
        "params" : chaincodeSpec,
        "id"     : 1
    }
    return chaincodeOpPayload

def invokeChaincode(context, devopsFunc, functionName, containerAlias, idGenAlg=None, attributes=[]):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    # Update the chaincodeSpec ctorMsg for invoke
    args = []
    #if 'table' in context:
    if hasattr(context, 'table'):
       # There is ctor arguments
       args = context.table[0].cells
    args = prepend(functionName, args)
    for idx, attr in enumerate(attributes):
        attributes[idx] = attr.strip()

    context.chaincodeSpec['attributes'] = attributes

    container = context.containerAliasMap[containerAlias]
    #If idGenAlg is passed then, we still using the deprecated devops API because this parameter can't be passed in the new API.
    if idGenAlg != None:
        context.chaincodeSpec['ctorMsg']['args'] = to_bytes(args)
        invokeUsingDevopsService(context, devopsFunc, functionName, container, idGenAlg)
    else:
        context.chaincodeSpec['ctorMsg']['args'] = args
        invokeUsingChaincodeService(context, devopsFunc, functionName, container)

def invokeUsingChaincodeService(context, devopsFunc, functionName, container):
    # Invoke the POST
    chaincodeOpPayload = createChaincodeOpPayload(devopsFunc, context.chaincodeSpec)
    context.response = bdd_request_util.httpPostToContainer(context, \
        container, "/chaincode", chaincodeOpPayload)

    if 'result' in context.response.json():
        result = context.response.json()['result']
        if 'message' in result:
            transactionID = result['message']
            context.transactionID = transactionID

def invokeUsingDevopsService(context, devopsFunc, functionName, container, idGenAlg):
    # Invoke the POST
    chaincodeInvocationSpec = {
        "chaincodeSpec" : context.chaincodeSpec,
        "idGenerationAlg": idGenAlg
    }
    #chaincodeInvocationSpec["chaincodeSpec"][    "idGenerationAlg": idGenAlg

    bdd_log(chaincodeInvocationSpec)
    context.response = bdd_request_util.httpPostToContainer(context, \
        container, "/chaincode", chaincodeInvocationSpec)
    #endpoint = "/devops/{0}".format(devopsFunc)
    #context.response = bdd_request_util.httpPostToContainer(context, \
    #    container, endpoint, chaincodeInvocationSpec)

    if 'message' in context.response.json():
        transactionID = context.response.json()['message']
        context.transactionID = transactionID

def invokeMasterChaincode(context, devopsFunc, chaincodeName, functionName, container):
    args = []
    #if 'table' in context:
    if hasattr(context, 'table'):
       args = context.table[0].cells
    args = prepend(functionName, args)
    typeGolang = 1
    chaincodeSpec = {
        "type": typeGolang,
        "chaincodeID": {
            "name" : chaincodeName
        },
        "ctorMsg":  {
            "args" : args
        }
    }
    #if 'userName' in context:
    if hasattr(context, 'userName'):
        chaincodeSpec["secureContext"] = context.userName

    chaincodeOpPayload = createChaincodeOpPayload(devopsFunc, chaincodeSpec)
    context.response = bdd_request_util.httpPostToContainer(context, \
        container, "/chaincode", chaincodeOpPayload)

    if 'result' in context.response.json():
        result = context.response.json()['result']
        if 'message' in result:
            transactionID = result['message']
            context.transactionID = transactionID

@then(u'I wait "{seconds}" seconds for chaincode to build')
def step_impl(context, seconds):
    """ This step takes into account the chaincodeImagesUpToDate tag, in which case the wait is reduce to some default seconds"""
    reducedWaitTime = 4
    if 'chaincodeImagesUpToDate' in context.tags:
        bdd_log("Assuming images are up to date, sleeping for {0} seconds instead of {1} in scenario {2}".format(reducedWaitTime, seconds, context.scenario.name))
        time.sleep(float(reducedWaitTime))
    else:
        time.sleep(float(seconds))

@then(u'I check the transaction ID if it is "{tUUID}"')
def step_impl(context, tUUID):
    assert 'transactionID' in context, "transactionID not found in context"
    assert context.transactionID == tUUID, "transactionID is not tUUID"

@then(u'I wait up to "{seconds}" seconds for transaction to be committed to all peers')
def step_impl(context, seconds):
    assert 'transactionID' in context, "transactionID not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"

    containers = context.compose_containers
    transactionCommittedToContainersWithinTimeout(context, containers, int(seconds))

@then(u'I wait up to "{seconds}" seconds for transaction to be committed to peers')
def step_impl(context, seconds):
    assert 'transactionID' in context, "transactionID not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    aliases = context.table.headings
    containers = [context.containerAliasMap[alias] for alias in aliases]
    transactionCommittedToContainersWithinTimeout(context, containers, int(seconds))

def transactionCommittedToContainersWithinTimeout(context, containers, timeout):
    # Set the max time before stopping attempts
    maxTime = datetime.now() + timedelta(seconds=timeout)
    endpoint = "/transactions/{0}".format(context.transactionID)

    for container in containers:
        request_url = bdd_request_util.buildContainerUrl(context, container, endpoint)
        urlFound = httpGetUntilSuccessfulOrTimeout(request_url, maxTime, responseIsOk)

        assert urlFound, "Timed out waiting for transaction to be committed to {}" \
            .format(container.name)

def responseIsOk(response):
    isResponseOk = False

    status_code = response.status_code
    assert status_code == 200 or status_code == 404, \
        "Error requesting {}, returned result code = {}, expected {} or {}" \
            .format(url, status_code, 200, 404)

    if status_code == 200:
        isResponseOk = True

    return isResponseOk

def httpGetUntilSuccessfulOrTimeout(url, timeoutTimestamp, isSuccessFunction):
    """ Keep attempting to HTTP GET the given URL until either the given
        timestamp is exceeded or the given callback function passes.
        isSuccessFunction should accept a requests.response and return a boolean
    """
    successful = False

    while timeNowIsWithinTimestamp(timeoutTimestamp) and not successful:
        response = bdd_request_util.httpGet(url, expectSuccess=False)
        successful = isSuccessFunction(response)
        time.sleep(1)

    return successful

def timeNowIsWithinTimestamp(timestamp):
    return datetime.now() < timestamp

@then(u'I wait up to "{seconds}" seconds for transactions to be committed to peers')
def step_impl(context, seconds):
    assert 'chainheight' in context, "chainheight not found in context"
    assert 'txcount' in context, "txcount not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    aliases = context.table.headings
    containers = [context.containerAliasMap[alias] for alias in aliases]
    allTransactionsCommittedToContainersWithinTimeout(context, containers, int(seconds))

def allTransactionsCommittedToContainersWithinTimeout(context, containers, timeout):
    maxTime = datetime.now() + timedelta(seconds=timeout)
    endpoint = "/chain"
    expectedMinHeight = int(context.chainheight) + int(context.txcount)

    allTransactionsCommitted = lambda (response): \
        getAttributeFromJSON("height", response.json()) >= expectedMinHeight

    for container in containers:
        request_url = bdd_request_util.buildContainerUrl(context, container, endpoint)
        urlFound = httpGetUntilSuccessfulOrTimeout(request_url, maxTime, allTransactionsCommitted)

        assert urlFound, "Timed out waiting for transaction to be committed to {}" \
            .format(container.name)

@then(u'I should get a rejection message in the listener after stopping it')
def step_impl(context):
    assert "eventlistener" in context, "no eventlistener is started"
    context.eventlistener.terminate()
    output = context.eventlistener.stdout.read()
    rejection = "Received rejected transaction"
    assert rejection in output, "no rejection message was found"
    assert output.count(rejection) == 1, "only one rejection message should be found"


@when(u'I query chaincode "{chaincodeName}" function name "{functionName}" on all peers')
def step_impl(context, chaincodeName, functionName):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    # Update the chaincodeSpec ctorMsg for invoke
    args = []
    #if 'table' in context:
    if hasattr(context, 'table'):
       # There is ctor arguments
       args = context.table[0].cells
    args = prepend(functionName, args)

    context.chaincodeSpec['ctorMsg']['args'] = args #context.table[0].cells if ('table' in context) else []
    chaincodeOpPayload = createChaincodeOpPayload("query", context.chaincodeSpec)

    responses = []
    for container in context.compose_containers:
        resp = bdd_request_util.httpPostToContainer(context, \
            container, "/chaincode", chaincodeOpPayload)
        responses.append(resp)
    context.responses = responses

@when(u'I unconditionally query chaincode "{chaincodeName}" function name "{functionName}" with value "{value}" on peers')
def step_impl(context, chaincodeName, functionName, value):
    query_common(context, chaincodeName, functionName, value, False)

@when(u'I query chaincode "{chaincodeName}" function name "{functionName}" with value "{value}" on peers')
def step_impl(context, chaincodeName, functionName, value):
    query_common(context, chaincodeName, functionName, value, True)

def query_common(context, chaincodeName, functionName, value, failOnError):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"
    assert 'peerToSecretMessage' in context, "peerToSecretMessage map not found in context"

    # Update the chaincodeSpec ctorMsg for invoke
    context.chaincodeSpec['ctorMsg']['args'] = [functionName, value]
    # Make deep copy of chaincodeSpec as we will be changing the SecurityContext per call.
    chaincodeOpPayload = createChaincodeOpPayload("query", copy.deepcopy(context.chaincodeSpec))

    responses = []
    aliases = context.table.headings
    containers = [context.containerAliasMap[alias] for alias in aliases]
    bdd_log("Query containers: {}".format(containers))
    for container in containers:
        # Change the SecurityContext per call
        chaincodeOpPayload['params']["secureContext"] = \
            context.peerToSecretMessage.get(container.composeService, container.name)['enrollId']
            #context.peerToSecretMessage[container.composeService]['enrollId']

        bdd_log("Chaincode payload = {0}".format(chaincodeOpPayload))
        bdd_log("Container {0} enrollID = {1}".format(container.name, container.getEnv("CORE_SECURITY_ENROLLID")))
        resp = bdd_request_util.httpPostToContainer(context, \
            container, "/chaincode", chaincodeOpPayload, expectSuccess=failOnError)
        responses.append(resp)

    context.responses = responses

@then(u'I wait up to "{seconds}" seconds for transaction to be committed to peers that fail')
def step_impl(context, seconds):
    assert 'transactionID' in context, "transactionID not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    headers = {'Accept': 'application/json', 'Content-type': 'application/json'}
    if context.byon and context.tls:
        headers['zACI-API'] = 'com.ibm.zaci.system/1.0'
        headers['Accept'] = 'application/vnd.ibm.zaci.paylod+json'

    aliases =  context.table.headings
    containerDataList = bdd_compose_util.getContainerDataValuesFromContext(context, aliases, lambda containerData: containerData)

    # Build map of "containerName" : resp.statusCode
    respMap = {container.containerName:0 for container in containerDataList}

    # Set the max time before stopping attempts
    maxTime = datetime.now() + timedelta(seconds = int(seconds))
    for container in containerDataList:
        request_url = buildUrl(context, container.url, "/transactions/{0}".format(context.transactionID))

        # Loop unless failure or time exceeded
        while (datetime.now() < maxTime):
            bdd_log("{0} GETing path = {1}".format(currentTime(), request_url))
            resp = bdd_request_util.httpGetToContainer(context, \
                container, "/transactions/{0}".format(context.transactionID), expectSuccess=failOnError)
            responses.append(resp)

            resp = requests.get(request_url, headers=headers, timeout=60, verify=False)
            if resp.status_code == 404:
                # Pause then try again
                respMap[container.containerName] = 404
                time.sleep(1)
                continue
            else:
                raise Exception("Error requesting {0}, returned result code = {1}".format(request_url, resp.status_code))
            resp.connection.close()
        else:
            assert respMap[container.containerName] in (404, 0), "response from transactions/{0}: {1}".format(context.transactionID, resp.status_code)
    bdd_log("Result of request to all peers = {0}".format(respMap))
    bdd_log("")

@then(u'I should get a JSON response from all peers with "{attribute}" = "{expectedValue}"')
def step_impl(context, attribute, expectedValue):
    assert 'responses' in context, "responses not found in context"
    for resp in context.responses:
        foundValue = getAttributeFromJSON(attribute, resp.json())
        assert (formatStringToCompare(foundValue) == expectedValue), "For attribute %s, expected (%s), instead found (%s)" % (attribute, expectedValue, foundValue)

@then(u'I should get a JSON response from peers with "{attribute}" = "{expectedValue}"')
def step_impl(context, attribute, expectedValue):
    assert 'responses' in context, "responses not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    for resp in context.responses:
        foundValue = getAttributeFromJSON(attribute, resp.json())
        assert (formatStringToCompare(foundValue) == expectedValue), "For attribute %s, expected (%s), instead found (%s)" % (attribute, expectedValue, foundValue)

@given(u'I register with CA supplying username "{userName}" and secret "{secret}" on peers')
def step_impl(context, userName, secret):
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    if context.byon:
        user_creds = get_primary_user(context)
        userName = user_creds[0]
        secret = user_creds[1]

    secretMsg = {
        "enrollId": userName,
        "enrollSecret" : secret
    }

    # Login to each container specified
    aliases = context.table.headings
    containers = [context.containerAliasMap[alias] for alias in aliases]
    for container in containers:
        context.response = bdd_request_util.httpPostToContainer(context, \
            container, "/registrar", secretMsg)

        # Create new User entry
        bdd_test_util.registerUser(context, secretMsg, container.composeService)

    # Store the username in the context
    context.userName = userName
    context.secret = secret
    # if we already have the chaincodeSpec, change secureContext
    #if 'chaincodeSpec' in context:
    if hasattr(context, 'chaincodeSpec'):
        context.chaincodeSpec["secureContext"] = context.userName


@given(u'I use the following credentials for querying peers')
def step_impl(context):
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers, username, secret) not found in context"

    peerToSecretMessage = {}

    if context.byon:
        user_creds = context.user_creds
    else:
        user_creds = context.table.rows

    # Login to each container specified using username and secret
    for row in user_creds:
        peer, userName, secret = row['peer'], row['username'], row['secret']
        peerToSecretMessage[peer] = {
            "enrollId": userName,
            "enrollSecret" : secret
        }

        container = context.containerAliasMap[peer]
        context.response = bdd_request_util.httpPostToContainer(context, \
            container, "/registrar", peerToSecretMessage[peer])

    context.peerToSecretMessage = peerToSecretMessage

@given(u'I mount peer data')
def step_impl(context):
    for container in context.compose_containers:
        if container.containerName.startswith("vp"):
            compose_output, compose_error, compose_returncode = \
                 bdd_test_util.cli_call(context,
                                        ["docker", "create", "-v", "/var/hyperledger/test/behave/db",
                                         "--name", "{0}_dbstore".format(container.containerName),
                                         "hyperledger/fabric-peer", "/bin/true"],
                                        expect_success=True)
        else:
            compose_output, compose_error, compose_returncode = \
                 bdd_test_util.cli_call(context,
                                        ["docker", "create", "-v", "/var/hyperledger/test/behave/db",
                                         "--name", "{0}_dbstore".format(container.containerName),
                                         "hyperledger/fabric-membersrvc", "/bin/true"],
                                        expect_success=True)
        assert compose_returncode == 0, "docker create failed to create a volume for the behave transaction database"

@given(u'I build new images')
def step_impl(context):
    # Grab the last 2 commit SHAs
    prev_log, error, returncode = bdd_test_util.cli_call(
                                   ["/usr/bin/git", "log", "-n", "2",
                                    "--oneline",
                                    "--no-abbrev-commit"],
                                   expect_success=True)
    commit = prev_log.split()[0]
    bdd_log("current commit: {0}".format(commit))

    try:
        # Build a new caserver and peer image from the previous commit
        res, error, returncode = bdd_test_util.cli_call(
                                   ['git', 'checkout', "%s~1" % commit],
                                   expect_success=True)
        bdd_log("Git results: {0}".format(res))

        # Kill chaincode containers
        res, error, returncode = bdd_test_util.cli_call(
                                   ["docker", "ps", "-n=4", "-q"],
                                   expect_success=True)
        bdd_log("Killing chaincode containers: {0}".format(res))
        result, error, returncode = bdd_test_util.cli_call(
                                   ["docker", "rm", "-f"] + res.split('\n'),
                                   expect_success=False)

        # Kill chaincode images
        res, error, returncode = bdd_test_util.cli_call(
                                   ["docker", "images"],
                                   expect_success=True)
        images = res.split('\n')
        for image in images:
            if image.startswith('dev-vp'):
                fields = image.split()
                r, e, ret= bdd_test_util.cli_call(
                                   ["docker", "rmi", "-f", fields[2]],
                                   expect_success=False)
        bdd_log("Removed chaincode images")

        # Build peer_beta
        output, error, returncode = bdd_test_util.cli_call(
                                   ["docker", "build",
                                    "-t", "hyperledger/fabric-peer:previous",
                                    "../build/image/peer"],
                                   expect_success=True)
        assert returncode == 0, "docker peer image not built correctly for previous commit"
        bdd_log("Successfully built new peer image")

        # Build membersrvc_beta
        output, error, returncode = bdd_test_util.cli_call(
                                   ["docker", "build",
                                    "-t", "hyperledger/fabric-membersrvc:previous",
                                    "../build/image/membersrvc"],
                                   expect_success=True)
        assert returncode == 0, "docker membersrvc image not built correctly for previous commit"
        bdd_log("Successfully built new membersrvc image")
    except:
        raise Exception("Unable to build images")
    finally:
        res, error, returncode = bdd_test_util.cli_call(
                                   ['git', 'checkout', commit],
                                   expect_success=True)


#@given(u'I build new images')
#def step_impl(context):
#    # Grab the last 2 commit SHAs
#    prev_log = subprocess.check_output(["/usr/bin/git", "log", "-n", "2",
#                                        "--oneline",
#                                        "--no-abbrev-commit"])
#    commit = prev_log.split()[0]
#    bdd_log("current commit: {0}".format(commit))
#
#    try:
#        # Build a new caserver and peer image from the previous commit
#        res = subprocess.check_output(['git', 'checkout', "%s~1" % commit])
#        bdd_log("Git results: {0}".format(res))
#
#        # Kill chaincode containers
#        res = subprocess.check_output(["docker", "ps", "-n=4", "-q"])
#        result = subprocess.check_output(["docker", "rm", "-f"] + res.split('\n'))
#
#        # Kill chaincode images
#        res = subprocess.check_output(["docker", "images", "|",
#                                       "awk", "'$1 ~ /dev-vp/ { print $3}'"])
#        result = subprocess.check_output(["docker", "rmi", "-f"] + res.split('\n'))
#
#        # Build peer_beta
#        output, error, returncode = bdd_test_util.cli_call(context,
#                                   ["docker", "build",
#                                    "-t", "hyperledger/fabric-peer:previous",
#                                    "../build/image/peer"],
#                                   expect_success=True)
#        assert returncode == 0, "docker peer image not built correctly for previous commit"
#
#        # Build membersrvc_beta
#        output, error, returncode = bdd_test_util.cli_call(context,
#                                   ["docker", "build",
#                                    "-t", "hyperledger/fabric-membersrvc:previous",
#                                    "../build/image/membersrvc"],
#                                   expect_success=True)
#        assert returncode == 0, "docker membersrvc image not built correctly for previous commit"
#    except:
#        pass
#    finally:
#        res = subprocess.check_output(['git', 'checkout', commit])

@given(u'I fallback using the following credentials')
def step_impl(context):
    assert 'table' in context, "table (of username, secret) not found in context"
    user_creds = context.table.rows
    fileArgsToDockerCompose = bdd_compose_util.getDockerComposeFileArgsFromYamlFile(context.compose_yaml)

    # Stop membersrvc
    compose_output, compose_error, compose_returncode = \
        bdd_test_util.cli_call(
                               ["docker-compose"] + fileArgsToDockerCompose + ["stop", "membersrvc0"],
                               expect_success=True)
    assert compose_returncode == 0, "docker failed to stop membersrvc"
    bdd_log("Stopped membersrvc0")

    context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != "membersrvc0"]

    # Start membersrvc
    compose_output, compose_error, compose_returncode = \
        bdd_test_util.cli_call(
                               ["docker", "run", "-d",
                                "--volumes-from", "bdddocker_dbstore_membersrvc0_1",
                                "--name=beta_membersrvc0",
                                "-p", "7054:7054",
                                "-p", "50052:7051",
                                "-it", "hyperledger/fabric-membersrvc:previous",
                                "membersrvc"],
                               expect_success=True)
    assert compose_returncode == 0, "docker failed to start membersrvc"

    # Give the membersrvc time to come up before starting peers
    time.sleep(2)

    # Update and Save the new containers to the context
    new_container_names = bdd_compose_util.update_peers(context, "beta", "previous")
    new_containers = bdd_compose_util.saveContainerDataToContext(new_container_names, context)
    context.compose_containers = context.compose_containers + new_containers
    context.containerAliasMap = bdd_compose_util.mapAliasesToContainers(context)
    context.containerNameMap = bdd_compose_util.mapContainerNamesToContainers(context)
    bdd_log("New Containers: {}".format(context.compose_containers))

#    # Login to each container specified
#    for containerData in new_containers:
#        index = new_containers.index(containerData)
#        userName, secret = user_creds[index]['username'], user_creds[index]['secret']
#        secretMsg = {
#            "enrollId": userName,
#            "enrollSecret" : secret
#        }
#        bdd_log("Secret Msg: {}".format(secretMsg))
#        #context.response = bdd_request_util.httpPostToContainer(context, \
#        response = bdd_request_util.httpPostToContainer(context, containerData, "/registrar", secretMsg)

@given(u'I fallback')
def step_impl(context):
    fileArgsToDockerCompose = bdd_compose_util.getDockerComposeFileArgsFromYamlFile(context.compose_yaml)

    # Stop membersrvc
    compose_output, compose_error, compose_returncode = \
        bdd_test_util.cli_call(["docker-compose"] + fileArgsToDockerCompose + ["stop", "membersrvc0"],
                               expect_success=True)
    assert compose_returncode == 0, "docker failed to stop membersrvc"
    bdd_log("Stopped membersrvc0")

    context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != "membersrvc0"]

    # Start membersrvc
    compose_output, compose_error, compose_returncode = \
        bdd_test_util.cli_call(["docker", "run", "-d",
                                "--volumes-from", "bdddocker_dbstore_membersrvc0_1",
                                "--name=beta_membersrvc0",
                                "-p", "50051:50051",
                                "-p", "50052:30303",
                                "-it", "hyperledger/fabric-membersrvc:previous",
                                "membersrvc"],
                               expect_success=True)
    assert compose_returncode == 0, "docker failed to start membersrvc"

    # Update and Save the new containers to the context
    new_container_names = bdd_compose_util.update_peers(context, "beta", "previous")
    new_containers = bdd_compose_util.saveContainerDataToContext(new_container_names, context)
    context.compose_containers = context.compose_containers + new_containers
    context.containerAliasMap = bdd_compose_util.mapAliasesToContainers(context)
    context.containerNameMap = bdd_compose_util.mapContainerNamesToContainers(context)

@given(u'I upgrade using the following credentials')
def step_impl(context):
    assert 'table' in context, "table (of username, secret) not found in context"

    # Verify that a latest build is present from the fallback scenario
    output, error, returncode = bdd_test_util.cli_call(
                                   ["docker", "images", "-q", "hyperledger/fabric-peer:latest"],
                                   expect_success=True)
    assert output != "", "There is no peer build with the 'latest' tag"
    assert returncode == 0, "docker peer image not built correctly for latest commit"
    output, error, returncode = bdd_test_util.cli_call(
                                   ["docker", "images", "-q", "hyperledger/fabric-membersrvc:latest"],
                                   expect_success=True)
    assert output != "", "There is no membersrvc build with the 'latest' tag"
    assert returncode == 0, "docker membersrvc image not built correctly for latest commit"

    # Stop membersrvc
    output, error, returncode = bdd_test_util.cli_call(
                               ["docker", "stop", "beta_membersrvc0"],
                               expect_success=False)
    assert returncode == 0, "docker failed to stop beta_membersrvc0"
    bdd_log("Stopped beta_membersrvc0")

    # Start membersrvc
    output, error, returncode = bdd_test_util.cli_call(
                               ["docker", "run", "-d",
                                "--volumes-from", "bdddocker_dbstore_membersrvc0_1",
                                "--name=caserver_2",
                                "-p", "7054:7054",
                                "-p", "50052:7051",
                                "-it", "hyperledger/fabric-membersrvc:latest",
                                "membersrvc"],
                               expect_success=True)
    assert returncode == 0, "docker failed to start caserver_2"

    # Update and Save the new containers to the context
    new_container_names = bdd_compose_util.update_peers(context, "new", "latest", previous="beta")
    new_containers = bdd_compose_util.saveContainerDataToContext(new_container_names, context)
    context.compose_containers = context.compose_containers + new_containers

@then(u'I should "{action}" the "{attribute}" from the JSON response')
def step_impl(context, action, attribute):
    assert attribute in context.response.json(), "Attribute not found in response ({})".format(attribute)
    foundValue = context.response.json()[attribute]
    if action == 'store':
        foundValue = getAttributeFromJSON(attribute, context.response.json())
        setattr(context, attribute, foundValue)
        bdd_log("Stored %s: %s" % (attribute, getattr(context, attribute)) )

#@then(u'I wait up to "{seconds}" seconds for transaction to be committed to peers that fail')
#def step_impl(context, seconds):
#    assert 'transactionID' in context, "transactionID not found in context"
#    assert 'compose_containers' in context, "compose_containers not found in context"
#    assert 'table' in context, "table (of peers) not found in context"
#
#    headers = {'Accept': 'application/json', 'Content-type': 'application/json'}
#    aliases =  context.table.headings
#    containerDataList = getContainerDataValuesFromContext(context, aliases, lambda containerData: containerData)
#
#    # Build map of "containerName" : resp.statusCode
#    respMap = {container.containerName:0 for container in containerDataList}
#
#    # Set the max time before stopping attempts
#    maxTime = datetime.now() + timedelta(seconds = int(seconds))
#    for container in containerDataList:
#        request_url = buildUrl(context, container.ipAddress, "/transactions/{0}".format(context.transactionID))
#
#        # Loop unless failure or time exceeded
#        while (datetime.now() < maxTime):
#            bdd_log("{0} GETing path = {1}".format(currentTime(), request_url))
#            resp = requests.get(request_url, headers=headers, timeout=60, verify=False)
#            if resp.status_code == 404:
#                # Pause then try again
#                respMap[container.containerName] = 404
#                time.sleep(1)
#                continue
#            else:
#                raise Exception("Error requesting {0}, returned result code = {1}".format(request_url, resp.status_code))
#            resp.connection.close()
#        else:
#            assert respMap[container.containerName] in (404, 0), "response from transactions/{0}: {1}".format(context.transactionID, resp.status_code)
#    bdd_log("Result of request to all peers = {0}".format(respMap))
#    bdd_log("")

#@given(u'I upgrade')
#def step_impl(context):
#    # Verify that a latest build is present from the fallback scenario
#    output, error, returncode = bdd_test_util.cli_call(context,
#                                   ["docker", "images", "-q", "hyperledger/fabric-peer:latest"],
#                                   expect_success=True)
#    assert output != "", "There is no peer build with the 'latest' tag"
#    assert returncode == 0, "docker peer image not built correctly for latest commit"
#    output, error, returncode = bdd_test_util.cli_call(context,
#                                   ["docker", "images", "-q", "hyperledger/fabric-membersrvc:latest"],
#                                   expect_success=True)
#    assert output != "", "There is no membersrvc build with the 'latest' tag"
#    assert returncode == 0, "docker membersrvc image not built correctly for latest commit"
#
#    # Stop membersrvc
#    output, error, returncode = bdd_test_util.cli_call(context,
#                               ["docker", "stop", "beta_membersrvc0"],
#                               expect_success=False)
#    assert returncode == 0, "docker failed to stop beta_membersrvc0"
#    bdd_log("Stopped beta_membersrvc0")
#
#    # Start membersrvc
#    output, error, returncode = bdd_test_util.cli_call(context,
#                               ["docker", "run", "-d",
#                                "--volumes-from", "bddtests_dbstore_membersrvc0_1",
#                                "--name=caserver_2",
#                                "-p", "50051:50051",
#                                "-p", "50052:30303",
#                                "-it", "hyperledger/fabric-membersrvc:latest",
#                                "membersrvc"],
#                               expect_success=True)
#    assert returncode == 0, "docker failed to start caserver_2"
#
#    # Update and Save the new containers to the context
#    new_container_names = update_peers(context, "new", "latest", previous="beta")
#    new_containers = saveContainerDataToContext(new_container_names, context)
#    context.compose_containers = context.compose_containers + new_containers

@given(u'I start a listener')
def step_impl(context):
    gopath = os.environ.get('GOPATH')
    assert gopath is not None, "Please set GOPATH properly!"
    listener = os.path.join(gopath, "src/github.com/hyperledger/fabric/build/bin/block-listener")
    assert os.path.isfile(listener), "Please build the block-listener binary!"
    bdd_test_util.start_background_process(context, "eventlistener", [listener, "-listen-to-rejections"] )


@given(u'I start peers')
def step_impl(context):
    compose_op(context, "start")

@given(u'I stop peers')
def step_impl(context):
    compose_op(context, "stop")

@given(u'I pause peers')
def step_impl(context):
    compose_op(context, "pause")

@given(u'I unpause peers')
def step_impl(context):
    compose_op(context, "unpause")

def compose_op(context, op):
    assert 'table' in context, "table (of peers) not found in context"
    assert 'compose_yaml' in context, "compose_yaml not found in context"

    fileArgsToDockerCompose = bdd_compose_util.getDockerComposeFileArgsFromYamlFile(context.compose_yaml)
    services =  context.table.headings
    # Loop through services and start/stop them, and modify the container data list if successful.
    for service in services:
       if context.byon:
           context.compose_output, context.compose_error, context.compose_returncode = handle_remote(context, service, op)
       else:
           context.compose_output, context.compose_error, context.compose_returncode = \
               bdd_test_util.cli_call(["docker-compose"] + fileArgsToDockerCompose + [op, service], expect_success=True)
       assert context.compose_returncode == 0, "docker-compose failed to {0} {0}".format(op, service)
       if op == "stop" or op == "pause":
           context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != service]
       else:
           bdd_compose_util.parseComposeOutput(context)
       bdd_log("After {0}ing, the container service list is = {1}".format(op, [containerData.composeService for  containerData in context.compose_containers]))

    context.containerAliasMap = bdd_compose_util.mapAliasesToContainers(context)
    context.containerNameMap = bdd_compose_util.mapContainerNamesToContainers(context)

def handle_remote(context, service, op):
    ipAddress = ""
    port = ""
    target = service
    for container in context.compose_containers:
        if service in container.name:
            ipAddress = container.ipAddress
            bdd_log("service: {}".format(service))
            bdd_log("remote map: {}".format(context.remote_map))
            port = context.remote_map[service]['port']
            target = service
    bdd_log("target::", target)
    bdd_log("ipAddress::", ipAddress)
    bdd_log("port::", port)
    if context.remote_ip:
        if op == 'start':
            bdd_remote_util.startNode(context, service)
        elif op == 'stop':
            bdd_remote_util.stopNode(context, service)
        elif op == 'pause':
            bdd_remote_util.stopNode(context, service)
        elif op == 'unpause':
            bdd_remote_util.startNode(context, service)
        # Give the network time to stablize
        time.sleep(15)
#    elif context.remote_ip is not None:
#        command = "sudo iptables -D INPUT -p tcp --destination-port 30303 -j DROP"
#        result = subprocess.check_output('ssh -p %s %s@%s "%s"' % (port, context.remote_user, context.remote_ip, command), shell=True)
    else:
        command = "export SUDO_ASKPASS=~/.remote_pass.sh;sudo iptables -D INPUT -p tcp --destination-port 30303 -j DROP"
        result = subprocess.check_output('ssh %s "%s"' % (ipAddress, command), shell=True)
    bdd_log("Print:>>{0}<<".format(result))
    return "", "%s %s completed" % (op, service), 0


def to_bytes(strlist):
    return [base64.standard_b64encode(s.encode('ascii')) for s in strlist]

def prepend(elem, l):
    if l is None or l == "":
        tail = []
    else:
        tail = l
    if elem is None:
	return tail
    return [elem] + tail

@given(u'I do nothing')
def step_impl(context):
    pass

def login(context, peer, userName=None, secret=None):
    enrollId = None
    enrollSecret = None

    if context.byon:
        enrollId = context.remote_user
        enrollSecret = context.remote_secret

    if context.remote_ip:
        user_creds = get_primary_user(context)
        userName = user_creds[0]
        secret = user_creds[1]

    secretMsg = {
        "enrollId": userName or enrollId,
        "enrollSecret" : secret or enrollSecret
    }
    container = context.containerAliasMap[peer]
    context.response = bdd_request_util.httpPostToContainer(context, container, "/registrar", secretMsg)

    bdd_log("message = {}".format(context.response.json()))
    return context
