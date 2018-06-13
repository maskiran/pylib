import virtualmachine
import vswitch
import vportgroup
import datastore
import time
import updatemor
import ssh

class Host:
    """Class for the host system"""

    def __init__(self,server_obj,datacenter_obj,host_mor=None):
        self._server = server_obj
        self._datacenter = datacenter_obj
        self.mor = host_mor
        self.user_name = ""
        self.password = ""
        self.ssh_handle = None

    def get_moid(self, stringify=True):
        moid = self.mor._moId
        if stringify:
            moid = str(moid)
        return moid

    def shell_cmd(self, cmd, user='root', password='nbv12345'):
        if not self.user_name:
            self.user_name = user
        if not self.password:
            self.password = password
        if not self.ssh_handle:
            self.ssh_handle = ssh.Client(self.mor.name, user, password)

        op = []
        out,err = self.ssh_handle.execute(cmd)
        out_op = out.read()
        err_op = err.read()
        if out_op:
            op.append(out_op)
        if err_op:
            op.append(err_op)
        return "\n".join(op)

    def delete(self,wait=True):
        """ Remove the current host"""
        # if the parent is cluster, then just remove the host
        # if the parent is compute resource then delete that
        if self.mor.parent.__class__.__name__ == "vim.ComputeResource":
            # not in cluster, so delete the parent computer resource
            tk = self.mor.parent.Destroy_Task()
        else:
            # as part of cluster
            t = self.mor.DisconnectHost_Task()
            self._server.wait_for_task(t)
            tk = self.mor.Destroy_Task()
        if wait:
            tk = self._server.wait_for_task(tk)
        else:
            tk = self._server.add_task(tk)
        return tk

    def disconnect_host(self,wait=True):
        """ Remove the current host"""
        # if the parent is cluster, then only allow to disconnect
        # TODO: if the parent is compute resource then do disconnect
        if self.mor.parent.__class__.__name__ != "vim.ComputeResource":
            # as part of cluster
            t = self.mor.DisconnectHost_Task()
        if wait:
            tk = self._server.wait_for_task(t)
        else:
            tk = self._server.add_task(t)
        return tk

    def connect_host(self,wait=True):
        """ Remove the current host"""
        # if the parent is cluster, then only allow to disconnect
        # TODO: if the parent is compute resource then do disconnect
        if self.mor.parent.__class__.__name__ != "vim.ComputeResource":
            # as part of cluster
            t = self.mor.ReconnectHost_Task()
        if wait:
            tk = self._server.wait_for_task(t)
        else:
            tk = self._server.add_task(t)
        return tk

    def get_vm(self,name=None):
        """Return all the vm objects or a given vm object under this
        host""" 
        vm_objs = []
        for vm in self.mor.vm:
            if not name or name == vm.name:
                obj = virtualmachine.VirtualMachine(self._server,vm)
                vm_objs.append(obj)
                if name and name == vm.name:
                    break;
        if name and len(vm_objs):
            vm_objs = vm_objs[0]
        return vm_objs

    def register_vm(self,name_or_path,wait=True):
        """Register a vm into the host. The vm can be provided either as
        a name or the path. If the name is provided, then its assumed to
        be present in the local datastore and in the folder as name and
        the vmx file with same name. If a path is provided, then its
        taken as is"""
        path = name_or_path
        if not name_or_path.startswith("["):
            name = name_or_path
            # name provided
            paths = self.search_datastore(name)
            if not paths:
                paths = self.search_datastore(name, refresh=True)
            path = paths[0]
            path += "/" + name + ".vmx"
        # register this under the datacenter's vmfolder
        tk = self._datacenter.mor.vmFolder.RegisterVM_Task(path=path,
                host=self.mor,asTemplate=False,
                pool=self.mor.parent.resourcePool)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
            return tk
        else:
            tk = self._server.add_task(tk)
            return tk
    
    # another method to register_vm
    attach_vm = register_vm

    def add_vswitch(self,name=None,num_ports=120):
        """Add a vswitch of the given name and return the object. If
        num_ports is none, then the default value by esx is assumed.
        num_ports is the total port count on the vswitch. esx reserves 8
        for uplink. so add 8 to the given number here. If the user wanted
        24 ports, then 32 is the value to be sent"""
        num_ports += 8
        spec = None
        if num_ports:
            spec = self._server.new_spec("HostVirtualSwitchSpec")
            spec.numPorts = num_ports

        self.mor.configManager.networkSystem.AddVirtualSwitch(vswitchName=name,spec=spec)
        self.update()
        return self.get_vswitch(name)

    def get_vswitch(self,name=None):
        """Return all vswitch objects or a given vswitch object under
        this host"""
        objs = []
        for i in self.mor.configManager.networkSystem.networkConfig.vswitch:
            if not name or (i.name == name):
                objs.append(vswitch.Vswitch(self._server,self,i))
                if name and i.name == name:
                    break
        if name and len(objs):
            objs = objs[0]
        return objs

    def get_network(self,name=None):
        """Return the network mors under the current host. There is no
        network object. It returns the standard mor to the network"""
        objs = []
        for i in self.mor.network:
            if not name or name == i.name:
                objs.append(i)
                if name and name == i.name:
                    break
        if name and len(objs):
            objs = objs[0]
        return objs

    def add_network_datastore(self,label,server,path,
            type='nfs',userName=None,password=None):
        """Add network storage onto the host.
        server is the name/ip of the nas server. 
        path is the remote path on the server to be mounted onto the host.
        label is the local name of this storage. 
        type can be nfs (default) or cifs
        For cifs, userName and password can be provided
        It returns the datastore object"""
        ds = self.get_datastore(label=label)
        if ds:
            return ds
        spec = self._server.new_spec("HostNasVolumeSpec")
        spec.accessMode = "readWrite"
        spec.localPath = label
        spec.remoteHost = server
        spec.remotePath = path
        ds_mor = self.mor.configManager.datastoreSystem.CreateNasDatastore(spec=spec)
        self.update()
        return datastore.Datastore(self._server,self,ds_mor)

    def get_datastore(self,label=None):
        """Return all datastore objects or a given datastore object"""
        objs = []
        for ds in self.mor.configManager.datastoreSystem.datastore:
            if not label or ds.name == label:
                objs.append(datastore.Datastore(self._server,self,ds))
                if label and ds.name == label:
                    break
        if label and len(objs):
            objs = objs[0]
        return objs

    def search_datastore(self,pattern,folder=None,refresh=False):
        """Search for the pattern in all the datastores and return the
        results as paths. Optionally can specify the parent folder"""
        paths = []
        for ds in self.get_datastore():
            file_list = ds.search(pattern, folder, refresh)
            paths.extend(file_list)
        return paths

    def enable_vmotion(self):
        nic = self.mor.configManager.virtualNicManager
        nic.SelectVnicForNicType(nicType='vmotion',device='vmk0')
        return

    def disable_vmotion(self):
        nic = self.mor.configManager.virtualNicManager
        nic.DeselectVnicForNicType(nicType='vmotion',device='vmk0')
        return

    def create_vm(self,name,datastore_obj,memory_mb,no_cpus,wait=True):
        """datastore_obj is obtained from the call to get_datastore"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.name = name
        spec.memoryMB = memory_mb
        spec.numCPUs = no_cpus
        # guestId is enum of VirtualMachineGuestOsIdentifier
        spec.guestId = 'centosGuest'
        spec.files = self._server.new_spec('VirtualMachineFileInfo')
        spec.files.vmPathName = "[%s] %s" % (datastore_obj.mor.name,name)
        tk = self._datacenter.mor.vmFolder.CreateVM_Task(config=spec,
                pool=self.mor.parent.resourcePool,host=self.mor)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def update(self):
        updatemor.update(self)

    def exit_maintenance_mode(self,wait=True):
        tk = self.mor.ExitMaintenanceMode_Task(timeout=90)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def enter_maintenance_mode(self,wait=True):
        tk = self.mor.EnterMaintenanceMode_Task(timeout=90)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def get_pnics(self):
        """
        Get all the pnics found for this host
        """
        pnics = []
        if self.mor.runtime.connectionState != "connected":
            return pnics

        config = self.mor.config
        if 'network' not in config.__dict__:
            return pnics

        network = config.network
        if 'pnic' not in network.__dict__:
            return pnics

        return network.pnic

