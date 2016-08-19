#!/usr/bin/python
import json
import getpass


z_network_file = raw_input("Please enter the name of the z-network file: ")
ip_address = raw_input("Please enter the 9.x IP address of the z-network to test: ")
username = raw_input("Please enter the username for the 9.x system [default=root]: ")
secret = getpass.getpass("Please enter the password: ")

with open(z_network_file, "r") as fd:
    network_info = json.loads(fd.read())

data = { "UserData": [], "PeerData": [] }
 
for ca in network_info['ca']:
    users = network_info['ca'][ca]['users']
    userInfo = []
    for user in users:
        if user.startswith("user_type1"):
            userInfo.append(dict(username=user, secret=users[user]))

rest_port = 20000
peerList = network_info['peers'].items()
for peerInfo in peerList:
    index = peerList.index(peerInfo)

    long_peerName = peerInfo[0].split('_')
    peerName = long_peerName[1]
    peerData = {'port': "unknown",
                'host': "internal",
                'api-host': "%s:%d" %(ip_address, rest_port),
                'name': peerName,
                'user': userInfo[0]['username']}
    userData = dict(peer=peerName,
                    username=userInfo[index]['username'],
                    secret=userInfo[index]['secret'])
    rest_port = rest_port + 100

    data['PeerData'].append(peerData)
    data['UserData'].append(userData)

data['CA_username'] = username or "root"
data['CA_secret'] = secret

with open("z_networkcredentials", "w") as fd:
   fd.write(json.dumps(data, indent=3))

