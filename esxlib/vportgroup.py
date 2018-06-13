import updatemor


class Portgroup:
    """Class to manage the portgroup on the vswitch"""
    def __init__(self,server_obj,host_obj,pg_mor):
        self._server = server_obj
        self._host = host_obj
        self.mor = pg_mor

    def delete(self):
        """Delete the current portgroup"""
        self._host.mor.configManager.networkSystem.RemovePortGroup(pgName=self.mor.spec.name)
        return

    def set_vlan(self,vlan):
        """Set vlan on the current portgroup to the give id. The id can
        be a valid vlan number, 0 to disable it, 4095 for all vlans"""
        pgspec = self._server.new_spec('HostPortGroupSpec')
        pgspec.vlanId = vlan
        pgspec.policy = self.mor.spec.policy
        pgspec.name = self.mor.spec.name
        pgspec.vswitchName = self.mor.spec.vswitchName
        self._host.mor.configManager.networkSystem.UpdatePortGroup(pgName=self.mor.spec.name,portgrp=pgspec)
        return

    def _set_promisc(self,value):
        pgspec = self._server.new_spec('HostPortGroupSpec')
        pgspec.vlanId = self.mor.spec.vlanId
        pgspec.policy.security.allowPromiscuous = value
        pgspec.name = self.mor.spec.name
        pgspec.vswitchName = self.mor.spec.vswitchName
        self._host.mor.configManager.networkSystem.UpdatePortGroup(pgName=self.mor.spec.name,portgrp=pgspec)
        return

    def enable_promisc(self):
        """Enable promiscuous mode on the current switch"""
        self._set_promisc(True)

    def disable_promisc(self):
        """Disable promiscuous mode on the current switch"""
        self._set_promisc(False)

    def update(self):
        updatemor.update(self)
