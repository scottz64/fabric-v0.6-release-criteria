#!/usr/bin/python
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
#
# Generating the networkcredentials file for use in the tests
# For zACI environment outside of BlueMix executing behave tests:
#     $ ./update_z.py -f <zACI network file name> --behave
#
# For X86 BlueMix environment:
#     $ ./update_z.py -b -f <BlueMix X86 file name>
#
# For available options, type:
#     $ ./update_z.py -h
#
# USAGE:
# 1. Create a text file "service_credentials_file" with the contents of your BlueMix network by using the
#    "service credentials" link/button at the bottom right corner of the Network tab of your IBM Blockchain network.
# 2. Use this script (named update_z.py) to generate the networkcredentials file by typing:
#        ./update_z.py -b -f service_credentials_file
# 3. Optionally copy it to ../util/    (optional since many test scripts will do that for you anyways):
#        cp networkcredentials ../util/NetworkCredentials.json. Many test scripts will do that for you anyways.
#

import json
import re
import getpass
import requests
from optparse import OptionParser


def handleOptions():
    '''Handle options'''
    parser = OptionParser(description='Process network files.')
    parser.add_option("-f", "--file", dest="network_file", default=None,
                      help="file containing network information for this remote network", metavar="NETWORK_FILE")
    parser.add_option("-i", "--ip", dest="ip_address", default=None,
                      help="9.x IP address of the remote network", metavar="IP_ADDRESS")
    parser.add_option("-u", "--user", dest="username", default="root",
                      help="username of the 9.x system in use", metavar="USERNAME")
    parser.add_option("-p", "--passwd", dest="secret", default=None,
                      help="password for the user of the 9.x system in use", metavar="PASSWORD")
    parser.add_option("-b", "--bluemix", dest="blue_mix", action="store_true", default=False,
                      help="set for a BlueMix formatted network file")
    parser.add_option("--behave", dest="behave", action="store_true", default=False,
                      help="set for a BlueMix formatted network file for behave tests")

    (options, args) = parser.parse_args()
    return options


def pullServiceCreds(network_id):
    '''Pull the service credentials file based on the network ID entered'''
    headers = {'Accept': 'application/json', 'Content-type': 'application/json'}
    resp = requests.get("https://obc-service-broker-prod.mybluemix.net/api/network/%s"%network_id, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    print "Unable to access the service credentials page. %d(%s): %s" % (resp.status_code, resp.reason, str(resp.content))


def readNetworkFile(network_file):
    '''Read the network file'''
    # Prompt if data is not present
    if network_file is None:
        network_file = raw_input("Please enter the name of the network file: ")

    # Read the given network file
    with open(network_file, "r") as fd:
        network_info = json.loads(fd.read())
    if 'credentials' in network_info.keys():
        return network_info['credentials']
    return network_info

 
def getUserData(network_info):
    '''Gather user data from the network file'''
    user_info = []

    for ca in network_info['ca']:
        users = network_info['ca'][ca]['users']
        for user in users:
            if user['username'].startswith("user_type1"):
                user_info.append(dict(username=user['username'], secret=user['secret']))
    return user_info


def getUserData_BM(users):
    '''Gather user data from the network file'''
    user_info = []

    for user in users:
        if user['username'].startswith("user_type1"):
            user_info.append(dict(username=user['username'], secret=user['secret']))
    return user_info


def saveData_BM(peerList, user_info):
    '''Save and format data for use in test'''
    data = { "UserData": [], "PeerData": [], "PeerGrpc": [] }

    # Save all the peer information for connecting to the peers
    grpc_port = 7051
    for peerInfo in peerList:
        index_match = re.match(r'.*-vp(?P<num>\d)-api.*', peerList[peerInfo].get('api_host', ""))
        index = index_match.group('num')
        peerName = "vp%s" % index

        url = peerList[peerInfo].get('url', '')
        port = peerList[peerInfo].get('api_port', '')

        data['PeerData'].append( {'name': 'PEER%s' % str(index),
                                  'api-port': str(peerList[peerInfo]["api_port"]),
                                  'api-host': peerList[peerInfo]['api_host']} )
        data['PeerGrpc'].append( {'api-host': peerList[peerInfo]['api_host'],
                                  'api-port': str(grpc_port)} )
        data['UserData'].append(dict(peer=peerName,
                        username=peerList[peerInfo]['security']['enrollId'],
                        secret=peerList[peerInfo]['security']['enrollSecret']))
        grpc_port = grpc_port + 2
    data['UserData'] = user_info
    #data['name'] = peerInfo["network_id"]
    data['name'] = network_info.get("lpar", "")
    return data


def saveData(options, peerList, user_info):
    '''Save and format data for use in test'''
    data = { "UserData": [], "PeerData": [] }

    ip_address = options.ip_address
    if not options.behave and not ip_address:
        ip_address = raw_input("Please enter the IP address for the system: ")

    # Save all the peer information for connecting to the peers
    rest_port = 20000
    for peerInfo in peerList:
        if isinstance(peerInfo, tuple):
            index = peerList.index(peerInfo)
            long_peerName = peerInfo[0].split('_')
            peerName = long_peerName[1]
        else:
            #index_match = re.match(r'.*-vp(?P<num>\d)-api.*', peerInfo.get('api_host', ""))
            index_match = re.match(r'.*-vp(?P<num>\d)-api.*', peerList[peerInfo].get('api_host', ""))
            index = index_match.group('num')
            peerName = "vp%s" % index

        if options.blue_mix:
            host = peerInfo.get('api_host', 'internal')
            url = "%(api_host)s:%(api_port)d" % peerInfo
            port = str(peerInfo['api_port'])
        elif ip_address is not None:
            host = ip_address
            url = "%s:%d" %(ip_address, rest_port)
            port = "unknown"
        else:
            host = peerList[peerInfo].get('api_host', 'internal')
            url = peerList[peerInfo].get('url', '')
            port = peerList[peerInfo].get('api_port', '')

        peerData = {'port': port,
                    'host': host,
                    'api-host': url,
                    'name': peerName}
        userData = dict(peer=peerName,
                        username=user_info[int(index)]['username'],
                        secret=user_info[int(index)]['secret'])
        #userData = dict(peer=peerName,
        #                username=peerList[peerInfo]['security']['enrollId'],
        #                secret=peerList[peerInfo]['security']['enrollSecret'])
        rest_port = rest_port + 100

        # Pull the user name for the vp0 user for all of the peers
        if peerName == 'vp0':
            main_user = user_info[int(index)]['username']
            #main_user = peerList[peerInfo]['security']['enrollId']

        data['PeerData'].append(peerData)
        data['UserData'].append(userData)
    return (main_user, data)


def savePrimaryUser(main_user, data):
    '''Save the user name for the vp0 user for all of the peers'''
    for peer in range(len(data['PeerData'])):
        data["PeerData"][peer]['user'] = main_user
    return data


def saveCAInfo(options, data, network_id="My Network"):
    '''Save the CA information for connecting to the peers'''
    username = options.username
    if username == "root":
        username = raw_input("Please enter the username for the 9.x system [default=root]: ")

    data['CA_username'] = username
    data['CA_secret'] = options.secret
    data['name'] = network_info.get("lpar", network_id)
    return data


def saveNetworkFile(data):
    '''Write new credentials file for use with behave tests'''
    with open("networkcredentials", "w") as fd:
       fd.write(json.dumps(data, indent=3))


if __name__ == "__main__":
    options = handleOptions()
    network_info = readNetworkFile(options.network_file)
    if options.blue_mix:
        #user_info = getUserData_BM(network_info['users'])
        user_info = getUserData(network_info)
        if options.behave:
            (main_user, data) = saveData(options, network_info["peers"], user_info)
            updated = savePrimaryUser(main_user, data)
            data = saveCAInfo(options, updated, network_info['peers'][0]['network_id'])
        else:
            data = saveData_BM(network_info["peers"], user_info)
    else:
        user_info = getUserData(network_info)
        #peerList = network_info['peers'].items()
        peerList = network_info['peers']
        (main_user, data) = saveData(options, peerList, user_info)
        updated = savePrimaryUser(main_user, data)
        data = saveCAInfo(options, updated)
    saveNetworkFile(data)
