#!/usr/bin/python
import subprocess
import json
import os


docker_ls = subprocess.check_output(["docker", "ps"])
docker_lines = docker_ls.splitlines()

if len(docker_lines) <= 1:
    #subprocess.check_call(["./local_fabric.sh", "-n", "8", "-s"], cwd="/opt/gopath/src/github.com/hyperledger/fabric/obcsdk/chcotest")
    subprocess.check_call(["./local_fabric.sh", "-n", "8", "-s"])
    docker_ls = subprocess.check_output(["docker", "ps"])
    docker_lines = docker_ls.splitlines()

containers = []
for line in docker_lines[1:]:
   info = line.split("   ")
   data = [x for x in info if x != '']
   clean = dict(id=data[0].strip(),
                name=data[6].strip())
   containers.append(clean)

cmds = []
updated = {}
for container in containers:
   ip_str = subprocess.check_output(["docker", "inspect", container["id"]])
   ip_struct = json.loads(ip_str)
   ip = ip_struct[0]['NetworkSettings']['IPAddress']
   updated[container['name']] = dict(id=container['id'], ip=ip)
   subprocess.check_call(["docker", "exec", container['id'], "apt-get", "install", "--reinstall", "-y", "iptables"])
   subprocess.check_call(["docker", "exec", container['id'], "apt-get", "-y", "update"])
   subprocess.check_call(["docker", "exec", container['id'], "apt-get", "install", "-y", "openssh-server"])
   subprocess.check_call(["docker", "exec", container['id'], "mkdir", "/var/run/sshd"])
   subprocess.check_call(["docker", "exec", container['id'], "chmod", "0755", "/var/run/sshd"])
   subprocess.check_call(["docker", "exec", container['id'], "/usr/sbin/sshd"])
   subprocess.check_call(["docker", "exec", container['id'], "useradd", "--create-home", "--shell", "/bin/bash", "--groups", "sudo", "binhn", "-p", "$(echo '7avZQLwcUe9q' | openssl passwd -1 -stdin)"])
   cmd = ["docker", "exec", container['id'], "useradd", "--create-home", "--shell", "/bin/bash", "--groups", "sudo", "vagrant", "-p", "$(echo 'vagrant' | openssl passwd -1 -stdin)"]
   cmds.append(" ".join(cmd))
print ">>>\n", "\n".join(cmds)

with open("networkcredentials", "r") as fd:
   info = json.loads(fd.read())

print updated
print info
new = info.copy()
new["PeerData"] = []
for peer in info["PeerData"]:
   peer_struct = {'name': peer['name'],
                  'api-host': peer['api-host'],
                  'host': peer['api-host'],
                  'port': peer['api-port'],
                  'user': "vagrant"}
   docker_id = updated[peer['name']].get('id', None)
   if docker_id:
      peer_struct['docker-id'] = docker_id
   new["PeerData"].append(peer_struct)
   new["CA_username"] = 'vagrant'
   new["CA_secret"] = 'vagrant'

with open("docker_cmd.sh", "w") as fd:
   fd.write("\n".join(cmds))

os.chmod("./docker_cmd.sh", 0755)
out = subprocess.check_output("./docker_cmd.sh", shell=True)
print out

with open("networkcredentials", "w") as fd:
   fd.write(json.dumps(new, indent=3))
print new

# Remove .sh scripts from local
os.remove("./docker_cmd.sh")
