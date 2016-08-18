#!/usr/bin/python
import json


z_network_file = "sample.txt"
ip_address = "9.2.98.200"

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


with open("z_networkcredentials", "w") as fd:
   fd.write(json.dumps(data, indent=3))

