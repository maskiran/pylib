import dvportgroup
import updatemor

class DVS:
    """Class to manage dvswitch (distributed virtual switch)"""

    def __init__(self,server_obj,dvs_mor):
        self._server = server_obj
        self.mor = dvs_mor

    def get_moid(self, stringify=True):
        moid = self.mor._moId
        if stringify:
            moid = str(moid)
        return moid

    def delete(self,wait=True):
        """Delete the current dvswitch"""
        tk = self.mor.Destroy_Task()
        if wait:
            tk = self._server.wait_for_task(tk)
        else:
            tk = self._server.add_task(tk)
        return tk

    def host_operation(self,operation,host_obj,nic):
        hspec = self._server.new_spec('DistributedVirtualSwitchHostMemberConfigSpec')
        hspec.host = host_obj.mor
        hspec.operation = operation
        hspec.backing = self._server.new_spec('DistributedVirtualSwitchHostMemberPnicBacking')
        if not type(nic) is list:
            nic = [ nic ]
        for n in nic:
            pnic_spec = self._server.new_spec('DistributedVirtualSwitchHostMemberPnicSpec')
            pnic_spec.pnicDevice = n
            hspec.backing.pnicSpec.append(pnic_spec)
        self.update() # without this, the next ReconfigureDvs_Task may fail
        dvs_spec = self._server.new_spec('DVSConfigSpec')
        dvs_spec.configVersion = self.mor.config.configVersion
        dvs_spec.host = [hspec]
        tk = self.mor.ReconfigureDvs_Task(spec=dvs_spec)
        tk = self._server.wait_for_task(tk)
        self.update() # without this, the next ReconfigureDvs_Task would fail
        return tk

    def add_host_nic(self,host_obj,nic=[]):
        """Add the host_obj and attach nic to the switch"""
        tk = self.host_operation("add", host_obj, nic)
        return tk

    def update_host_nic(self,host_obj,nic=[]):
        """Update the host_obj and nic attachment to the switch"""
        tk = self.host_operation("edit", host_obj, nic)
        return tk

    def delete_host(self,host_obj):
        """Delete the host_obj from the switch"""
        tk = self.host_operation("remove", host_obj, [])
        return tk

    def enable_lldp(self):
        """Enable lldp on the switch"""
        dvs_spec = self._server.new_spec('VMwareDVSConfigSpec')
        dvs_spec.configVersion = self.mor.config.configVersion
        dvs_spec.linkDiscoveryProtocolConfig = self._server.new_spec('LinkDiscoveryProtocolConfig')
        dvs_spec.linkDiscoveryProtocolConfig.protocol = "lldp"
        dvs_spec.linkDiscoveryProtocolConfig.operation = "both"
        tk = self.mor.ReconfigureDvs_Task(spec=dvs_spec)
        tk = self._server.wait_for_task(tk)
        self.update() # without this, the next ReconfigureDvs_Task would fail
        return tk

    def set_mtu(self, maxMtu=1500):
        """Set the mtu of the switch"""
        dvs_spec = self._server.new_spec('VMwareDVSConfigSpec')
        dvs_spec.configVersion = self.mor.config.configVersion
        dvs_spec.maxMtu = maxMtu
        tk = self.mor.ReconfigureDvs_Task(spec=dvs_spec)
        tk = self._server.wait_for_task(tk)
        self.update() # without this, the next ReconfigureDvs_Task would fail
        return tk

    def rename(self, name):
        """Rename the switch"""
        dvs_spec = self._server.new_spec('VMwareDVSConfigSpec')
        dvs_spec.configVersion = self.mor.config.configVersion
        dvs_spec.name = name
        tk = self.mor.ReconfigureDvs_Task(spec=dvs_spec)
        tk = self._server.wait_for_task(tk)
        self.update() # without this, the next ReconfigureDvs_Task would fail
        return tk

    def enable_cdp(self):
        """Enable CDP on the switch"""
        dvs_spec = self._server.new_spec('VMwareDVSConfigSpec')
        dvs_spec.configVersion = self.mor.config.configVersion
        dvs_spec.linkDiscoveryProtocolConfig = self._server.new_spec('LinkDiscoveryProtocolConfig')
        dvs_spec.linkDiscoveryProtocolConfig.protocol = "cdp"
        dvs_spec.linkDiscoveryProtocolConfig.operation = "both"
        tk = self.mor.ReconfigureDvs_Task(spec=dvs_spec)
        tk = self._server.wait_for_task(tk)
        self.update() # without this, the next ReconfigureDvs_Task would fail
        return tk

    def add_port_group(self,name,num_ports=128,vlan=None,wait=True):
        """Add portgroup of the given name to the switch. If wait=True
        then return the portgroup object, otherwise return the task"""
        spec = self._server.new_spec('DVPortgroupConfigSpec')
        spec.name = name
        spec.numPorts = num_ports
        spec.type = "earlyBinding"
        if vlan:
            spec.defaultPortConfig = self._server.new_spec('VMwareDVSPortSetting')
            spec.defaultPortConfig.vlan = self._server.new_spec('VmwareDistributedVirtualSwitchVlanIdSpec')
            spec.defaultPortConfig.vlan.vlanId = vlan
            spec.defaultPortConfig.vlan.inherited = False
        tk = self.mor.AddDVPortgroup_Task(spec=spec)
        if wait:
            tk = self._server.wait_for_task(tk)
            return self.get_port_group(name)
        else:
            tk = self._server.add_task(tk)
            return tk

    def get_port_group(self,name=None):
        """Return all the portgroup objects or the given port group
        object under the current switch"""
        objs = []
        for pg in self.mor.portgroup:
            if not name or name == pg.name:
                objs.append(dvportgroup.Portgroup(self,pg))
                if name and name == pg.name:
                    break
        if name and len(objs):
            objs = objs[0]
        return objs

    def rename_uplinks(self,name=None):
        """Rename the uplinks portgroup name with the given name. There
        should not be any need to call this manually. Its called by the
        add_dvswitch to rename it appropriately"""
        uplink_pg = self.mor.config.uplinkPortgroup[0]
        pg = dvportgroup.Portgroup(self,uplink_pg)
        if not name:
            name = self.mor.name + "-uplinks"
        pg.rename(name)
        return

    def update(self):
        updatemor.update(self)
