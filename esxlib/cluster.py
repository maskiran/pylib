import ssh
import hostsystem
import updatemor
import ssl
import hashlib

class Cluster:
    """Class to operate on the cluster"""

    def __init__(self,server_obj,datacenter_obj,cluster_mor):
        self._server = server_obj
        self.mor = cluster_mor
        self._host_folder = self.mor # cluster is the folder
        self._datacenter = datacenter_obj

    def get_moid(self, stringify=True):
        moid = self.mor._moId
        if stringify:
            moid = str(moid)
        return moid

    def delete(self,wait=True):
        """Delete the cluster"""
        tk = self.mor.Destroy_Task()
        if wait:
            tk = self._server.wait_for_task(tk)
        else:
            tk = self._server.add_task(tk)
        return tk

    def add_host(self,host,user='root',password='nbv12345',
            wait=True):
        """ Add the given host to the current cluster. Return the host
        object if wait=True or return the task object if wait=False"""

        host_spec = self._server.new_spec('HostConnectSpec')
        host_spec.force = True
        host_spec.hostName = host
        host_spec.userName = user
        host_spec.password = password
        host_spec.vmFolder = None

        """
        host_ssh = ssh.Client(host,user,password)
        host_spec.sslThumbprint =\
            host_ssh.get_ssl_thumbprint()
        """

        # http://www.vmware.com/support/developer/vc-sdk/visdk25pubs/ReferenceGuide/vim.host.ConnectSpec.html
        server_cert = ssl.get_server_certificate((host, 443))
        scsha1 = hashlib.sha1(ssl.PEM_cert_to_DER_cert(server_cert)).hexdigest()
        fmt = ':'.join([scsha1[i:i+2] for i,j in enumerate(scsha1) if not (i%2)])
        host_spec.sslThumbprint = fmt


        license = self._server._licenses['esx']
        tk = self.mor.AddHost_Task(spec=host_spec,
                asConnected=True,license=license)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
            host_obj = self.get_host(host)
            return host_obj
        else:
            tk = self._server.add_task(tk)
            return tk

    def get_host(self,name=None):
        """Returns all host objects or given host object under the
        current cluster"""
        host_list = []
        # childEntity.host is a list of hosts
        for host in self.mor.host:
            if not name or name == host.name:
                obj = hostsystem.Host(self._server,self._datacenter,host)
                host_list.append(obj)
                if name and name == host.name:
                    break
        if name and len(host_list):
            host_list = host_list[0]
        return host_list

    def update(self):
        updatemor.update(self)
