#! /usr/bin/python

"""
Parse the DHCP leases file from the DHCP server and return a dict
mapping mac address to ip address

e.g output
mapping['00:01:02:03:04:05'] = 1.2.3.4
mapping['00:01:02:03:04:06'] = 1.2.3.5

Sample DHCP lease output
lease 172.21.158.113 {
  starts 3 2012/07/04 01:37:03;
  ends 3 2012/07/04 01:47:03;
  tstp 3 2012/07/04 01:47:03;
  cltt 3 2012/07/04 01:37:03;
  binding state free;
  hardware ethernet 00:0c:29:4b:ab:40;
  uid "\001\000\014)K\253@";
}
lease 172.21.158.118 {
  starts 5 2012/07/06 02:37:20;
  ends 5 2012/07/06 02:39:20;
  cltt 5 2012/07/06 02:37:20;
  binding state free;
  hardware ethernet cc:ef:48:b4:5a:5c;
}

Go through each line, once you see lease line make a note of the ip and
then look for hardware ethernet. map the ip to the hardware ethernet and
continue

"""

#import paramiko
import re
import pickle
import os

DHCP_SERVER = {
    'VM Network':{
        'server':['172.21.158.11'],
        'user':'tester',
        'password':'welcome123',
        'lease_file':'/var/lib/dhcp/dhcpd.leases'
    },
    'esx-mgmt-192':{
        'server':['172.21.158.25', '192.168.64.1'],
        'user':'root',
        'password':'welcome123',
        'lease_file':'/var/lib/dhcpd/dhcpd.leases'
    }
}

def get_mac_mapping(network_name=None, from_cache=True):
    if not DHCP_SERVER.has_key(network_name):
        return {}
    server_details = DHCP_SERVER[network_name]
    """Return a dict of mac and ip. keys are macs, values are ips"""

    cache_file = '/tmp/dhcp-leases-%s' % network_name

    if from_cache and os.path.exists(cache_file):
        fd = open(cache_file)
        mapping = pickle.load(fd)
        fd.close()
    else:
        dhcpServer = paramiko.SSHClient()
        dhcpServer.load_system_host_keys()
        dhcpServer.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        con_success = None
        for s in server_details['server']:
            try:
                dhcpServer.connect(s,
                                   username=server_details['user'],
                               password=server_details['password'])
            except Exception as e:
                print "Failed to connect to dhcp server", s
            else:
                con_success = True
                break
        if not con_success:
            raise e
        lease_file = server_details['lease_file']
        stdin,stdout,stderr = dhcpServer.exec_command("cat "+lease_file)

        lines = stdout.readlines()
        mapping = {}
        for line in lines:
            obj = re.search("lease\s+(.+)\s+{",line)
            if obj:
                ip = obj.group(1)
            obj = re.search("hardware\s+ethernet\s+(.+);",line)
            if obj:
                mac = obj.group(1)
                mapping[mac] = ip

        fd = open(cache_file, "wb")
        pickle.dump(mapping, fd)
        fd.close()

    return mapping

if __name__ == "__main__":
    import pprint
    pprint.pprint(get_mac_mapping('VM Network'))
