import ssh
import hostsystem
import dvswitch
import cluster
import updatemor
import ssl
import hashlib

class Datacenter:
    """Class to operate on the datacenter"""

    def __init__(self,server_obj,dc_mor=None):
        self._server = server_obj
        self.mor = dc_mor

    def get_moid(self, stringify=True):
        moid = self.mor._moId
        if stringify:
            moid = str(moid)
        return moid

    def delete(self):
        """Delete the datacenter"""
        tk = self.mor.Destroy_Task()
        tk = self._server.wait_for_task(tk)
        return tk

    def add_cluster(self,name, drs_enable=False):
        """Adds a new cluster of the given name and return the cluster
        object"""
        # check if name already exists
        cl = self.get_cluster(name)
        if cl:
            return cl
        spec = self._server.new_spec('ClusterConfigSpecEx')

        #
        # Create config spec, that has DRS enabled. This is required by
        # vCD, to be able to use the resources of this cluster
        #
        # spec.vmSwapPlacement = "vmDirectory"
        # spec.dasConfig.enabled = True
        # spec.dasConfig.vmMonitoring = "vmMonitoringDisabled"
        # spec.dasConfig.hostMonitoring = "enabled"
        # spec.dasConfig.failoverLevel = 1
        # spec.dasConfig.defaultVmSettings.restartPriority = "medium"
        # spec.dasConfig.defaultVmSettings.isolationResponse = "none"
        # spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.enabled = False
        # spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.vmMonitoring = "vmMonitoringDisabled"
        # spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.clusterSettings = False
        # spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.failureInterval = 30
        # spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.minUpTime = 120
        # spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailures = 3
        # spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailureWindow = 3600

        # Lets optionally enable drs setting.
        if True == drs_enable:
            spec.drsConfig.enabled = True
            spec.drsConfig.enableVmBehaviorOverrides = True
            spec.drsConfig.defaultVmBehavior = "manual"
            spec.drsConfig.vmotionRate = 3

            # Let power management be disabled?
            spec.dpmConfig.enabled = False
            spec.dpmConfig.defaultDpmBehavior = "automated"
            spec.dpmConfig.hostPowerActionRate = 3

        self.mor.hostFolder.CreateClusterEx(name=name,spec=spec)
        self.update()
        return self.get_cluster(name)

    def reconfig_cluster(self, name, drs_enable=False):
        """Adds a new cluster of the given name and return the cluster
        object"""
        # check if name already exists
        cl = self.get_cluster(name)
        if cl is None:
            return None

        spec = self._server.new_spec('ClusterConfigSpecEx')

        # Lets optionally enable drs setting.
        spec.drsConfig.enabled = drs_enable
        spec.drsConfig.enableVmBehaviorOverrides = True
        spec.drsConfig.defaultVmBehavior = "manual"
        spec.drsConfig.vmotionRate = 3

        # Let power management be disabled?
        spec.dpmConfig.enabled = False
        spec.dpmConfig.defaultDpmBehavior = "automated"
        spec.dpmConfig.hostPowerActionRate = 3

        cl.mor.ReconfigureComputeResource_Task(spec=spec, modify=True)
        #self.mor.hostFolder.ReconfigureComputeResource_Task(spec=spec,
        #                                                    modify=True)
        self.update()
        return self.get_cluster(name)

    def get_cluster(self,name=None):
        """Return all clusters under this datacenter as a list of
        cluster objects or given cluster as cluster object"""
        objs = []
        for obj in self.mor.hostFolder.childEntity:
            if obj.__class__.__name__ != "vim.ClusterComputeResource":
                continue
            if not name or name == obj.name:
                objs.append(cluster.Cluster(self._server,self,obj))
                if name and name == obj.name:
                    break
        if name and len(objs):
            objs = objs[0]
        return objs

    def add_dvswitch(self,name,version):
        """Add a distributed virtual switch of the given name and
        version to the datacenter. Version string can be one of
        4.0, 4.1.0, 5.0.0, 5.1.0. It returns the dvs object"""
        # check if the name already exists
        dvs = self.get_dvswitch(name)
        if dvs:
            return dvs
        net_folder = self.mor.networkFolder
        spec = self._server.new_spec('DVSCreateSpec')
        spec.configSpec = self._server.new_spec('DVSConfigSpec')
        spec.configSpec.name = name
        spec.configSpec.configVersion = version
        tk = net_folder.CreateDVS_Task(spec=spec)
        self._server.wait_for_task(tk)
        self.update()
        dvs = self.get_dvswitch(name)
        dvs.rename_uplinks()
        return dvs

    def get_dvswitch(self,name=None,net_folder=None):
        """Return all dvs objects under this datacenter or dvs object of
        the given name"""
        self.update()
        objs = []
        if not net_folder:
            net_folder = self.mor.networkFolder
        vds_class = "vim.dvs.VmwareDistributedVirtualSwitch"
        for child in net_folder.childEntity:
            if child.__class__.__name__ == 'vim.Folder':
                # to get children dvswitch inside a folder
                cobjs = self.get_dvswitch(name,child)
                if isinstance(cobjs,list):
                    objs.extend(self.get_dvswitch(name,child))
                else:
                    objs.append(self.get_dvswitch(name,child))
                continue
            if child.__class__.__name__ != vds_class:
                continue
            if not name or child.name == name:
                objs.append(dvswitch.DVS(self._server,child))
                if name and child.name == name:
                    break
        if name and len(objs):
            objs = objs[0]
        return objs

    def add_host(self,host,user='root',password='nbv12345',
            wait=True):
        """ Add the given host under the current datacenter. 
        It returns the host object if wait=True or task object if
        wait=False"""

        # check if the host is already added
        h = self.get_host(host)
        if h:
            return h
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
        tk = self.mor.hostFolder.AddStandaloneHost_Task(spec=host_spec,
                addConnected=True,compResSpec=None,license=license)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
            host_obj = self.get_host(host)
            return host_obj
        else:
            tk = self._server.add_task(tk)
            return tk

    def get_host(self,name=None):
        """Returns all the hosts or given host under this datacenter"""
        # 2 scenarios
        # dc has clusters and clusters have hosts or 
        # dc has hosts
        # hosts are under childEntity of the dc hostFolder.
        # each childEntity under hostfolder is compute or cluster
        host_list = []
        for rsrc in self.mor.hostFolder.childEntity:
            if rsrc.__class__.__name__ not in\
                    ['vim.ClusterComputeResource','vim.ComputeResource']:
                continue
            # rsrc can be either cluster or compute. cluster or compute
            # has the hosts under it (compute has 1, cluster many)
            for host in rsrc.host:
                if not name or name == host.name:
                    obj = hostsystem.Host(self._server,self,host)
                    host_list.append(obj)
                    if name and name == host.name:
                        break
        if name and len(host_list):
            host_list = host_list[0]
        return host_list

    def update(self):
        updatemor.update(self)
