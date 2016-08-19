import subprocess
import os
import glob
import json
import requests

from steps.bdd_test_util import cli_call

from steps.coverage import saveCoverageFiles, createCoverageAggregate


def coverageEnabled(context):
    return context.config.userdata.get("coverage", "false") == "true"

def tlsEnabled(context):
    return context.config.userdata.get("tls", "false") == "true"

def ssh_call(context, command):
    context.remote_ip = context.config.userdata.get("remote-ip", None)
    context = get_remote_servers(context)
    for server in context.remote_servers:
        if context.remote_ip is not None:
            subprocess.call('ssh -p %s %s@%s "%s"' % (server['port'], context.remote_user, context.remote_ip, command), shell=True)
        else:
            subprocess.call("ssh %s: %s" % (server['ip'], command), shell=True)

def getDockerComposeFileArgsFromYamlFile(compose_yaml):
    parts = compose_yaml.split()
    args = []
    for part in parts:
        args = args + ["-f"] + [part]
    return args

def get_logs_from_peer_containers(containers, file_suffix):
    for containerData in containers:
        with open(containerData.containerName + file_suffix, "w+") as logfile:
            sys_rc = subprocess.call(["docker", "logs", containerData.containerName], stdout=logfile, stderr=logfile)
            if sys_rc !=0 :
                print("Cannot get logs for {0}. Docker rc = {1}".format(containerData.containerName,sys_rc))

def get_logs_from_chaincode_containers(context, file_suffix):
    cc_output, cc_error, cc_returncode = \
        cli_call(context, ["docker",  "ps", "-f",  "name=dev-", "--format", "{{.Names}}"], expect_success=True)
    for containerName in cc_output.splitlines():
        namePart,sep,junk = containerName.rpartition("-")
        with open(namePart + file_suffix, "w+") as logfile:
            sys_rc = subprocess.call(["docker", "logs", containerName], stdout=logfile, stderr=logfile)
            if sys_rc !=0 :
                print("Cannot get logs for {0}. Docker rc = {1}".format(namepart,sys_rc))

def retrieve_logs(context, scenario):
    file_suffix = "_" + scenario.name.replace(" ", "_") + ".log"
    if context.byon:
        print("Getting BYON logs".format(scenario.name))
        get_logs_from_network(context, file_suffix)
    else:
        print("Scenario {0} failed. Getting container logs".format(scenario.name))
        get_logs_from_peer_containers(context.compose_containers, file_suffix)
        get_logs_from_chaincode_containers(context, file_suffix)

def decompose_containers(context, scenario):
    fileArgsToDockerCompose = getDockerComposeFileArgsFromYamlFile(context.compose_yaml)

    print("Decomposing with yaml '{0}' after scenario {1}, ".format(context.compose_yaml, scenario.name))
    context.compose_output, context.compose_error, context.compose_returncode = \
        cli_call(context, ["docker-compose"] + fileArgsToDockerCompose + ["unpause"], expect_success=True)
    context.compose_output, context.compose_error, context.compose_returncode = \
        cli_call(context, ["docker-compose"] + fileArgsToDockerCompose + ["stop"], expect_success=True)

    #Save the coverage files for this scenario before removing containers
    if coverageEnabled(context):
        containerNames = [containerData.containerName for  containerData in context.compose_containers]
        saveCoverageFiles("coverage", scenario.name.replace(" ", "_"), containerNames, "cov")

    context.compose_output, context.compose_error, context.compose_returncode = \
        cli_call(context, ["docker-compose"] + fileArgsToDockerCompose + ["rm","-f"], expect_success=True)
    # now remove any other containers (chaincodes)
    context.compose_output, context.compose_error, context.compose_returncode = \
        cli_call(context, ["docker",  "ps",  "-qa"], expect_success=True)
    if context.compose_returncode == 0:
        # Remove each container
        for containerId in context.compose_output.splitlines():
            context.compose_output, context.compose_error, context.compose_returncode = \
                cli_call(context, ["docker",  "rm", "-f", containerId], expect_success=True)

##########################################
def get_remote_servers(context):
    with open("networkcredentials", "r") as network_file:
        network_creds = json.loads(network_file.read())
        context.remote_servers = [{'ip': peer['host'], 'port': peer['port']} for peer in network_creds['PeerData']]
        context.remote_user = network_creds["CA_username"]
        context.remote_secret = network_creds["CA_secret"]
        context.user_creds = network_creds['UserData']
    context.remote_ip = context.config.userdata.get("remote-ip", None)
    return context

def decompose_remote(context, scenario):
    print("Perform 'peer node pause' (through iptable block of 30303)")
    context.remote_ip = context.config.userdata.get("remote-ip", None)
    context = get_remote_servers(context)
    print("pause!!!")
    if context.tls and context.remote_ip:
        for target in ["vp0", "vp1", "vp2", "vp3"]:
            request_url = "https://{0}/api/com.ibm.zBlockchain/peers/{1}/restart".format(context.remote_ip, target)
            print("POSTing path = {0}".format(request_url))
            resp = requests.post(request_url, headers={'Content-type': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}, verify=False)
            print("Restart result:>>{0}<<".format(resp.text))
    else:
        command = " export SUDO_ASKPASS=~/.remote_pass.sh;sudo iptables -A INPUT -p tcp --destination-port 30303 -j DROP"
        ssh_call(context, command)

def get_logs_from_network(context, file_suffix):
    if context.tls and context.remote_ip:
        for target in ["vp0", "vp1", "vp2", "vp3"]:
            request_url = "https://{0}/api/com.ibm.zBlockchain/peers/{1}/logs".format(context.remote_ip, target)
            #"https://{0}/api/com.ibm.zBlockchain/networks/:network_id/peers/{1}/logs"
            print("GETing path = {0}".format(request_url))
            resp = requests.get(request_url, headers={'Content-type': 'application/json', 'zACI-API': 'com.ibm.zaci.system/1.0'}, verify=False)
            try:
                with open("REMOTE_PEER_{0}_{1}.log".format(context.remote_ip, target), "w") as fd:
                    fd.write(resp.text)
            except:
                print("response = {0}".format(resp.status_code))
                print("Unable to pull log through zACI API: {0}".format(resp.status_code))
    else:
        # SCP from the network
        print("SCP from nodes in the network...")
        info = dict(user=context.remote_user, ip=context.remote_ip)
        for peer in context.remote_servers:
            info['port'] = peer['port']
            if info['port'] == '5000':
                info['port'] = 22
                info['ip'] = peer['ip']
            command = "scp -P %(port)s %(user)s@%(ip)s:/srv/data/hyperledger/hyperledger.log REMOTE_PEER_%(ip)s_%(port)s.log" % info
            subprocess.call(command, shell=True)
##########################################

def after_scenario(context, scenario):
    get_logs = context.config.userdata.get("logs", "N")
    if get_logs.lower() == "force" or (scenario.status == "failed" and get_logs.lower() == "y"):
        # get logs
        retrieve_logs(context, scenario)
    if 'doNotDecompose' in scenario.tags and 'compose_yaml' in context:
        print("Not going to decompose after scenario {0}, with yaml '{1}'".format(scenario.name, context.compose_yaml))
    elif context.byon:
        print("Stopping a BYON (Bring Your Own Network) setup")
        retrieve_logs(context, scenario)
        decompose_remote(context, scenario)
    elif 'compose_yaml' in context:
        decompose_containers(context, scenario)
    else:
        print("Nothing to stop in this setup")

# stop any running peer that could get in the way before starting the tests
def before_all(context):
    context.byon = os.path.exists("networkcredentials")
    context.remote_ip = context.config.userdata.get("remote-ip", None)
    context.tls = tlsEnabled(context)
    print("TLS??", context.tls)
    if context.byon:
        context = get_remote_servers(context)
        if context.tls and context.remote_ip:
            print("Already restarted during 'pause'!!!")
        else:
            command = "export SUDO_ASKPASS=~/.remote_pass.sh;sudo iptables -D INPUT 1"
            ssh_call(context, command)
    else:
        cli_call(context, ["../build/bin/peer", "node", "stop"], expect_success=False)

# stop any running peer that could get in the way before starting the tests
def after_all(context):
    print("context.failed = {0}".format(context.failed))

    if coverageEnabled(context):
        createCoverageAggregate()
