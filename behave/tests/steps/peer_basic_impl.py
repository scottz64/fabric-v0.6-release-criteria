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

import os
import os.path
import re
import time
import copy
from datetime import datetime, timedelta

import sys, requests, json, yaml
import subprocess

import bdd_test_util

CORE_REST_PORT = 5000
JSONRPC_VERSION = "2.0"

class ContainerData:
    def __init__(self, containerName, ipAddress, url, port, envFromInspect, composeService, byon=False, tls=False):
        self.containerName = containerName
        self.ipAddress = ipAddress
        self.url = url
        self.port = port
        self.envFromInspect = envFromInspect
        self.composeService = composeService
        if byon:
            self.chainHeight = self.getHeight(tls)

    def getHeight(self, tls):
        schema = "http"
        headers = {'Accept': 'application/json'}
        if tls:
            schema = "https"
            headers = {'Accept': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}
        request_url = "{0}://{1}/chain".format(schema, self.url)

        print("Requesting path = {0}".format(request_url))
        resp = requests.get(request_url, headers=headers, verify=False)
        print("Resulting chain height {0}".format(resp.json()['height']))
        return resp.json()['height']

    def getEnv(self, key):
        envValue = None
        for val in self.envFromInspect:
            if val.startswith(key):
                envValue = val[len(key):]
                break
        if envValue == None:
            raise Exception("ENV key not found ({0}) for container ({1})".format(key, self.containerName))
        return envValue

def getContainerNames(context):
    """ Use the prefix to get the container name"""
    containerNamePrefix = os.path.basename(os.getcwd()) + "_"
    containerNames = []
    for l in context.compose_error.splitlines():
        tokens = l.split()
        print(tokens)
        if 1 < len(tokens):
            thisContainer = tokens[1]
            if containerNamePrefix not in thisContainer:
               thisContainer = containerNamePrefix + thisContainer + "_1"
            if thisContainer not in containerNames:
               containerNames.append(thisContainer)
    return containerNames

def getContainerIP(context, containerName):
    command = ["docker", "inspect", "--format", "{{ .NetworkSettings.IPAddress }}", containerName]
    output, error, returncode = bdd_test_util.cli_call(context, command, expect_success=True)
    return output.splitlines()[0]

def getContainerEnvArray(context, containerName):
    output, error, returncode = \
        bdd_test_util.cli_call(context, ["docker", "inspect", "--format",  "{{ .Config.Env }}", containerName], expect_success=True)
    return output.splitlines()[0][1:-1].split()

def getContainerServiceLabels(context, containerName):
    """ Get the Labels to access the com.docker.compose.service value"""
    output, error, returncode = \
        bdd_test_util.cli_call(context, ["docker", "inspect", "--format",  "{{ .Config.Labels }}", containerName], expect_success=True)
    if len(output) <= 6:
        result = containerName.split("_")
        return [result[-1]]
    labels = output.splitlines()[0][4:-1].split()
    return [composeService[27:] for composeService in labels if composeService.startswith("com.docker.compose.service:")][0]

def saveContainerDataToContext(containerNames, context):
    """ Now get the Network Address for each name, and set the ContainerData onto the context."""
    containerDataList = []
    for containerName in containerNames:
        dockerComposeService = getContainerServiceLabels(context, containerName)
        print("dockerComposeService = {0}".format(dockerComposeService))
        ipAddress = getContainerIP(context, containerName)
        print("container {0} has address = {1}".format(containerName, ipAddress))
        env = getContainerEnvArray(context, containerName)
        print("container {0} has env = {1}".format(containerName, env))
        containerDataList.append(ContainerData(containerName, ipAddress, ipAddress+":{0}".format(CORE_REST_PORT), None, env, dockerComposeService, byon=context.byon, tls=context.tls))
    return containerDataList

def get_ssh_info(context, peer):
    env_result = ''
    if context.tls and context.remote_ip:
        request_url = "https://{0}/api/com.ibm.zBlockchain/peers/{1}/status".format(context.remote_ip, peer['name'])
        print("GETing path = {0}".format(request_url))
        resp = requests.get(request_url, headers={'Content-type': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}, verify=False)
        env_result = resp.text
    elif context.remote_ip is not None:
        env_result = subprocess.check_output('ssh -p %s %s@%s "env"' % (peer['port'], context.remote_user, context.remote_ip),
                                             shell=True)
    elif 'docker-id' in peer:
        subprocess.call("docker start %s" % peer['docker-id'], shell=True)
        time.sleep(5)
        restart = subprocess.check_output("docker exec %s /usr/sbin/sshd" % peer['docker-id'], shell=True)
        print(restart)
        env_result = subprocess.check_output("docker exec %s env" % peer['docker-id'], shell=True)
    elif context.remote_ip is None:
        env_result = subprocess.check_output('ssh %s "env"' % peer['host'], shell=True)
    else:
        print("ERROR: Unable to access %s!!!" % peer['containerName'])
    return env_result

def get_peer_env(context, peer):
    if 'user' in peer:
        env_result = get_ssh_info(context, peer)
    elif 'docker-id' in peer:
        result = bdd_test_util.cli_call(context, ["docker", "exec", peer['docker-id'], "env"], expect_success=True)
        env_result = result[0]
    else:
        env_result = bdd_test_util.cli_call(context, ["vagrant", "ssh", "-c", "env"], expect_success=True)
    return env_result.splitlines()

def gather_peer_info(context, network, yaml_data):
    containerDataList = []

    for peer in network['PeerData']:
        url = peer['api-host']
        if ":" not in url:
            url = url + ":{0}".format(CORE_REST_PORT)
        ipAddress = peer['host']
        port = peer['port']
        env = get_peer_env(context, peer)

        service = "vp"
        docker_name = peer['name']
        for node in yaml_data.keys():
            name_match = re.match(r'\w+(?P<num>\d)', peer['name'])
            node_match = re.match(r'vp(?P<num>\d)', node)
            if node_match and name_match and node_match.group('num') == name_match.group('num') and 'extends' in yaml_data[node]:
                service = yaml_data[node]['extends']['service']
                docker_name = node
                break
            nvp_node_match = re.match(r'nvp(?P<num>\d)', node)
            num_containers = len(containerDataList)
            if len(containerDataList) == 0:
                last_container_name = ""
            else:
                last_container_name = containerDataList[-1].containerName
            if node not in last_container_name and nvp_node_match and 'extends' in yaml_data[node]:
                fig_peer = int(nvp_node_match.group('num')) + num_containers
                if str(fig_peer) in peer['name']:
                    service = yaml_data[node]['extends']['service']
                    docker_name = node
                    break

        containerDataList.append(ContainerData(peer['name']+"_"+docker_name,
                                 ipAddress,
                                 url,
                                 port,
                                 env,
                                 service,
                                 byon=context.byon,
                                 tls='TLS' in context.tags or context.tls))
    print("Initial containerList: {0}".format([container.containerName for container in containerDataList]))
    return containerDataList

def saveNetworkDataToContext(context):
    with open("networkcredentials", "r") as fd:
        network = json.loads(fd.read())

    compose_yaml = context.compose_yaml.split()
    yaml_data = {}
    for yaml_file in compose_yaml:
        with open(yaml_file) as data:
            if yaml_data == {}:
                yaml_data.update(yaml.safe_load(data))
            else:
                update_data = yaml.safe_load(data)
                for peer in yaml_data.keys():
                    if peer in update_data.keys():
                        yaml_data[peer].update(update_data[peer])

    print("Yaml info: {0}".format(yaml_data))
    containerDataList = gather_peer_info(context, network, yaml_data)
    context.containerCount = len(network['PeerData'])
    return containerDataList

def parseComposeOutput(context):
    """Parses the compose output results and set appropriate values into context.  Merges existing with newly composed."""
    if context.byon:
        containerDataList = saveNetworkDataToContext(context)
        print("Num of Containers: ", len(containerDataList))
    else:
        containerNames = getContainerNames(context)
        print("Containers started: \n", containerNames)
        containerDataList = saveContainerDataToContext(containerNames, context)

    # Now merge the new containerData info with existing
    newContainerDataList = []
    if "compose_containers" in context:
        # Need to merge I new list
        newContainerDataList = context.compose_containers
    newContainerDataList = newContainerDataList + containerDataList

    setattr(context, "compose_containers", newContainerDataList)
    print("")

def buildUrl(context, url, path):
    schema = "http"
    if 'TLS' in context.tags or context.tls:
        schema = "https"
    return "{0}://{1}{2}".format(schema, url, path)

def currentTime():
    return time.strftime("%H:%M:%S")

def getDockerComposeFileArgsFromYamlFile(compose_yaml):
    parts = compose_yaml.split()
    args = []
    for part in parts:
        args = args + ["-f"] + [part]
    return args

@given(u'we compose "{composeYamlFile}"')
def step_impl(context, composeYamlFile):
    print("BYON?????", str(context.byon))
    context.compose_yaml = composeYamlFile
    if not context.byon:
        fileArgsToDockerCompose = getDockerComposeFileArgsFromYamlFile(context.compose_yaml)
        context.compose_output, context.compose_error, context.compose_returncode = \
            bdd_test_util.cli_call(context, ["docker-compose"] + fileArgsToDockerCompose + ["up","--force-recreate", "-d"], expect_success=True)
        assert context.compose_returncode == 0, "docker-compose failed to bring up {0}".format(composeYamlFile)
    parseComposeOutput(context)
    time.sleep(10)       # Should be replaced with a definitive interlock guaranteeing that all peers/membersrvc are ready

@when(u'requesting "{path}" from "{containerName}"')
def step_impl(context, path, containerName):
    headers = {'Accept': 'application/json'}
    if context.byon and context.tls:
        headers = {'Accept': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}
    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)
    request_url = buildUrl(context, base_url, path)
    print("Requesting path = {0}".format(request_url))
    resp = requests.get(request_url, headers=headers, verify=False)
    assert resp.status_code == 200, "Failed to GET url %s:  %s" % (request_url,resp.text)
    context.response = resp
    print("")

@then(u'I should get a JSON response with "height" = "{expectedValue}"')
def step_impl(context, expectedValue):
    assert "height" in context.response.json(), "Attribute not found in response (height)"
    foundValue = context.response.json()["height"]
    if context.byon:
        print("Containers::", [(c.containerName, c.chainHeight) for c in context.compose_containers])
        prevHeight = str(context.compose_containers[0].chainHeight)
        print("Previous height:", prevHeight)
        print("New height:", str(int(prevHeight)+1))
        expected = int(prevHeight) + int(expectedValue)
        #assert (str(foundValue) in (prevHeight, str(expected))), "For attribute height, expected (%s), instead found (%s)" % (expected, foundValue)
        assert (foundValue > int(prevHeight)), "For attribute height, expected (%s), instead found (%s)" % (expected, foundValue)
    elif expectedValue == 'store':
        context.height = context.response.json()["height"]
        print("Stored height:", context.height)
    elif expectedValue == 'previous':
        assert (foundValue == context.height), "For attribute height, expected (%s), instead found (%s)" % (context.height, foundValue)
    else:
        assert (str(foundValue) == expectedValue), "For attribute height, expected (%s), instead found (%s)" % (expectedValue, foundValue)

@then(u'I should get a JSON response containing "{attribute}" attribute')
def step_impl(context, attribute):
    getAttributeFromJSON(attribute, context.response.json(), "Attribute not found in response (%s)" %(attribute))

@then(u'I should get a JSON response containing no "{attribute}" attribute')
def step_impl(context, attribute):
    try:
        getAttributeFromJSON(attribute, context.response.json(), "")
        assert None, "Attribute found in response (%s)" %(attribute)
    except AssertionError:
        print("Attribute not found as was expected.")

def getAttributeFromJSON(attribute, jsonObject, msg):
    return getHierarchyAttributesFromJSON(attribute.split("."), jsonObject, msg)

def getHierarchyAttributesFromJSON(attributes, jsonObject, msg):
    if len(attributes) > 0:
        print("Attr: {0}".format(attributes))
        print("Obj: {0}".format(jsonObject))
        assert attributes[0] in jsonObject, msg
        return getHierarchyAttributesFromJSON(attributes[1:], jsonObject[attributes[0]], msg)
    return jsonObject

def formatStringToCompare(value):
    # double quotes are replaced by simple quotes because is not possible escape double quotes in the attribute parameters.
    return str(value).replace("\"", "'")

@then(u'I should get a JSON response with "{attribute}" = "{expectedValue}"')
def step_impl(context, attribute, expectedValue):
    foundValue = getAttributeFromJSON(attribute, context.response.json(), "Attribute not found in response (%s)" %(attribute))
    assert (formatStringToCompare(foundValue) == expectedValue), "For attribute %s, expected (%s), instead found (%s)" % (attribute, expectedValue, foundValue)

@then(u'I should get a JSON response with array "{attribute}" contains "{expectedValue}" elements')
def step_impl(context, attribute, expectedValue):
    assert attribute in context.response.json(), "Attribute not found in response (%s)" %(attribute)
    #foundValue = context.response.json()[attribute]
    foundValue = getAttributeFromJSON(attribute, context.response.json(), "Attribute not found in response (%s)" %(attribute))
    if context.byon:
        assert (len(foundValue) == context.containerCount), "For attribute %s, expected array of size (%s), instead found (%s)" % (attribute, context.containerCount, len(foundValue))
    else:
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

@when(u'I deploy lang chaincode "{chaincodePath}" of "{chainLang}" with ctor "{ctor}" to "{containerName}"')
def step_impl(context, chaincodePath, chainLang, ctor, containerName):
    print("Printing chaincode language " + chainLang)
    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)
    #request_url = buildUrl(context, base_url, "/devops/deploy")
    request_url = buildUrl(context, base_url, "/chaincode")
    print("Requesting path = {0}".format(request_url))
    args = []
    if 'table' in context:
       # There is ctor arguments
       args = context.table[0].cells

    # Create a ChaincodeSpec structure
    chaincodeSpec = {
        "type": getChaincodeTypeValue(chainLang),
        "chaincodeID": {
            "path" : chaincodePath,
            "name" : ""
        },
        "ctorMsg":  {
            "function" : ctor,
            "args" : args
        },
    }
    if context.byon:
        chaincodeSpec["secureContext"] = get_primary_user(context)[0]
    elif 'userName' in context:
        chaincodeSpec["secureContext"] = context.userName

    chaincodeOpPayload = createChaincodeOpPayload("deploy", chaincodeSpec)

    resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(chaincodeOpPayload), verify=False)
    assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
    context.response = resp
    chaincodeName = resp.json()['result']['message']
    chaincodeSpec['chaincodeID']['name'] = chaincodeName
    context.chaincodeSpec = chaincodeSpec
    print(json.dumps(chaincodeSpec, indent=4))
    print("")

def get_primary_user(context):
    for user in context.user_creds:
        if user['peer'] == 'vp0':
            return (user['username'], user['secret'])
    return (context.user_creds[0]['username'], context.user_creds[0]['secret'])

@when(u'I deploy chaincode "{chaincodePath}" with ctor "{ctor}" to "{containerName}"')
def step_impl(context, chaincodePath, ctor, containerName):
    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)
    if context.byon:
        context = login(context, base_url)
    #request_url = buildUrl(context, base_url, "/devops/deploy")
    request_url = buildUrl(context, base_url, "/chaincode")
    print("Requesting path = {0}".format(request_url))
    args = []
    if 'table' in context:
          # There is ctor arguments
          args = context.table[0].cells
    typeGolang = 1

    # Create a ChaincodeSpec structure
    chaincodeSpec = {
        "type": typeGolang,
        "chaincodeID": {
            "path" : chaincodePath,
            "name" : ""
        },
        "ctorMsg":  {
            "function" : ctor,
            "args" : args
        },
#        "secureContext" : "binhn"
    }
    if context.byon:
        chaincodeSpec["secureContext"] = get_primary_user(context)[0]
    elif 'userName' in context:
        chaincodeSpec["secureContext"] = context.userName

    if 'metadata' in context:
        chaincodeSpec["metadata"] = context.metadata

    print("Chaincode specs = {0}".format(json.dumps(chaincodeSpec)))
    print("")

    #resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(chaincodeSpec), verify=False)
    chaincodeOpPayload = createChaincodeOpPayload("deploy", chaincodeSpec)

    resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(chaincodeOpPayload), verify=False)
    assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
    context.response = resp
    chaincodeName = resp.json()['result']['message']
    chaincodeSpec['chaincodeID']['name'] = chaincodeName
    context.chaincodeSpec = chaincodeSpec
    print(json.dumps(chaincodeSpec, indent=4))
    print("")

@then(u'I should have received a chaincode name')
def step_impl(context):
    if 'chaincodeSpec' in context:
        assert context.chaincodeSpec['chaincodeID']['name'] != ""
        # Set the current transactionID to the name passed back
        context.transactionID = context.chaincodeSpec['chaincodeID']['name']
    elif 'grpcChaincodeSpec' in context:
        assert context.grpcChaincodeSpec.chaincodeID.name != ""
        # Set the current transactionID to the name passed back
        context.transactionID = context.grpcChaincodeSpec.chaincodeID.name
    else:
        fail('chaincodeSpec not in context')

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" on "{containerName}" with "{idGenAlg}"')
def step_impl(context, chaincodeName, functionName, containerName, idGenAlg):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    invokeChaincode(context, "invoke", functionName, containerName, idGenAlg)

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" on "{containerName}" "{times}" times')
def step_impl(context, chaincodeName, functionName, containerName, times):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    for i in range(int(times)):
        invokeChaincode(context, "invoke", functionName, containerName)

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" with attributes "{attrs}" on "{containerName}"')
def step_impl(context, chaincodeName, functionName, attrs, containerName):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    assert attrs, "attrs were not specified"
    invokeChaincode(context, "invoke", functionName, containerName, None, attrs.split(","))

@when(u'I invoke chaincode "{chaincodeName}" function name "{functionName}" on "{containerName}"')
def step_impl(context, chaincodeName, functionName, containerName):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    invokeChaincode(context, "invoke", functionName, containerName)

@when(u'I invoke master chaincode "{chaincodeName}" function name "{functionName}" on "{containerName}"')
def step_impl(context, chaincodeName, functionName, containerName):
    invokeMasterChaincode(context, "invoke", chaincodeName, functionName, containerName)

@then(u'I should have received a transactionID')
def step_impl(context):
    assert 'transactionID' in context, 'transactionID not found in context'
    assert context.transactionID != ""
    pass

@when(u'I unconditionally query chaincode "{chaincodeName}" function name "{functionName}" on "{containerName}"')
def step_impl(context, chaincodeName, functionName, containerName):
    invokeChaincode(context, "query", functionName, containerName)

@when(u'I query chaincode "{chaincodeName}" function name "{functionName}" on "{containerName}"')
def step_impl(context, chaincodeName, functionName, containerName):
    invokeChaincode(context, "query", functionName, containerName)

def createChaincodeOpPayload(method, chaincodeSpec):
    chaincodeOpPayload = {
        "jsonrpc": JSONRPC_VERSION,
        "method" : method,
        "params" : chaincodeSpec,
        "id"     : 1
    }
    return chaincodeOpPayload

def invokeChaincode(context, devopsFunc, functionName, containerName, idGenAlg=None, attributes=[]):
    assert 'chaincodeSpec' in context, "chaincodeSpec not found in context"
    # Update the chaincodeSpec ctorMsg for invoke
    args = []
    if 'table' in context:
       # There is ctor arguments
       args = context.table[0].cells

    for idx, attr in enumerate(attributes):
        attributes[idx] = attr.strip()

    context.chaincodeSpec['ctorMsg']['function'] = functionName
    context.chaincodeSpec['ctorMsg']['args'] = args
    context.chaincodeSpec['attributes'] = attributes

    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)

    #If idGenAlg is passed then, we still using the deprecated devops API because this parameter can't be passed in the new API.
    if idGenAlg != None:
        invokeUsingDevopsService(context, devopsFunc, functionName, containerName, idGenAlg)
    else:
        invokeUsingChaincodeService(context, devopsFunc, functionName, containerName)

    if context.byon:
        print("containerName:", containerName)
        username = None
        for user in context.user_creds:
            if user['peer'] == containerName:
                username = user['username']
                secret = user['secret']
                context = login(context, base_url, username, secret)
                secretMsg = dict(enrollId=username, enrollSecret=secret)
                composeService = context.compose_containers[0].composeService
                for containerData in context.compose_containers:
                    if containerData.containerName == containerName:
                        composeService = containerData.composeService
                bdd_test_util.registerUser(context, secretMsg, composeService)
        context.chaincodeSpec["secureContext"] = username or get_primary_user(context)[0]
    elif 'userName' in context:
        context.chaincodeSpec["secureContext"] = context.userName

def invokeUsingChaincodeService(context, devopsFunc, functionName, containerName):
    headers = {'Content-type': 'application/json'}
    if context.byon and context.tls:
        headers = {'Content-type': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}
    # Invoke the POST
    chaincodeOpPayload = createChaincodeOpPayload(devopsFunc, context.chaincodeSpec)

    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)

    request_url = buildUrl(context, base_url, "/chaincode")
    print("{0} POSTing path = {1}".format(currentTime(), request_url))
    print("Using attributes {0}".format(context.chaincodeSpec['attributes']))

    resp = requests.post(request_url, headers=headers, data=json.dumps(chaincodeOpPayload), verify=False)
    assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
    context.response = resp
    print("RESULT from {0} of chaincode from peer {1}".format(functionName, containerName))
    print(json.dumps(context.response.json(), indent = 4))
    if 'result' in resp.json():
        result = resp.json()['result']
        if 'message' in result:
            transactionID = result['message']
            context.transactionID = transactionID

def invokeUsingDevopsService(context, devopsFunc, functionName, containerName, idGenAlg):
    # Invoke the POST
    chaincodeInvocationSpec = {
        "chaincodeSpec" : context.chaincodeSpec }
    if idGenAlg is not None:
	    chaincodeInvocationSpec['idGenerationAlg'] = idGenAlg

    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)
    request_url = buildUrl(context, base_url, "/devops/{0}".format(devopsFunc))
    print("{0} POSTing path = {1}".format(currentTime(), request_url))
    print("{0} POSTing data = {1}".format(currentTime(), chaincodeInvocationSpec))

    resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(chaincodeInvocationSpec), verify=False)
    assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
    context.response = resp
    print("RESULT from {0} of chaincode from peer {1}".format(functionName, containerName))
    print(json.dumps(context.response.json(), indent = 4))
    if 'message' in resp.json():
        transactionID = context.response.json()['message']
        context.transactionID = transactionID

def invokeMasterChaincode(context, devopsFunc, chaincodeName, functionName, containerName):
    args = []
    if 'table' in context:
       args = context.table[0].cells
    typeGolang = 1
    chaincodeSpec = {
        "type": typeGolang,
        "chaincodeID": {
            "name" : chaincodeName
        },
        "ctorMsg":  {
            "function" : functionName,
            "args" : args
        }
    }
    if context.byon:
        chaincodeSpec["secureContext"] = get_primary_user(context)[0]
    elif 'userName' in context:
        chaincodeSpec["secureContext"] = context.userName

    chaincodeOpPayload = createChaincodeOpPayload(devopsFunc, chaincodeSpec)
    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)
    #request_url = buildUrl(context, base_url, "/devops/{0}".format(devopsFunc))
    request_url = buildUrl(context, base_url, "/chaincode")
    print("{0} POSTing path = {1}".format(currentTime(), request_url))

    resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(chaincodeOpPayload), verify=False)
    assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
    context.response = resp
    print("RESULT from {0} of chaincode from peer {1}".format(functionName, containerName))
    print(json.dumps(context.response.json(), indent = 4))
    if 'result' in resp.json():
        result = resp.json()['result']
        if 'message' in result:
            transactionID = result['message']
            context.transactionID = transactionID

@then(u'I wait "{seconds}" seconds for chaincode to build')
def step_impl(context, seconds):
    """ This step takes into account the chaincodeImagesUpToDate tag, in which case the wait is reduce to some default seconds"""
    reducedWaitTime = 4
    if 'chaincodeImagesUpToDate' in context.tags:
        print("Assuming images are up to date, sleeping for {0} seconds instead of {1} in scenario {2}".format(reducedWaitTime, seconds, context.scenario.name))
        time.sleep(float(reducedWaitTime))
    else:
        time.sleep(float(seconds))

@then(u'I wait "{seconds}" seconds for transaction to be committed to block on "{containerName}"')
def step_impl(context, seconds, containerName):
    assert 'transactionID' in context, "transactionID not found in context"
    headers = {'Accept': 'application/json'}
    if context.byon and context.tls:
        headers = {'Accept': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}
    base_url = bdd_test_util.ipFromContainerNamePart(containerName, context.compose_containers, context.byon)
    request_url = buildUrl(context, base_url, "/transactions/{0}".format(context.transactionID))
    print("{0} GETing path = {1}".format(currentTime(), request_url))

    resp = requests.get(request_url, headers=headers, verify=False)
    assert resp.status_code == 200, "Failed to GET from %s:  %s" %(request_url, resp.text)
    context.response = resp

def multiRequest(context, seconds, containerDataList, pathBuilderFunc):
    """Perform a multi request against the system"""
    headers = {'Accept': 'application/json'}
    if context.byon and context.tls:
        headers = {'Accept': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}
    # Build map of "containerName" : response
    respMap = {container.containerName:None for container in containerDataList}
    # Set the max time before stopping attempts
    maxTime = datetime.now() + timedelta(seconds = int(seconds))
    for container in containerDataList:
        request_url = buildUrl(context, container.url, pathBuilderFunc(context, container))

        # Loop unless failure or time exceeded
        while (datetime.now() < maxTime):
            print("{0} GETing path = {1}".format(currentTime(), request_url))
            resp = requests.get(request_url, headers=headers, verify=False)
            respMap[container.containerName] = resp
        else:
            raise Exception("Max time exceeded waiting for multiRequest with current response map = {0}".format(respMap))

@then(u'I wait up to "{seconds}" seconds for transaction to be committed to all peers')
def step_impl(context, seconds):
    assert 'transactionID' in context, "transactionID not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"

    headers = {'Accept': 'application/json'}
    if context.byon and context.tls:
        headers = {'Accept': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}

    # Build map of "containerName" : resp.statusCode
    respMap = {container.containerName:0 for container in context.compose_containers}

    # Set the max time before stopping attempts
    maxTime = datetime.now() + timedelta(seconds = int(seconds))
    for container in context.compose_containers:
        request_url = buildUrl(context, container.url, "/transactions/{0}".format(context.transactionID))

        # Loop unless failure or time exceeded
        while (datetime.now() < maxTime):
            print("{0} GETing path = {1}".format(currentTime(), request_url))
            resp = requests.get(request_url, headers=headers, verify=False)
            if resp.status_code == 404:
                # Pause then try again
                respMap[container.containerName] = 404
                time.sleep(1)
                continue
            elif resp.status_code == 200:
                # Success, continue
                respMap[container.containerName] = 200
                break
            else:
                raise Exception("Error requesting {0}, returned result code = {1}".format(request_url, resp.status_code))
        else:
            raise Exception("Max time exceeded waiting for transactions with current response map = {0}".format(respMap))
    print("Result of request to all peers = {0}".format(respMap))
    print("")

@then(u'I check the transaction ID if it is "{tUUID}"')
def step_impl(context, tUUID):
    assert 'transactionID' in context, "transactionID not found in context"
    assert context.transactionID == tUUID, "transactionID is not tUUID"

def getContainerDataValuesFromContext(context, aliases, callback):
    """Returns the IPAddress based upon a name part of the full container name"""
    assert 'compose_containers' in context, "compose_containers not found in context"
    values = []
    containerNamePrefix = os.path.basename(os.getcwd()) + "_"
    for namePart in aliases:
        for containerData in context.compose_containers:
            if containerData.containerName.startswith(containerNamePrefix + namePart):
                values.append(callback(containerData))
                break
    return values

@then(u'I wait up to "{seconds}" seconds for transaction to be committed to peers that fail')
def step_impl(context, seconds):
    assert 'transactionID' in context, "transactionID not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    headers = {'Accept': 'application/json'}
    if context.byon and context.tls:
        headers = {'Accept': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}

    aliases =  context.table.headings
    containerDataList = getContainerDataValuesFromContext(context, aliases, lambda containerData: containerData)

    # Build map of "containerName" : resp.statusCode
    respMap = {container.containerName:0 for container in containerDataList}

    # Set the max time before stopping attempts
    maxTime = datetime.now() + timedelta(seconds = int(seconds))
    for container in containerDataList:
        request_url = buildUrl(context, container.url, "/transactions/{0}".format(context.transactionID))

        # Loop unless failure or time exceeded
        while (datetime.now() < maxTime):
            print("{0} GETing path = {1}".format(currentTime(), request_url))
            resp = requests.get(request_url, headers=headers, verify=False)
            if resp.status_code == 404:
                # Pause then try again
                respMap[container.containerName] = 404
                time.sleep(1)
                continue
            else:
                raise Exception("Error requesting {0}, returned result code = {1}".format(request_url, resp.status_code))
        else:
            assert respMap[container.containerName] in (404, 0), "response from transactions/{0}: {1}".format(context.transactionID, resp.status_code)
    print("Result of request to all peers = {0}".format(respMap))
    print("")

@then(u'I wait up to "{seconds}" seconds for transaction to be committed to peers')
def step_impl(context, seconds):
    assert 'transactionID' in context, "transactionID not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    headers = {'Accept': 'application/json'}
    if context.byon and context.tls:
        headers = {'Accept': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}

    aliases =  context.table.headings
    containerDataList = bdd_test_util.getContainerDataValuesFromContext(context, aliases, lambda containerData: containerData)

    # Build map of "containerName" : resp.statusCode
    respMap = {container.containerName:0 for container in containerDataList}

    # Set the max time before stopping attempts
    maxTime = datetime.now() + timedelta(seconds = int(seconds))
    for container in containerDataList:
        request_url = buildUrl(context, container.url, "/transactions/{0}".format(context.transactionID))

        # Loop unless failure or time exceeded
        while (datetime.now() < maxTime):
            print("{0} GETing path = {1}".format(currentTime(), request_url))
            resp = requests.get(request_url, headers=headers, verify=False)
            if resp.status_code == 404:
                # Pause then try again
                respMap[container.containerName] = 404
                time.sleep(1)
                continue
            elif resp.status_code == 200:
                # Success, continue
                respMap[container.containerName] = 200
                break
            else:
                raise Exception("Error requesting {0}, returned result code = {1}".format(request_url, resp.status_code))
        else:
            raise Exception("Max time exceeded waiting for transactions with current response map = {0}".format(respMap))
    print("Result of request to all peers = {0}".format(respMap))
    print("")


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
    if 'table' in context:
       # There is ctor arguments
       args = context.table[0].cells
    context.chaincodeSpec['ctorMsg']['function'] = functionName
    context.chaincodeSpec['ctorMsg']['args'] = args #context.table[0].cells if ('table' in context) else []
    # Invoke the POST
    chaincodeOpPayload = createChaincodeOpPayload("query", context.chaincodeSpec)

    responses = []
    for container in context.compose_containers:
        #request_url = buildUrl(context, container.url, "/devops/{0}".format(functionName))
        request_url = buildUrl(context, container.url, "/chaincode")
        print("{0} POSTing path = {1}".format(currentTime(), request_url))
        resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(chaincodeOpPayload), verify=False)
        assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
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

    aliases =  context.table.headings
    containerDataList = bdd_test_util.getContainerDataValuesFromContext(context, aliases, lambda containerData: containerData)
#    container_names = [container.containerName for container in containerDataList]
#    print("ContainerList: {0}".format(container_names))

    # Update the chaincodeSpec ctorMsg for invoke
    context.chaincodeSpec['ctorMsg']['function'] = functionName
    context.chaincodeSpec['ctorMsg']['args'] = [value]
    # Invoke the POST
    # Make deep copy of chaincodeSpec as we will be changing the SecurityContext per call.
    chaincodeOpPayload = createChaincodeOpPayload("query", copy.deepcopy(context.chaincodeSpec))

    responses = []
    for container in containerDataList:
        # Change the SecurityContext per call
        if container.composeService not in context.peerToSecretMessage:
            continue
        print("Secret Message: {0}".format(context.peerToSecretMessage))
        chaincodeOpPayload['params']["secureContext"] = context.peerToSecretMessage[container.composeService]['enrollId']
        print("Container {0} enrollID = {1}".format(container.containerName, container.getEnv("CORE_SECURITY_ENROLLID")))
        #request_url = buildUrl(context, container.url, "/devops/{0}".format(functionName))
        request_url = buildUrl(context, container.url, "/chaincode")
        print("{0} POSTing path = {1}".format(currentTime(), request_url))
        resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(chaincodeOpPayload), timeout=30, verify=False)
        if failOnError:
            assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
        print("RESULT from {0} of chaincode from peer {1}".format(functionName, container.containerName))
        print(json.dumps(resp.json(), indent = 4))
        responses.append(resp)
    context.responses = responses

@then(u'I should get a JSON response from all peers with "{attribute}" = "{expectedValue}"')
def step_impl(context, attribute, expectedValue):
    assert 'responses' in context, "responses not found in context"
    for resp in context.responses:
        foundValue = getAttributeFromJSON(attribute, resp.json(), "Attribute not found in response (%s)" %(attribute))
        assert (formatStringToCompare(foundValue) == expectedValue), "For attribute %s, expected (%s), instead found (%s)" % (attribute, expectedValue, foundValue)

@then(u'I should get a JSON response from peers with "{attribute}" = "{expectedValue}"')
def step_impl(context, attribute, expectedValue):
    assert 'responses' in context, "responses not found in context"
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"

    for resp in context.responses:
        foundValue = getAttributeFromJSON(attribute, resp.json(), "Attribute not found in response (%s)" %(attribute))
        assert (formatStringToCompare(foundValue) == expectedValue), "For attribute %s, expected (%s), instead found (%s)" % (attribute, expectedValue, foundValue)

def login(context, base_url, userName=None, secret=None):
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
    request_url = buildUrl(context, base_url, "/registrar")
    print("{0} POSTing path = {1}".format(currentTime(), request_url))

    print("secretMsg = {0}".format(secretMsg))
    print ("")

    resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(secretMsg), verify=False)
    assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
    context.response = resp
    print("message = {0}".format(resp.json()))
    return context

@given(u'I register with CA supplying username "{userName}" and secret "{secret}" on peers')
def step_impl(context, userName, secret):
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers) not found in context"
    print("Peer????: ", context.table.rows)

    # Get list of IPs to login to
    aliases =  context.table.headings
    containerDataList = bdd_test_util.getContainerDataValuesFromContext(context, aliases, lambda containerData: containerData)

    if context.byon:
        user_creds = get_primary_user(context)
        userName = user_creds[0]
        secret = user_creds[1]

    secretMsg = {
        "enrollId": userName,
        "enrollSecret" : secret
    }

    # Login to each container specified
    for containerData in containerDataList:
        context = login(context, containerData.url, userName, secret)
        # Create new User entry
        bdd_test_util.registerUser(context, secretMsg, containerData.composeService, expect_success=False)

    # Store the username in the context
    context.userName = userName
    context.secret = secret


@given(u'I use the following credentials for querying peers')
def step_impl(context):
    assert 'compose_containers' in context, "compose_containers not found in context"
    assert 'table' in context, "table (of peers, username, secret) not found in context"
    time.sleep(5)

    peerToSecretMessage = {}

    if context.byon:
        user_creds = context.user_creds
    else:
        user_creds = context.table.rows

    # Login to each container specified using username and secret
    #for row in context.table.rows:
    for row in user_creds:
        peer, userName, secret = row['peer'], row['username'], row['secret']
        secretMsg = {
            "enrollId": userName,
            "enrollSecret" : secret
        }

        base_url = bdd_test_util.ipFromContainerNamePart(peer, context.compose_containers, context.byon)
        request_url = buildUrl(context, base_url, "/registrar")
        print("POSTing to service = {0}, path = {1}".format(peer, request_url))

        print("secretMsg = {0}".format(secretMsg))
        print ("")
        resp = requests.post(request_url, headers={'Content-type': 'application/json'}, data=json.dumps(secretMsg), verify=False)
        assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
        context.response = resp
        print("message = {0}".format(resp.json()))
        peerToSecretMessage[peer] = secretMsg
        request_url = buildUrl(context, base_url, "/registrar/{0}/tcert".format(userName))
        resp = requests.get(request_url, headers={'Content-type': 'application/json'}, verify=False)
        print("TCERT??? {0}".format(resp))
    context.peerToSecretMessage = peerToSecretMessage


@given(u'I mount peer data')
def step_impl(context):
    for container in context.compose_containers:
        if container.containerName.startswith("vp"):
            compose_output, compose_error, compose_returncode = \
                 bdd_test_util.cli_call(context,
                                        ["docker", "create", "-v", "/var/hyperledger/test/behave/db", "--name", "{0}_dbstore".format(container.containerName), "hyperledger/fabric-peer", "/bin/true"],
                                        expect_success=True)
        else:
            compose_output, compose_error, compose_returncode = \
                 bdd_test_util.cli_call(context,
                                        ["docker", "create", "-v", "/var/hyperledger/test/behave/db", "--name", "{0}_dbstore".format(container.containerName), "hyperledger/fabric-membersrvc", "/bin/true"],
                                        expect_success=True)
        assert compose_returncode == 0, "docker create failed to create a volume for the behave transaction database"


def getNetworkCreds():
    network_creds = {}
    with open("membersrvc.yaml", "r") as fd:
        contents = fd.read()
        search_val = contents.find("users:")
        cred_val = contents[search_val:].find("test_vp")
        cred_info = contents[search_val + cred_val: search_val + cred_val + 200].split('\n')
    for cred in cred_info:
        if cred.strip() != '':
            values = cred.strip().split(":")
            pswd = values[1].split()
            network_creds[values[0]] = pswd[-1]
    print("network creds:{0}".format(network_creds))
    return network_creds


def getPeerFromName(containerName):
    name_pieces = containerName.split('_')
    if len(name_pieces) > 3 or 'dbstore' in name_pieces or 'membersrvc0' in name_pieces:
        return None
    return name_pieces[1]


def update_peers(context, prefix, tag, previous=None):
    new_container_names = []
    fileArgsToDockerCompose = getDockerComposeFileArgsFromYamlFile(context.compose_yaml)

    # Grab the username and secrets from membersrvc.yaml file
    network_creds = getNetworkCreds()

    # stop and start specified peers
    for container in context.compose_containers:
        peer = getPeerFromName(container.containerName)
        if peer is None:
            continue

        if not context.byon:
            # Stop the existing peers
            if previous is not None:
                res = subprocess.check_output(["docker", "stop", "%speer_%s" % (previous, peer)])
                print("Stopped {0}peer_{1}".format(previous, peer))
            else:
                compose_output, compose_error, compose_returncode = \
                    bdd_test_util.cli_call(context,
                                           ["docker-compose"] + fileArgsToDockerCompose + ["stop", peer],
                                           expect_success=True)
                assert compose_returncode == 0, "docker failed to stop peer {0}".format(peer)

            # Remove container from context list
            context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != peer]

            # Add the new container to the context list
            compose_output, compose_error, compose_returncode = \
                bdd_test_util.cli_call(context,
                                       ["docker", "run", "-d", "--name=%speer_%s" % (prefix, peer),
                                        "--volumes-from", "bddtests_dbstore_%s_1" % peer,
                                        "-e", "CORE_VM_ENDPOINT=http://172.17.0.1:2375",
                                        "-e", "CORE_PEER_ID=%s" % peer,
                                        "-e", "CORE_SECURITY_ENABLED=true",
                                        "-e", "CORE_SECURITY_PRIVACY=true",
                                        "-e", "CORE_PEER_ADDRESSAUTODETECT=true",
                                        "-e", "CORE_PEER_ADDRESS=172.17.0.1:5001",
                                        "-e", "CORE_PEER_PKI_ECA_PADDR=172.17.0.1:50051",
                                        "-e", "CORE_PEER_PKI_TCA_PADDR=172.17.0.1:50051",
                                        "-e", "CORE_PEER_PKI_TLSCA_PADDR=172.17.0.1:50051",
                                        "-e", "CORE_PEER_LISTENADDRESS=0.0.0.0:30303",
                                        "-e", "CORE_PEER_LOGGING_LEVEL=debug",
                                        "-e", "CORE_VM_DOCKER_TLS_ENABLED=false",
                                        "-e", "CORE_SECURITY_ENROLLID=test_%s" % peer,
                                        "-e", "CORE_SECURITY_ENROLLSECRET=%s" % network_creds['test_'+peer],
                                        "hyperledger/fabric-peer:%s" % tag, "peer", "node", "start"],
                                       expect_success=True)
        assert compose_returncode == 0, "docker run failed to bring up {0} image for {1}".format(prefix, peer)
        new_container_names.append("%speer_%s" % (prefix, peer))
    return new_container_names


@given(u'I build new images')
def step_impl(context):
    # Grab the last 2 commit SHAs
    prev_log = subprocess.check_output(["/usr/bin/git", "log", "-n", "2",
                                        "--oneline",
                                        "--no-abbrev-commit"])
    commit = prev_log.split()[0]
    print("current commit: {0}".format(commit))

    try:
        # Build a new caserver and peer image from the previous commit
        res = subprocess.check_output(['git', 'checkout', "%s~1" % commit])
        print("Git results: {0}".format(res))

        # Kill chaincode containers
        res = subprocess.check_output(["docker", "ps", "-n=4", "-q"])
        result = subprocess.check_output(["docker", "rm", "-f"] + res.split('\n'))

        # Kill chaincode images
        res = subprocess.check_output(["docker", "images", "|",
                                       "awk", "'$1 ~ /dev-vp/ { print $3}'"])
        result = subprocess.check_output(["docker", "rmi", "-f"] + res.split('\n'))

        # Build peer_beta
        output, error, returncode = bdd_test_util.cli_call(context,
                                   ["docker", "build",
                                    "-t", "hyperledger/fabric-peer:previous",
                                    "../build/image/peer"],
                                   expect_success=True)
        assert returncode == 0, "docker peer image not built correctly for previous commit"

        # Build membersrvc_beta
        output, error, returncode = bdd_test_util.cli_call(context,
                                   ["docker", "build",
                                    "-t", "hyperledger/fabric-membersrvc:previous",
                                    "../build/image/membersrvc"],
                                   expect_success=True)
        assert returncode == 0, "docker membersrvc image not built correctly for previous commit"
    except:
        pass
    finally:
        res = subprocess.check_output(['git', 'checkout', commit])


@given(u'I fallback')
def step_impl(context):
    fileArgsToDockerCompose = getDockerComposeFileArgsFromYamlFile(context.compose_yaml)

    # Stop membersrvc
    compose_output, compose_error, compose_returncode = \
        bdd_test_util.cli_call(context,
                               ["docker-compose"] + fileArgsToDockerCompose + ["stop", "membersrvc0"],
                               expect_success=True)
    assert compose_returncode == 0, "docker failed to stop membersrvc"
    print("Stopped membersrvc0")

    context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != "membersrvc0"]

    # Start membersrvc
    compose_output, compose_error, compose_returncode = \
        bdd_test_util.cli_call(context,
                               ["docker", "run", "-d",
                                "--volumes-from", "bddtests_dbstore_membersrvc0_1",
                                "--name=beta_membersrvc0",
                                "-p", "50051:50051",
                                "-p", "50052:30303",
                                "-it", "hyperledger/fabric-membersrvc:previous",
                                "membersrvc"],
                               expect_success=True)
    assert compose_returncode == 0, "docker failed to start membersrvc"

    # Update and Save the new containers to the context
    new_container_names = update_peers(context, "beta", "previous")
    new_containers = saveContainerDataToContext(new_container_names, context)
    context.compose_containers = context.compose_containers + new_containers 


@given(u'I upgrade')
def step_impl(context):
    # Verify that a latest build is present from the fallback scenario
    output, error, returncode = bdd_test_util.cli_call(context,
                                   ["docker", "images", "-q", "hyperledger/fabric-peer:latest"],
                                   expect_success=True)
    assert output != "", "There is no peer build with the 'latest' tag"
    assert returncode == 0, "docker peer image not built correctly for latest commit"
    output, error, returncode = bdd_test_util.cli_call(context,
                                   ["docker", "images", "-q", "hyperledger/fabric-membersrvc:latest"],
                                   expect_success=True)
    assert output != "", "There is no membersrvc build with the 'latest' tag"
    assert returncode == 0, "docker membersrvc image not built correctly for latest commit"

    # Stop membersrvc
    output, error, returncode = bdd_test_util.cli_call(context,
                               ["docker", "stop", "beta_membersrvc0"],
                               expect_success=False)
    assert returncode == 0, "docker failed to stop beta_membersrvc0"
    print("Stopped beta_membersrvc0")

    # Start membersrvc
    output, error, returncode = bdd_test_util.cli_call(context,
                               ["docker", "run", "-d",
                                "--volumes-from", "bddtests_dbstore_membersrvc0_1",
                                "--name=caserver_2",
                                "-p", "50051:50051",
                                "-p", "50052:30303",
                                "-it", "hyperledger/fabric-membersrvc:latest",
                                "membersrvc"],
                               expect_success=True)
    assert returncode == 0, "docker failed to start caserver_2"

    # Update and Save the new containers to the context
    new_container_names = update_peers(context, "new", "latest", previous="beta")
    new_containers = saveContainerDataToContext(new_container_names, context)
    context.compose_containers = context.compose_containers + new_containers 


@given(u'I stop peers')
def step_impl(context):
    compose_op(context, "stop")


@given(u'I start a listener')
def step_impl(context):
    gopath = os.environ.get('GOPATH')
    assert gopath is not None, "Please set GOPATH properly!"
    listener = os.path.join(gopath, "src/github.com/hyperledger/fabric/build/docker/bin/block-listener")
    assert os.path.isfile(listener), "Please build the block-listener binary!"
    bdd_test_util.start_background_process(context, "eventlistener", [listener, "-listen-to-rejections"] )


@given(u'I start peers')
def step_impl(context):
    compose_op(context, "start")

@given(u'I pause peers')
def step_impl(context):
    compose_op(context, "pause")

@given(u'I unpause peers')
def step_impl(context):
    compose_op(context, "unpause")

def compose_op(context, op):
    assert 'table' in context, "table (of peers) not found in context"
    assert 'compose_yaml' in context, "compose_yaml not found in context"

    fileArgsToDockerCompose = getDockerComposeFileArgsFromYamlFile(context.compose_yaml)
    services = context.table.headings
    # Loop through services and start/stop them, and modify the container data list if successful.
    for service in services:
       if context.byon:
           ipAddress = ""
           port = ""
           target = "vp0"
           for container in context.compose_containers:
               if service in container.containerName:
                   ipAddress = container.ipAddress
                   port = container.port
                   target = service
           print("target::", target)
           print("ipAddress::", ipAddress)
           print("port::", port)
           if context.tls:
               action = op
               if op == 'start':
                   action = 'restart'
               # Use a REST call to the correct interface in order to stop and start the peer
               request_url = buildUrl(context, context.remote_ip, "/api/com.ibm.zBlockchain/peers/{0}/{1}".format(target, action))
               print("{0} POSTing path = {1}".format(currentTime(), request_url))

               resp = requests.post(request_url, headers={'Content-type': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}, verify=False)
               assert resp.status_code == 200, "Failed to POST to %s:  %s" %(request_url, resp.text)
               result = resp.text
           elif context.remote_ip is not None:
               command = "sudo iptables -D INPUT -p tcp --destination-port 30303 -j DROP"
               result = subprocess.check_output('ssh -p %s %s@%s "%s"' % (port, context.remote_user, context.remote_ip, command), shell=True)
           else:
               command = "export SUDO_ASKPASS=~/.remote_pass.sh;sudo iptables -D INPUT -p tcp --destination-port 30303 -j DROP"
               result = subprocess.check_output('ssh %s "%s"' % (ipAddress, command), shell=True)
           print("Print:>>{0}<<".format(result))
           context.compose_returncode = 0
       else:
           context.compose_output, context.compose_error, context.compose_returncode = \
               bdd_test_util.cli_call(context, ["docker-compose"] + fileArgsToDockerCompose + [op, service], expect_success=True)
       assert context.compose_returncode == 0, "docker-compose failed to {0} {0}".format(op, service)
       if op == "stop" or op == "pause":
           context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != service]
       else:
           parseComposeOutput(context)
       print("After {0}ing, the container service list is = {1}".format(op, [containerData.composeService for  containerData in context.compose_containers]))
