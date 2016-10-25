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

import os, time, re, requests
import json, yaml, subprocess

import bdd_remote_util
from bdd_request_util import httpGetToContainer, CORE_REST_PORT
from bdd_json_util import getAttributeFromJSON
from bdd_test_util import cli_call, bdd_log

class Container:
    def __init__(self, name, ipAddress, envFromInspect, composeService, byon=False, tls=False):
        self.name = name
        self.ipAddress = ipAddress
        self.envFromInspect = envFromInspect
        self.composeService = composeService

    def getEnv(self, key):
        envValue = None
        for val in self.envFromInspect:
            if val.startswith(key):
                envValue = val[len(key):]
                break
        if envValue == None:
            raise Exception("ENV key not found ({0}) for container ({1})".format(key, self.name))
        return envValue

    def __str__(self):
        return "{} - {}".format(self.name, self.ipAddress)

    def __repr__(self):
        return self.__str__()

DOCKER_COMPOSE_FOLDER = "bdd-docker"

def getDockerComposeFileArgsFromYamlFile(compose_yaml):
    parts = compose_yaml.split()
    args = []
    for part in parts:
        part = "{}/{}".format(DOCKER_COMPOSE_FOLDER, part)
        args = args + ["-f"] + [part]
    return args

def saveContainerDataToContext(containerNames, context):
    """ Now get the Network Address for each name, and set the ContainerData onto the context."""
    containerDataList = []
    for containerName in containerNames:
        ipAddress = getIpFromContainerName(containerName)
        env = getEnvironmentVariablesFromContainerName(containerName)
        dockerComposeService = getDockerComposeServiceForContainer(containerName)
        containerDataList.append(Container(containerName, ipAddress, env, dockerComposeService, tls=context.tls))
    return containerDataList

def parseComposeOutput(context):
    """Parses the compose output results and set appropriate values into context.  Merges existing with newly composed."""
    if context.byon:
        containerDataList = saveNetworkDataToContext(context)
        bdd_log("Num of Containers: {0}".format(len(containerDataList)))
    else:
        containerNames = getContainerNamesFromContext(context)
        bdd_log("Containers started: {0} \n".format(containerNames))
        containerDataList = saveContainerDataToContext(containerNames, context)

    # Now merge the new containerData info with existing
    newContainerDataList = []
    if "compose_containers" in context:
        # Need to merge I new list
        newContainerDataList = context.compose_containers
    newContainerDataList = newContainerDataList + containerDataList

    setattr(context, "compose_containers", newContainerDataList)
    bdd_log("")


def getContainerNamesFromContext(context):
    containerNames = []
    for l in context.compose_error.splitlines():
        tokens = l.split()
        bdd_log("DEBUG:: {}".format(tokens))

        if len(tokens) > 1:
            thisContainer = tokens[1]
            if "containerAliasMap" in context:
               thisContainer = context.containerAliasMap.get(tokens[1], tokens[1])

            if thisContainer not in containerNames:
               containerNames.append(thisContainer)

    return containerNames

def getIpFromContainerName(containerName):
    output, error, returncode = \
            cli_call(["docker", "inspect", "--format",  "{{ .NetworkSettings.IPAddress }}", containerName], expect_success=False)
    bdd_log("container {0} has address = {1}".format(containerName, output.splitlines()[0]))

    return output.splitlines()[0]

def getEnvironmentVariablesFromContainerName(containerName):
    output, error, returncode = \
            cli_call(["docker", "inspect", "--format",  "{{ .Config.Env }}", containerName], expect_success=False)
    env = output.splitlines()[0][1:-1].split()
    bdd_log("container {0} has env = {1}".format(containerName, env))

    return env

def getDockerComposeServiceForContainer(containerName):
    # Get the Labels to access the com.docker.compose.service value
    output, error, returncode = \
        cli_call(["docker", "inspect", "--format",  "{{ .Config.Labels }}", containerName], expect_success=True)
    labels = output.splitlines()[0][4:-1].split()
    compose_info = [composeService[27:] for composeService in labels if composeService.startswith("com.docker.compose.service:")]

    if compose_info == []:
        dockerComposeService = extractAliasFromContainerName(containerName)
    else:
        dockerComposeService = compose_info[0]
    bdd_log("dockerComposeService = {0}".format(dockerComposeService))

    return dockerComposeService

def allContainersAreReadyWithinTimeout(context, timeout):
    timeoutTimestamp = time.time() + timeout
    formattedTime = time.strftime("%X", time.localtime(timeoutTimestamp))
    bdd_log("All containers should be up by {}".format(formattedTime))

    allContainers = context.compose_containers

    for container in allContainers:
        if 'dbstore' in container.name:
            allContainers.remove(container)
        elif not containerIsInitializedByTimestamp(container, timeoutTimestamp):
            return False

    bdd_log("All containers remaining: {}".format(allContainers))
    peersAreReady = peersAreReadyByTimestamp(context, allContainers, timeoutTimestamp)

    if peersAreReady:
        bdd_log("All containers in ready state, ready to proceed")

    return peersAreReady

def containerIsInitializedByTimestamp(container, timeoutTimestamp):
    while containerIsNotInitialized(container):
        if timestampExceeded(timeoutTimestamp):
            bdd_log("Timed out waiting for {} to initialize".format(container.name))
            return False

        bdd_log("{} not initialized, waiting...".format(container.name))
        time.sleep(1)

    bdd_log("{} now available".format(container.name))
    return True

def timestampExceeded(timeoutTimestamp):
    return time.time() > timeoutTimestamp

def containerIsNotInitialized(container):
    return not containerIsInitialized(container)

def containerIsInitialized(container):
    isReady = tcpPortsAreReady(container)
    isReady = isReady and restPortRespondsIfContainerIsPeer(container)

    return isReady

def tcpPortsAreReady(container):
    netstatOutput = getContainerNetstatOutput(container.name)

    for line in netstatOutput.splitlines():
        if re.search("ESTABLISHED|LISTEN", line):
            return True

    bdd_log("No TCP connections are ready in container {}".format(container.name))
    return False

def getContainerNetstatOutput(containerName):
    command = ["docker", "exec", containerName, "netstat", "-atun"]
    stdout, stderr, returnCode = cli_call(command, expect_success=False)

    return stdout

def restPortRespondsIfContainerIsPeer(container):
    containerName = container.name
    command = ["docker", "exec", containerName, "curl", "localhost:{}".format(CORE_REST_PORT)]

    if containerIsPeer(container):
        stdout, stderr, returnCode = cli_call(command, expect_success=False)

        if returnCode != 0:
            bdd_log("Connection to REST Port on {} failed".format(containerName))

        return returnCode == 0

    return True

def peersAreReadyByTimestamp(context, containers, timeoutTimestamp):
    peers = getPeerContainers(containers)
    bdd_log("Detected Peers: {}".format(peers))

    for peer in peers:
        if not peerIsReadyByTimestamp(context, peer, peers, timeoutTimestamp):
            return False

    return True

def getPeerContainers(containers):
    peers = []

    for container in containers:
        if containerIsPeer(container):
            peers.append(container)

    return peers

def containerIsPeer(container):
    # This is not an ideal way of detecting whether a container is a peer or not since
    # we are depending on the name of the container. Another way of detecting peers is
    # is to determine if the container is listening on the REST port. However, this method
    # may run before the listening port is ready. Hence, as along as the current
    # convention of vp[0-9] is adhered to this function will be good enough.
    if 'dbstore' not in container.name:
        return re.search("vp[0-9]+", container.name, re.IGNORECASE)
    return False

def peerIsReadyByTimestamp(context, peerContainer, allPeerContainers, timeoutTimestamp):
    while peerIsNotReady(context, peerContainer, allPeerContainers):
        if timestampExceeded(timeoutTimestamp):
            bdd_log("Timed out waiting for peer {}".format(peerContainer.name))
            return False

        bdd_log("Peer {} not ready, waiting...".format(peerContainer.name))
        time.sleep(1)

    bdd_log("Peer {} now available".format(peerContainer.name))
    return True

def peerIsNotReady(context, thisPeer, allPeers):
    return not peerIsReady(context, thisPeer, allPeers)

def peerIsReady(context, thisPeer, allPeers):
    connectedPeers = getConnectedPeersFromPeer(context, thisPeer)

    if connectedPeers is None:
        return False

    numPeers = len(allPeers)
    numConnectedPeers = len(connectedPeers)

    if numPeers != numConnectedPeers:
        bdd_log("Expected {} peers, got {}".format(numPeers, numConnectedPeers))
        bdd_log("Connected Peers: {}".format(connectedPeers))
        bdd_log("Expected Peers: {}".format(allPeers))

    return numPeers == numConnectedPeers

def getConnectedPeersFromPeer(context, thisPeer):
    response = httpGetToContainer(context, thisPeer, "/network/peers")

    if response.status_code != 200:
        return None

    return getAttributeFromJSON("peers", response.json())

def mapAliasesToContainers(context):
    aliasToContainerMap = {}

    for container in context.compose_containers:
        alias = extractAliasFromContainerName(container.name)
        aliasToContainerMap[alias] = container

    return aliasToContainerMap

def extractAliasFromContainerName(containerName):
    """ Take a compose created container name and extract the alias to which it
        will be refered. For example bddtests_vp1_0 will return vp0 """
    return containerName.split("_")[1]

def mapContainerNamesToContainers(context):
    nameToContainerMap = {}

    for container in context.compose_containers:
        name = container.name
        nameToContainerMap[name] = container

    return nameToContainerMap

def get_ssh_info(context, peer):
    env_result = ''
    if context.remote_ip:
        bdd_log("Peer: {}".format(peer))
        status = bdd_remote_util.getNodeStatus(context, peer['name'])
        env_result = status.json()[peer['name']]
        time.sleep(2)
#    elif context.remote_ip is not None:
#        env_result = subprocess.check_output('ssh -p %s %s@%s "env"' % (peer['port'], context.remote_user, context.remote_ip),
#                                             shell=True)
    elif 'docker-id' in peer:
        subprocess.call("docker start %s" % peer['docker-id'], shell=True)
        time.sleep(5)
        restart = subprocess.check_output("docker exec %s /usr/sbin/sshd" % peer['docker-id'], shell=True)
        bdd_log(restart)
        env_result = subprocess.check_output("docker exec %s env" % peer['docker-id'], shell=True)
    elif context.remote_ip is None:
        env_result = subprocess.check_output('ssh %s "env"' % peer['host'], shell=True)
    else:
        bdd_log("ERROR: Unable to access %s!!!" % peer['containerName'])
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
            # Get container name
            num_containers = len(containerDataList)
            if len(containerDataList) == 0:
                last_container_name = ""
            else:
                last_container_name = containerDataList[-1].name

            name_match = re.match(r'\w+(?P<num>\d)', peer['name'])
            node_match = re.match(r'vp(?P<num>\d)', node)
            nvp_node_match = re.match(r'nvp(?P<num>\d)', node)
            if node_match and name_match and node_match.group('num') == name_match.group('num') and 'extends' in yaml_data[node]:
                service = yaml_data[node]['extends']['service']
                if service == "vpBatch":
                    service = node
                docker_name = node
                break
            if nvp_node_match and node not in last_container_name and 'extends' in yaml_data[node]:
                fig_peer = int(nvp_node_match.group('num')) + num_containers
                if str(fig_peer) in peer['name']:
                    service = yaml_data[node]['extends']['service']
                    if service == "vpBatch":
                        service = node
                    docker_name = node
                    break

        bdd_log("Service used: {0}".format(service))
#        containerDataList.append(ContainerData(peer['name']+"_"+docker_name,
#                                 ipAddress,
#                                 url,
#                                 port,
#                                 env,
#                                 service,
#                                 byon=context.byon,
#                                 tls='TLS' in context.tags or context.tls))
        containerDataList.append(Container(peer['name']+"_"+docker_name,
                                 ipAddress,
                                 env,
                                 service,
                                 byon=context.byon,
                                 tls='TLS' in context.tags or context.tls))
    bdd_log("Initial containerList: {0}".format([container.name for container in containerDataList]))
    return containerDataList

def saveNetworkDataToContext(context):
    with open("networkcredentials", "r") as fd:
        network = json.loads(fd.read())

    compose_yaml = context.compose_yaml.split()
    yaml_data = {}
    for yaml_file in compose_yaml:
        with open("{}/{}".format(DOCKER_COMPOSE_FOLDER, yaml_file)) as data:
            if yaml_data == {}:
                yaml_data.update(yaml.safe_load(data))
            else:
                update_data = yaml.safe_load(data)
                for peer in yaml_data.keys():
                    if peer in update_data.keys():
                        yaml_data[peer].update(update_data[peer])

    bdd_log("Yaml info: {0}".format(yaml_data))
    containerDataList = gather_peer_info(context, network, yaml_data)
    context.containerCount = len(network['PeerData'])
    return containerDataList

def getContainerDataValuesFromContext(context, aliases, callback):
    """Returns the IPAddress based upon a name part of the full container name"""
    assert 'compose_containers' in context, "compose_containers not found in context"
    values = []
    containerNamePrefix = os.path.basename(os.getcwd()) + "_"
    for namePart in aliases:
        for containerData in context.compose_containers:
            if containerData.name.startswith(containerNamePrefix + namePart):
                values.append(callback(containerData))
                break
    return values

def update_peers(context, prefix, tag, previous=None):
    new_container_names = []
    fileArgsToDockerCompose = getDockerComposeFileArgsFromYamlFile(context.compose_yaml)

    # Grab the username and secrets
    network_creds = {}
    for row in context.table.rows:
        network_creds[row['username']] = row['secret']
    bdd_log("network creds: {}".format(network_creds))

    bdd_log("containers: {}".format(context.compose_containers))
    # stop and start specified peers
    for container in context.compose_containers:
        peer = extractAliasFromContainerName(container.name)
        if peer in [None, 'dbstore', 'membersrvc']:
            continue

        # Stop the existing peers
        if previous is not None:
            res, error, returncode = cli_call(
                                       ["docker", "stop", "%speer_%s" % (previous, peer)],
                                       expect_success=True)
            bdd_log("Stopped {0}peer_{1}".format(previous, peer))
        else:
            compose_output, compose_error, compose_returncode = \
                cli_call(["docker-compose"] + fileArgsToDockerCompose + ["stop", peer],
                         expect_success=True)
            assert compose_returncode == 0, "docker failed to stop peer {0}".format(peer)

    sorted_containers = sorted(context.compose_containers, key=lambda container: container.name)
    for container in sorted_containers:
        peer = extractAliasFromContainerName(container.name)
        if peer in [None, 'dbstore', 'membersrvc']:
            #context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != peer]
            context.compose_containers.remove(container)
            continue

        #get membersrvc IP
        ms_ip = getIpFromContainerName("%s_membersrvc0" % prefix)

        # Remove container from context list
        context.compose_containers = [containerData for containerData in context.compose_containers if containerData.composeService != peer]

        # Get peer number
        match = re.match('vp(?P<index>\d)', peer)
        index = match.groupdict()['index']
        # Add the new container to the context list
        command = ["docker", "run", "-d", "--name=%speer_%s" % (prefix, peer),
                      "--volumes-from", "bdddocker_dbstore_%s_1" % peer,
                      "-v", "/var/run/:/host/var/run/",
                      "--link", "%s_membersrvc0" % prefix,
                      "-e", "CORE_PEER_ADDRESSAUTODETECT=true",
                      #"-e", "CORE_VM_ENDPOINT=http://172.17.0.1:2375",
                      "-e", "CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock",
                      "-e", "CORE_LOGGING_LEVEL=DEBUG",
                      "-e", "CORE_PEER_LOGGING_LEVEL=debug",
                      "-e", "CORE_SECURITY_ENABLED=true",
                      "-e", "CORE_PEER_PKI_ECA_PADDR=%s:7054" % ms_ip,
                      "-e", "CORE_PEER_PKI_TCA_PADDR=%s:7054" % ms_ip,
                      "-e", "CORE_PEER_PKI_TLSCA_PADDR=%s:7054" % ms_ip,
                      "-e", "CORE_PEER_PKI_TLS_ROOTCERT_FILE=./bddtests/tlsca.cert",
                      #"-e", "CORE_SECURITY_PRIVACY=true",
                      #"-e", "CORE_PEER_VALIDATOR_CONSENSUS_PLUGIN=pbft",
                      #"-e", "CORE_PBFT_GENERAL_TIMEOUT_REQUEST=10s",
                      #"-e", "CORE_PBFT_GENERAL_MODE=batch",
                      #"-e", "CORE_PBFT_GENERAL_BATCHSIZE=1",
                      #"-e", "CORE_PEER_LISTENADDRESS=0.0.0.0:7051",
                      #"-e", "CORE_VM_DOCKER_TLS_ENABLED=false",
                      "-e", "CORE_PBFT_GENERAL_N=4",
                      "-e", "CORE_PBFT_GENERAL_K=2",
                      "-e", "CORE_PEER_ID=%s" % peer,
                      "-e", "CORE_SECURITY_ENROLLID=test_%s" % peer,
                      "-e", "CORE_SECURITY_ENROLLSECRET=%s" % network_creds['test_'+peer],
                      "hyperledger/fabric-peer:%s" % tag, "peer", "node", "start"]
        if int(index) != 0:
            vp0_ip = getIpFromContainerName("%speer_vp0" % prefix)
            first_env_var = command.index('-e')
            command.insert(first_env_var, "CORE_PEER_DISCOVERY_ROOTNODE=%s:7051" % vp0_ip)
            command.insert(first_env_var, "-e")
        bdd_log("Command: {}".format(command))
        compose_output, compose_error, compose_returncode = \
            cli_call(command,
#            cli_call(["docker", "run", "-d", "--name=%speer_%s" % (prefix, peer),
#                      "--volumes-from", "bdddocker_dbstore_%s_1" % peer,
#                      #"--volumes-from", "dbstore_%s" % peer,
#                      "--link", "%s_membersrvc0" % prefix,
#                      "-e", "CORE_VM_ENDPOINT=http://172.17.0.1:2375",
#                      "-e", "CORE_PEER_ID=%s" % peer,
#                      "-e", "CORE_SECURITY_ENABLED=true",
#                      "-e", "CORE_SECURITY_PRIVACY=true",
#                      "-e", "CORE_PEER_ADDRESSAUTODETECT=true",
#                      "-e", "CORE_PEER_PKI_ECA_PADDR=172.17.0.1:7054",
#                      "-e", "CORE_PEER_PKI_TCA_PADDR=172.17.0.1:7054",
#                      "-e", "CORE_PEER_PKI_TLSCA_PADDR=172.17.0.1:7054",
#                      "-e", "CORE_PEER_LISTENADDRESS=0.0.0.0:7051",
#                      "-e", "CORE_PEER_LOGGING_LEVEL=debug",
#                      "-e", "CORE_VM_DOCKER_TLS_ENABLED=false",
#                      "-e", "CORE_SECURITY_ENROLLID=test_%s" % peer,
#                      "-e", "CORE_SECURITY_ENROLLSECRET=%s" % network_creds['test_'+peer],
#                      #"-e", "CORE_SECURITY_ENROLLID=test_user%s" % index,
#                      #"-e", "CORE_SECURITY_ENROLLSECRET=%s" % network_creds['test_user'+index],
#                      "hyperledger/fabric-peer:%s" % tag, "peer", "node", "start"],
                      expect_success=True)
        assert compose_returncode == 0, "docker run failed to bring up {0} image for {1}".format(prefix, peer)
        new_container_names.append("%speer_%s" % (prefix, peer))
    return new_container_names
