import copy
import vportgroup

class Vswitch:
    """Class to manage virtual switch"""

    def __init__(self,server_obj,host_obj,vswitch_mor):
        self._server = server_obj
        self._host = host_obj
        self.mor = vswitch_mor

    def set_num_ports(self,num_ports):
        if self.mor.spec.numPorts == num_ports:
            # if the value is already set dont do anything 
            return
        vspec = copy.deepcopy(self.mor.spec)
        if hasattr(vspec,'bridge'):
            del vspec.bridge
        vspec.numPorts = num_ports
        self._host.mor.configManager.networkSystem.UpdateVirtualSwitch(vswitchName=self.mor.name,spec=vspec)
        return
        

    def add_uplink_nic(self,nic):
        """Add uplink nic to the switch. nic is the string name of the
        nic adapter of the host"""
        vspec = self.mor.spec
        vspec.bridge = self._server.new_spec('HostVirtualSwitchBondBridge')
        vspec.bridge.nicDevice.append(nic)
        vspec.policy.nicTeaming.nicOrder = self._server.new_spec('HostNicOrderPolicy') 
        vspec.policy.nicTeaming.nicOrder.activeNic.append(nic)
        self._host.mor.configManager.networkSystem.UpdateVirtualSwitch(vswitchName=self.mor.name,spec=vspec)
        return

    def remove_uplink_nic(self):
        """Removes the uplink nic from the switch"""
        vspec = copy.deepcopy(self.mor.spec)
        vspec.bridge = self._server.new_spec('HostVirtualSwitchBridge')
        del vspec.policy
        self._host.mor.configManager.networkSystem.UpdateVirtualSwitch(vswitchName=self.mor.name,spec=vspec)
        return

    def delete(self,wait=True):
        """Delete the current vswitch"""
        self._host.mor.configManager.networkSystem.RemoveVirtualSwitch(vswitchName=self.mor.name)
        return

    def add_port_group(self, name, vlan_id=0):
        """Add portgroup of the given name to the vswitch and returns
        the portgroup object"""
        pgspec = self._server.new_spec('HostPortGroupSpec')
        pgspec.vlanId = vlan_id
        pgspec.policy = self._server.new_spec('HostNetworkPolicy')
        pgspec.name = name
        pgspec.vswitchName = self.mor.name
        self._host.mor.configManager.networkSystem.AddPortGroup(portgrp=pgspec)
        return self.get_port_group(name)

    def get_port_group(self,name=None):
        """Return the list of all the portgroup objects or the given
        portgroup under this vswitch"""
        objs = []
        for i in self._host.mor.configManager.networkSystem.networkConfig.portgroup:
            # get all the portgroups and see if the vswitchname is the
            # current switch
            if i.spec.vswitchName != self.mor.name:
                continue
            if not name or (i.spec.name == name):
                objs.append(vportgroup.Portgroup(self._server,self._host,i))
                if name and i.spec.name == name:
                    break
        if name and len(objs):
            objs = objs[0]
        return objs

    def _set_promisc(self,value):
        if self.mor.spec.policy.security.allowPromiscuous == value:
            # if the value is already set dont do anything 
            return
        # if an uplink already exists this fails. so do a workaround
        uplink = None
        if hasattr(self.mor.spec,'bridge') and\
                hasattr(self.mor.spec.bridge,'nicDevice'):
            uplink = self.mor.spec.bridge.nicDevice[0]
        vspec = copy.deepcopy(self.mor.spec)
        try:
            del vspec.bridge
        except:
            pass
        try:
            del vspec.policy.nicTeaming.nicOrder
        except:
            pass

        vspec.policy.security.allowPromiscuous = value
        self._host.mor.configManager.networkSystem.UpdateVirtualSwitch(vswitchName=self.mor.name,spec=vspec)
        if uplink:
            self.add_uplink_nic(uplink)
        return

    def enable_promisc(self):
        """Enable promiscuous mode on the current switch"""
        self._set_promisc(True)

    def disable_promisc(self):
        """Disable promiscuous mode on the current switch"""
        self._set_promisc(False)
