#!/usr/bin/python
import json
import getpass
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

    (options, args) = parser.parse_args()
    return options


def readNetworkFile(network_file):
    '''Read the network file'''
    # Prompt if data is not present
    if network_file is None:
        network_file = raw_input("Please enter the name of the network file: ")

    # Read the given network file
    with open(network_file, "r") as fd:
        network_info = json.loads(fd.read())
    return network_info

 
def getUserData(network_info):
    '''Gather user data from the network file'''
    user_info = []

    for ca in network_info['ca']:
        users = network_info['ca'][ca]['users']
        for user in users:
            if user.startswith("user_type1"):
                user_info.append(dict(username=user, secret=users[user]))
    return user_info


def saveData(ip_address, network_info, user_info):
    '''Save and format data for use in test'''
    data = { "UserData": [], "PeerData": [] }

    if ip_address is None:
        ip_address = raw_input("Please enter the 9.x IP address of the z-network to test: ")

    # Save all the peer information for connecting to the peers
    rest_port = 20000
    peerList = network_info['peers'].items()
    for peerInfo in peerList:
        index = peerList.index(peerInfo)

        long_peerName = peerInfo[0].split('_')
        peerName = long_peerName[1]
        peerData = {'port': "unknown",
                    'host': "internal",
                    'api-host': "%s:%d" %(ip_address, rest_port),
                    'name': peerName}
        userData = dict(peer=peerName,
                        username=user_info[index]['username'],
                        secret=user_info[index]['secret'])
        rest_port = rest_port + 100

        # Pull the user name for the vp0 user for all of the peers
        if peerName == 'vp0':
            main_user = user_info[index]['username']

        data['PeerData'].append(peerData)
        data['UserData'].append(userData)
    return (main_user, data)


def savePrimaryUser(main_user, data):
    '''Save the user name for the vp0 user for all of the peers'''
    for peer in range(len(data['PeerData'])):
        data["PeerData"][peer]['user'] = main_user
    return data


def saveCAInfo(options, data):
    '''Save the CA information for connecting to the peers'''
    username = options.username
    if username == "root":
        username = raw_input("Please enter the username for the 9.x system [default=root]: ")

    secret = options.secret
    if secret is None:
        secret = getpass.getpass("Please enter the password: ")

    data['CA_username'] = username
    data['CA_secret'] = secret
    return data


def saveNetworkFile(data):
    '''Write new credentials file for use with behave tests'''
    with open("z_networkcredentials", "w") as fd:
       fd.write(json.dumps(data, indent=3))


if __name__ == "__main__":
    options = handleOptions()
    network_info = readNetworkFile(options.network_file)
    user_info = getUserData(network_info)
    (main_user, data) = saveData(options.ip_address, network_info, user_info)
    updated = savePrimaryUser(main_user, data)
    data = saveCAInfo(options, updated)
    saveNetworkFile(data)
