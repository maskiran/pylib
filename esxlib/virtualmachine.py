import dhcp
import updatemor

class VirtualMachine:

    def __init__(self,server_obj,vm_mor=None):
        self._server = server_obj
        self.mor = vm_mor
        self._mgmt_ip = None
        self._mgmt_network = None

    def get_moid(self, stringify=True):
        moid = self.mor._moId
        if stringify:
            moid = str(moid)
        return moid

    def power_off(self,wait=True):
        """ Power off the current vm"""
        self.update()
        state = self.mor.runtime.powerState
        tk = None
        if state != "poweredOff":
            tk = self.mor.PowerOffVM_Task()
            if wait:
                tk = self._server.wait_for_task(tk)
            else:
                tk = self._server.add_task(tk)
        return tk

    def power_on(self,wait=True):
        """ Power on the given vm"""
        self.update()
        state = self.mor.runtime.powerState
        tk = None
        if state != "poweredOn":
            tk = self.mor.PowerOnVM_Task()
            if wait:
                tk = self._server.wait_for_task(tk)
            else:
                tk = self._server.add_task(tk)
        return tk

    def suspend(self,wait=True):
        """ Suspend the current vm"""
        self.update()
        state = self.mor.runtime.powerState
        tk = None
        if state != "suspended":
            tk = self.mor.SuspendVM_Task()
            if wait:
                tk = self._server.wait_for_task(tk)
            else:
                tk = self._server.add_task(tk)
        return tk

    def clone(self,name,dest_host=None,wait=True,datastore=None):
        """Clone to the new name. If the dest_host object is provided,
        the clone is added to the given dest_host. 
        datastore is the destination datastore object. If its not
        provided, then the clone is created in the same location as the
        current vm.
        It returns the task
        object. (To get the new vm object use get_vm of the host)"""
        rspec = self._server.new_spec("VirtualMachineRelocateSpec")
        if dest_host:
            rspec.host = dest_host.mor
            rspec.pool = dest_host.mor.parent.resourcePool
        else:
            rspec.host = None
            rspec.pool = self.mor.resourcePool
        rspec.transform = None
        rspec.datastore = None
        if datastore:
            rspec.datastore = datastore.mor
        cspec = self._server.new_spec("VirtualMachineCloneSpec")
        cspec.powerOn = False
        cspec.snapshot = None
        cspec.template = False
        cspec.config = None
        cspec.customization = None
        cspec.location = rspec
        # TODO this should be done better
        # depending on cluster or root, this changes
        if hasattr(self.mor.parent.parent, 'vmFolder'):
            # not cluster
            folder = self.mor.parent.parent.vmFolder # data center folder
        if hasattr(self.mor.parent.parent.parent, 'vmFolder'):
            # cluster
            folder = self.mor.parent.parent.parent.vmFolder # data center folder
        if dest_host:
            if hasattr(dest_host.mor.parent.parent.parent, 'vmFolder'):
                # not cluster
                folder = dest_host.mor.parent.parent.parent.vmFolder # data center folder
            if hasattr(dest_host.mor.parent.parent.parent.parent, 'vmFolder'):
                # cluster
                folder = dest_host.mor.parent.parent.parent.parent.vmFolder # data center folder
        tk = self.mor.CloneVM_Task(name=name,spec=cspec,folder=folder)
        if wait:
            tk = self._server.wait_for_task(tk)
        else:
            tk = self._server.add_task(tk)
        return tk

    def delete(self,wait=True):
        """Delete the current vm"""
        self.power_off()
        tk = self.mor.Destroy_Task()
        if wait:
            tk = self._server.wait_for_task(tk)
        else:
            tk = self._server.add_task(tk)
        return tk

    def unregister(self):
        """Unregister the VM. The files are not deleted but just
        unregistered from the host and vcenter"""
        self.power_off()
        self.mor.UnregisterVM()
        return

    # another method to unregister
    detach = unregister

    def get_mgmt_mac(self):
        """Get the mac address of the interface connected to the
        management (VM Network) network or esx-mgmt-192 network.
        If multiple interfaces are connected to vm network,
        returns the first one found. If a vm has both the networks then
        VM Network interface is returned"""
        mac = None
        for dev in self.mor.config.hardware.device:
            if dev.deviceInfo.summary == "VM Network":
                # found the vm network, so break after getting the mac
                mac = dev.macAddress
                self._mgmt_network = "VM Network"
                break
            if dev.deviceInfo.summary == "esx-mgmt-192":
                mac = dev.macAddress
                self._mgmt_network = "esx-mgmt-192"
                # i might find a VM Network, so continue searching
        return mac
        
    def get_all_macs(self):
        """Get all the mac addresses of the interfaces"""
        macs = {}
        for dev in self.mor.config.hardware.device:
            if hasattr(dev,'macAddress'):
                macs[dev.deviceInfo.summary] = dev.macAddress
        return macs
        
    def get_dhcp_assigned_mgmt_ip(self):
        """Returns the IP address assigned to the vm by DHCP server.
        This is usually for the management network. It queries the DHCP
        server for the ip assigned to the mac address and returns
        that"""
        if not self._mgmt_ip:
            # based on the network type, the mapping has to be obtained
            # from a different server
            if hasattr(self.mor.guest,'ipAddress') and self.mor.guest.ipAddress:
                self._mgmt_ip = self.mor.guest.ipAddress
            else:
                mac = self.get_mgmt_mac()
                mapping = dhcp.get_mac_mapping(self._mgmt_network)
                if mac not in mapping:
                    mapping = dhcp.get_mac_mapping(self._mgmt_network,
                                                   from_cache=False)
                self._mgmt_ip = mapping.get(mac)
        return self._mgmt_ip

    def get_all_dhcp_ips(self):
        """Returns the IP addresses assigned to the vm by DHCP server"""
        ips = []
        if hasattr(self.mor.guest,'net'):
            for net in self.mor.guest.net:
                if not hasattr(net,'ipAddress'):
                    continue
                for ip in net.ipAddress:
                    # ignore ipv6 for now
                    if ip.find(':') >= 0:
                        continue
                    ips.append(ip)
        if not ips:
            # if the lookup from guest tools fails, try from DHCP
            # based on the network type, the mapping has to be obtained
            # from a different server
            macs = self.get_all_macs()
            for network in macs:
                mapping = dhcp.get_mac_mapping(network)
                if mapping.has_key(macs[network]):
                    ips.append(mapping.get(macs[network]))
        return ips

    def add_nic(self,network=None,wait=True):
        """Adds a network adapter to the vm and maps it to the given
        network mor. The network mor is obtained from the call to the
        get_network under host"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        deviceChange.operation = "add"
        deviceChange.fileOperation = None
        deviceChange.device = self._server.new_spec('VirtualE1000')
        deviceChange.device.backing = self._server.new_spec('VirtualEthernetCardNetworkBackingInfo')
        deviceChange.device.backing.network = network
        deviceChange.device.backing.deviceName = network.name
        #spec.deviceChange.device.connectable.connected = True
        #spec.deviceChange.device.connectable.startConnected = True
        #spec.deviceChange.device.connectable.allowGuestControl = True
        spec.deviceChange.append(deviceChange)
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def delete_nic(self, network=None, label=None, wait=True):
        """Deletes a network adapter on the vm thats on the given
        network mor. The network mor is obtained from the call to the
        get_network under host. The first adapter matching the network
        is deleted. If a label is provided, the adapter matching the
        label is deleted"""
        key = None
        for dev in self.mor.config.hardware.device:
            if network:
                if dev.deviceInfo.summary == network.name:
                    key = dev.key
            elif label:
                if dev.deviceInfo.label == label:
                    key = dev.key
            if key:
                break
        if not key:
            return None
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        deviceChange.operation = "remove"
        deviceChange.fileOperation = None
        deviceChange.device = self._server.new_spec('VirtualE1000')
        deviceChange.device.key = key
        spec.deviceChange.append(deviceChange)
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def add_lsi_sas_controller(self):
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        deviceChange.operation = "add"
        deviceChange.fileOperation = None
        deviceChange.device = self._server.new_spec('VirtualLsiLogicSASController')
        deviceChange.device.sharedBus = 'noSharing'
        spec.deviceChange.append(deviceChange)
        tk = self.mor.ReconfigVM_Task(spec=spec)
        tk = self._server.wait_for_task(tk)
        self.update()
        return tk

    def add_disk(self,size_kb,name=None,unit=0,wait=True):
        """Adds a Hard disk of the given size in KB
        """
        if not name:
            name = self.mor.name
        path = self.mor.summary.config.vmPathName.split("/")[:-1]
        path = "/".join(path)
        path += "/" + name + ".vmdk"
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        deviceChange.operation = "add"
        deviceChange.fileOperation = "create"
        deviceChange.device = self._server.new_spec('VirtualDisk')
        deviceChange.device.capacityInKB = size_kb
        for cntrl in self.mor.config.hardware.device:
            if cntrl.deviceInfo.label.startswith('SCSI'):
                deviceChange.device.controllerKey = cntrl.key
                break
        deviceChange.device.backing = self._server.new_spec('VirtualDiskFlatVer2BackingInfo')
        deviceChange.device.backing.fileName = path
        deviceChange.device.backing.diskMode = "persistent"
        deviceChange.device.backing.split = False
        deviceChange.device.backing.writeThrough = False
        deviceChange.device.backing.thinProvisioned = True
        deviceChange.device.unitNumber = unit
        spec.deviceChange.append(deviceChange)
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def list_nic(self):
        nics = {}
        for device in self.mor.config.hardware.device:
            if device.deviceInfo.label.startswith('Network'):
                nics[device.deviceInfo.label] = device
        return nics
   
    def change_macs(self, nic_dict, wait=True):
        """Change the mac address of the given network adapters"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        for (nic, addrType, mac) in nic_dict:
            deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
            deviceChange.operation = "edit"
            deviceChange.fileOperation = None
            # find the nic device with the given name
            nic_device = None
            adapterType = None
            for device in self.mor.config.hardware.device:
                if device.deviceInfo.label == nic:
                    adapterType = (device.__class__.__name__).split(".")[-1]
                    nic_device = device
                    break
            if nic_device and adapterType:   
                deviceChange.device = self._server.new_spec(adapterType)
                deviceChange.device.key = nic_device.key
                deviceChange.device.addressType = addrType
                if mac:
                    deviceChange.device.macAddress = mac
                spec.deviceChange.append(deviceChange)
    
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk
 
    def change_nics(self, nic_dict, wait=True):
        """Change a network adapter of the vm and maps it to the given
        network mor. The network mor is obtained from the call to the
        get_network under host"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        for nic, network in nic_dict.items():
            deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
            deviceChange.operation = "edit"
            deviceChange.fileOperation = None
            # find the nic device with the given name
            nic_device = None
            adapterType = None
            for device in self.mor.config.hardware.device:
                if device.deviceInfo.label == nic:
                    adapterType = (device.__class__.__name__).split(".")[-1]
                    nic_device = device
                    break
            if nic_device and adapterType:   
                deviceChange.device = self._server.new_spec(adapterType)
                deviceChange.device.key = nic_device.key
                deviceChange.device.addressType = nic_device.addressType
                deviceChange.device.macAddress = nic_device.macAddress
                if network.__class__.__name__ == "vim.DistributedVirtualPortgroup" or \
                   network.__class__.__name__ == "vim.dvs.DistributedVirtualPortgroup":
                    deviceChange.device.backing = self._server.new_spec('VirtualEthernetCardDistributedVirtualPortBackingInfo')
                    deviceChange.device.backing.port = self._server.new_spec('DistributedVirtualSwitchPortConnection')
                    deviceChange.device.backing.port.portgroupKey = network.config.key
                    deviceChange.device.backing.port.switchUuid = network.config.distributedVirtualSwitch.uuid
                else:
                    deviceChange.device.backing = self._server.new_spec('VirtualEthernetCardNetworkBackingInfo')
                    deviceChange.device.backing.network = network
                    deviceChange.device.backing.deviceName = network.name
                deviceChange.device.connectable = self._server.new_spec('VirtualDeviceConnectInfo')
                deviceChange.device.connectable.connected = True
                deviceChange.device.connectable.startConnected = True
                deviceChange.device.connectable.allowGuestControl = True
                spec.deviceChange.append(deviceChange)
        
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk
   
    def change_nic(self,nic,network=None,wait=True):
        """Change a network adapter of the vm and maps it to the given
        network mor. The network mor is obtained from the call to the
        get_network under host"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        deviceChange.operation = "edit"
        deviceChange.fileOperation = None
        # find the nic device with the given name
        nic_device = None
        adapterType = None
        for device in self.mor.config.hardware.device:
            if device.deviceInfo.label == nic:
                adapterType = (device.__class__.__name__).split(".")[-1]
                nic_device = device
                break
        if nic_device and adapterType:
            deviceChange.device = self._server.new_spec(adapterType)
            deviceChange.device.key = nic_device.key
            deviceChange.device.addressType = nic_device.addressType
            deviceChange.device.macAddress = nic_device.macAddress
            if network.__class__.__name__ == "vim.dvs.DistributedVirtualPortgroup":
                deviceChange.device.backing = self._server.new_spec('VirtualEthernetCardDistributedVirtualPortBackingInfo')
                deviceChange.device.backing.port = self._server.new_spec('DistributedVirtualSwitchPortConnection')
                deviceChange.device.backing.port.portgroupKey = network.config.key
                deviceChange.device.backing.port.switchUuid = network.config.distributedVirtualSwitch.uuid
            else:
                deviceChange.device.backing = self._server.new_spec('VirtualEthernetCardNetworkBackingInfo')
                deviceChange.device.backing.network = network
                deviceChange.device.backing.deviceName = network.name
            deviceChange.device.connectable = self._server.new_spec('VirtualDeviceConnectInfo')
            deviceChange.device.connectable.connected = True
            deviceChange.device.connectable.startConnected = True
            deviceChange.device.connectable.allowGuestControl = True
            spec.deviceChange.append(deviceChange)
            tk = self.mor.ReconfigVM_Task(spec=spec)
            if wait:
                tk = self._server.wait_for_task(tk)
                self.update()
            else:
                tk = self._server.add_task(tk)
            return tk
        else:
            print "NIC Device",nic," not found"
        return

    def change_serial(self,serial,uri,wait=True):
        """Change a serial adapter of the vm"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        deviceChange.operation = "edit"
        # find the device with the given name
        serial_device = None
        for device in self.mor.config.hardware.device:
            if device.deviceInfo.label == serial:
                serial_device = device
                break
        if serial_device:
            deviceChange.device = self._server.new_spec('VirtualSerialPort')
            deviceChange.device.key = serial_device.key
            deviceChange.device.backing = self._server.new_spec('VirtualSerialPortURIBackingInfo')
            deviceChange.device.backing.serviceURI = uri
            deviceChange.device.backing.direction = 'server'
            """
            deviceChange.device.connectable = self._server.new_spec('VirtualDeviceConnectInfo')
            deviceChange.device.connectable.connected = True
            deviceChange.device.connectable.startConnected = True
            deviceChange.device.connectable.allowGuestControl = True
            """
            spec.deviceChange.append(deviceChange)
            tk = self.mor.ReconfigVM_Task(spec=spec)
            if wait:
                tk = self._server.wait_for_task(tk)
                self.update()
            else:
                tk = self._server.add_task(tk)
            return tk
        else:
            print "Serial device", serial, "not found"
        return

    def change_name(self,name,wait=True):
        """Change the name of the VM
        """
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.name = name
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)

        return tk

    def disconnect_nic(self,nic,wait=True):
        """Disconnect a network adapter of the vm"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        spec.deviceChange.append(deviceChange)
        deviceChange.operation = "edit"
        deviceChange.fileOperation = None
        # find the nic device with the given name
        nic_device = None
        adapterType = None
        for device in self.mor.config.hardware.device:
            if device.deviceInfo.label == nic:
                nic_device = device
                adapterType = (device.__class__.__name__).split(".")[-1]
                break
        if nic_device and adapterType:   
            deviceChange.device = self._server.new_spec(adapterType)
            deviceChange.device.key = nic_device.key
            deviceChange.device.macAddress = nic_device.macAddress
            deviceChange.device.addressType = nic_device.addressType
            deviceChange.device.connectable = self._server.new_spec('VirtualDeviceConnectInfo')
            deviceChange.device.connectable.connected = False
            deviceChange.device.connectable.startConnected = False
            deviceChange.device.connectable.allowGuestControl = False
            tk = self.mor.ReconfigVM_Task(spec=spec)
            if wait:
                tk = self._server.wait_for_task(tk)
                self.update()
            else:
                tk = self._server.add_task(tk)
            return tk
        else:
            print "NIC Device",nic," not found"
        return

    def reconnect_nic(self,nic,wait=True):
        """Reconnect a network adapter of the vm"""
        spec = self._server.new_spec('VirtualMachineConfigSpec')
        spec.deviceChange = []
        deviceChange = self._server.new_spec('VirtualDeviceConfigSpec')
        spec.deviceChange.append(deviceChange)
        deviceChange.operation = "edit"
        deviceChange.fileOperation = None
        # find the nic device with the given name
        nic_device = None
        adapterType = None
        for device in self.mor.config.hardware.device:
            if device.deviceInfo.label == nic:
                adapterType = (device.__class__.__name__).split(".")[-1]
                nic_device = device
                break
        if nic_device and adapterType:   
            deviceChange.device = self._server.new_spec(adapterType)
            deviceChange.device.key = nic_device.key
            deviceChange.device.macAddress = nic_device.macAddress
            deviceChange.device.addressType = nic_device.addressType
            deviceChange.device.connectable = self._server.new_spec('VirtualDeviceConnectInfo')
            deviceChange.device.connectable.connected = True
            deviceChange.device.connectable.startConnected = True
            deviceChange.device.connectable.allowGuestControl = True
            tk = self.mor.ReconfigVM_Task(spec=spec)
            if wait:
                tk = self._server.wait_for_task(tk)
                self.update()
            else:
                tk = self._server.add_task(tk)
            return tk
        else:
            print "NIC Device",nic," not found"
        return

    def is_nic_present(self,network):
        """Checks if a nic is available and connected to the given
        network. Network is mor obtained from the call to get_network
        under host"""
        for device in self.mor.config.hardware.device:
            if device.__class__.__name__ != 'vim.vm.device.VirtualE1000':
                continue
            if device.deviceInfo.summary == network.name:
                return device.deviceInfo.label
        return False

    def migrate(self,dest_host,wait=True):
        """Migrate to the given host.
        It returns the task object."""
        if dest_host.mor.parent.__class__.__name__ == "vim.ClusterComputeResource":
            tk = self.mor.MigrateVM_Task(pool=dest_host.mor.parent.resourcePool, host=dest_host.mor,priority="defaultPriority")
        else:
            tk = self.mor.MigrateVM_Task(pool=dest_host.mor.parent.resourcePool, priority="defaultPriority")
        if wait:
            tk = self._server.wait_for_task(tk)
            dest_host.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def relocate(self,dest_host,datastore,wait=True):
        """Reloate the vm to given dest_host and storage"""
        spec = self._server.new_spec("VirtualMachineRelocateSpec")
        spec.datastore = datastore.mor
        spec.host = dest_host.mor
        spec.pool = dest_host.mor.parent.resourcePool
        spec.transform = None
        tk = self.mor.RelocateVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
        else:
            tk = self._server.add_task(tk)
        return tk

    def update(self):
        updatemor.update(self)

    def reserve_cpu(self, mHz, wait=True):
        spec = self._server.new_spec("VirtualMachineConfigSpec")
        spec.cpuAllocation.reservation = mHz
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

    def reserve_memory(self, mb, wait=True):
        if mb == 0:
            mb = self.mor.runtime.maxMemoryUsage
        spec = self._server.new_spec("VirtualMachineConfigSpec")
        spec.memoryAllocation.reservation = mb
        tk = self.mor.ReconfigVM_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            self.update()
        else:
            tk = self._server.add_task(tk)
        return tk

