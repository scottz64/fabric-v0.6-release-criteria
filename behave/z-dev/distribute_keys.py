#!/usr/bin/python
import json
import os
import sys
import subprocess
import getpass
import pexpect


def get_scp_commands(peer, cmds):
   env = {'home': os.environ['HOME'],
          'peer': peer['api-host']}
   cmd = 'ssh-keygen -f "%(home)s/.ssh/known_hosts" -R %(peer)s' % env
   cmds.append(cmd)
   cmd = "scp %(home)s/.ssh/id_rsa.pub %(peer)s:/tmp/id_rsa.pub" % env
   cmds.append(cmd)
   cmd = 'ssh %(peer)s "mkdir -p %(home)s/.ssh; chmod 700 %(home)s/.ssh;touch %(home)s/.ssh/authorized_keys;cat /tmp/id_rsa.pub >> %(home)s/.ssh/authorized_keys"' % env
   cmds.append(cmd)
   return cmds

def get_sshpass_commands(peer, cmds):
   cmd = ["ssh-keygen", "-f", '"/home/vagrant/.ssh/known_hosts"', "-R", peer['api-host']]
   cmds.append(" ".join(cmd))
   cmd = ["sshpass", "-e", "ssh-copy-id", "-i", "~/.ssh/id_rsa.pub", "-oStrictHostKeyChecking=no", peer['api-host']]
   cmds.append(" ".join(cmd))
   cmd = "scp .remote_pass.sh %s:~/.remote_pass.sh" % peer['api-host']
   cmds.append(cmd)
   return cmds

def use_scp(cmd):
   NEWKEY = r'Are you sure you want to continue connecting \(yes/no\)\?'
   print "Command:", cmd
   child = pexpect.spawn(cmd)
   retval = child.expect([pexpect.TIMEOUT, NEWKEY, ".*@.*'s password:"])
   if retval == 0:
      print("Got unexpected output: %s %s" % (child.before, child.after))
      sys.exit()
   elif retval == 1:
      child.sendline ('yes')
      child.expect([pexpect.TIMEOUT, NEWKEY, ".*@.*'s password:"])
   child.sendline(peer_password)
   print child.read()

def use_sshpass(cmds):
   with open(".remote_pass.sh", "w") as remote_file:
      remote_file.write("#!/bin/bash\n\necho %s" % peer_password)
   os.chmod("./.remote_pass.sh", 0700)

   with open("dist_keys.sh", "w") as fd:
      fd.write("\n".join(cmds))

   os.chmod("./dist_keys.sh", 0755)
   out = subprocess.check_output("./dist_keys.sh", shell=True)
   print out

   # Remove .sh scripts from local
   os.remove("./dist_keys.sh")
   os.remove("./.remote_pass.sh")

###################################################
peer_password = getpass.getpass("Peer Password: ")

cmds = []
peerData = []

with open("networkcredentials", "r") as fd:
   info = json.loads(fd.read())

# Check if sshpass installed on current system
try:
   sshpass_present = subprocess.check_output("which sshpass", shell=True)
except:
   sshpass_present = "no sshpass"

for peer in info["PeerData"]:
   if "no sshpass" in sshpass_present:
      cmds = get_scp_commands(peer, cmds)
   else:
      cmds = get_sshpass_commands(peer, cmds)

if "no sshpass" in sshpass_present:
   for cmd in cmds:
      if "ssh-keygen" in cmd:
         out = subprocess.check_output(cmd, shell=True)
         print out
      else:
         use_scp(cmd)
else:
   use_sshpass(cmds)
