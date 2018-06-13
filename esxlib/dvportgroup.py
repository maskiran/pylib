import updatemor

class Portgroup:
    """Class to manage the dvportgroup"""

    def __init__(self,dvs_obj,pg_mor):
        self._dvs = dvs_obj
        self.mor = pg_mor

    def get_moid(self, stringify=True):
        moid = self.mor._moId
        if stringify:
            moid = str(moid)
        return moid

    def delete(self):
        """Delete the current portgroup"""
        tk = self.mor.Destroy_Task()
        tk = self._dvs._server.wait_for_task(tk)
        return tk

    def set_vlan(self,vlan):
        """Set vlan to the given vlan id on the portgroup"""
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.configVersion = self.mor.config.configVersion
        spec.defaultPortConfig = self._dvs._server.new_spec('VMwareDVSPortSetting')
        spec.defaultPortConfig.vlan = self._dvs._server.new_spec('VmwareDistributedVirtualSwitchVlanIdSpec')
        spec.defaultPortConfig.vlan.vlanId = vlan
        spec.defaultPortConfig.vlan.inherited = False
        self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        self.update()
        return

    def set_uplink_port_vlan_range(self,vlan_range):
        """Set vlan rtange on the current uplink portgroup to the give id. The id is
        dictionary of start and end vlan range """
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.configVersion = self.mor.config.configVersion
        spec.defaultPortConfig = self._dvs._server.new_spec('VMwareDVSPortSetting')
        spec.defaultPortConfig.vlan = self._dvs._server.new_spec('VmwareDistributedVirtualSwitchTrunkVlanSpec')
        spec.defaultPortConfig.vlan.vlanId = vlan_range
        spec.defaultPortConfig.vlan.inherited = False
        self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        self.update()
        return

    def rename(self,name):
        """Rename the current portgroup"""
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.name = name
        spec.configVersion = self.mor.config.configVersion
        self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        self.update()
        return

    def _set_promisc(self,value):
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.configVersion = self.mor.config.configVersion
        spec.defaultPortConfig = self._dvs._server.new_spec('VMwareDVSPortSetting')
        spec.defaultPortConfig.securityPolicy = self._dvs._server.new_spec('DVSSecurityPolicy')
        spec.defaultPortConfig.securityPolicy.inherited = False
        spec.defaultPortConfig.securityPolicy.allowPromiscuous = self._dvs._server.new_spec('BoolPolicy')
        if value:
            spec.defaultPortConfig.securityPolicy.allowPromiscuous.value = True
        else:
            spec.defaultPortConfig.securityPolicy.allowPromiscuous.value = False
        spec.defaultPortConfig.securityPolicy.allowPromiscuous.inherited = False
        self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        self.update()
        return

    def _set_security(self,value):
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.configVersion = self.mor.config.configVersion
        spec.defaultPortConfig = self._dvs._server.new_spec('VMwareDVSPortSetting')
        spec.defaultPortConfig.securityPolicy = self._dvs._server.new_spec('DVSSecurityPolicy')
        spec.defaultPortConfig.securityPolicy.inherited = False
        spec.defaultPortConfig.securityPolicy.allowPromiscuous = self._dvs._server.new_spec('BoolPolicy')
        spec.defaultPortConfig.securityPolicy.macChanges = self._dvs._server.new_spec('BoolPolicy')
        spec.defaultPortConfig.securityPolicy.forgedTransmits = self._dvs._server.new_spec('BoolPolicy')
        if value:
            spec.defaultPortConfig.securityPolicy.allowPromiscuous.value = True
            spec.defaultPortConfig.securityPolicy.macChanges.value = True
            spec.defaultPortConfig.securityPolicy.forgedTransmits.value = True
        else:
            spec.defaultPortConfig.securityPolicy.allowPromiscuous.value = False
            spec.defaultPortConfig.securityPolicy.macChanges.value = False
            spec.defaultPortConfig.securityPolicy.forgedTransmits.value = False

        spec.defaultPortConfig.securityPolicy.allowPromiscuous.inherited = False
        spec.defaultPortConfig.securityPolicy.macChanges.inherited = False
        spec.defaultPortConfig.securityPolicy.forgedTransmits.inherited = False
        self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        self.update()
        return

    def enable_mac_hash_lb(self):
        """Enable lb based on mac hash on the current portgroup"""
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.configVersion = self.mor.config.configVersion
        spec.defaultPortConfig = self._dvs._server.new_spec('VMwareDVSPortSetting')
        spec.defaultPortConfig.uplinkTeamingPolicy = self._dvs._server.new_spec('VmwareUplinkPortTeamingPolicy')
        spec.defaultPortConfig.uplinkTeamingPolicy.policy = self._dvs._server.new_spec('StringPolicy')
        spec.defaultPortConfig.uplinkTeamingPolicy.policy.value = 'loadbalance_srcmac'
        self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        self.update()
        return
 
    def set_pg_type(self,value, wait=True):
        self.update()
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.configVersion = self.mor.config.configVersion
        spec.type = value
        tk = self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        if wait:
            tk = self._dvs._server.wait_for_task(tk)
        else:
            tk = self._dvs._server.add_task(tk)
        return tk

    def set_num_ports(self,value, wait=True):
        self.update()
        spec = self._dvs._server.new_spec('DVPortgroupConfigSpec')
        spec.configVersion = self.mor.config.configVersion
        spec.numPorts = value
        tk = self.mor.ReconfigureDVPortgroup_Task(spec=spec)
        if wait:
            tk = self._dvs._server.wait_for_task(tk)
        else:
            tk = self._dvs._server.add_task(tk)
        return tk

    def enable_promisc(self):
        """Enable promiscuous mode on the current portgroup"""
        self._set_promisc(True)

    def disable_promisc(self):
        """Disable promiscuous mode on the current portgroup"""
        self._set_promisc(False)

    def enable_security_policy(self):
        """Enable security policy on the current portgroup"""
        self._set_security(True)

    def disable_security_policy(self):
        """Disable security policy on the current portgroup"""
        self._set_security(False)
    
    def update(self):
        updatemor.update(self)

