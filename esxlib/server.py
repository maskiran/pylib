import os

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import fix_ssl_error

import datacenter
import task


class Server:
    """Creates a server object by connecting to the vcenter"""

    def __init__(self,host,user='administrator',password='in$1eme'):
        """Host - ip/hostname of the vcenter server"""
        # mor to the server
        self._host = host
        self._user = user
        self._password = password

        self.mor = None
        self._connect()
        # list of all the background tasks (async tasks)
        self._task_list = []

        # licenses
        self._licenses = {}
        self._licenses['vc'] = '054A7-4EJ9K-M8H46-082HM-08EQ0'
        # 100 cpu
        #self._licenses['esx'] = 'DM01H-D8L97-2894R-0T480-8JQ1N'
        # 452 cpu
        self._licenses['esx'] = '4M09K-88N55-P884J-0CW84-9X53N'
        self._licenses['vs'] = 'J1215-4CH9H-58J57-0WEHP-A9ZJ4'

        #self._add_licenses()
        #self._update_license()


    def _connect(self):
        self.mor = SmartConnect(host=self._host,
                                user=self._user,
                                pwd=self._password)
        return

    def _add_licenses(self):
        lm = self.mor.content.licenseManager
        for lic in self._licenses.values():
            lm.AddLicense(licenseKey=lic)

    def _update_license(self, vcenter=True, esx=True, vshield=True):
        lam = self.mor.content.licenseManager.licenseAssignmentManager
        if vcenter:
            lam.UpdateAssignedLicense(entity=self.mor.content.about.instanceUuid,
                                      licenseKey=self._licenses['vc'])
        # assign licenses to all the hosts also
        if esx:
            for dc in self.get_datacenter():
                for host in dc.get_host():
                    lam.UpdateAssignedLicense(entity=host.get_moid(),
                                              licenseKey=self._licenses['esx'])

        if vshield:
            lam.UpdateAssignedLicense(entity="vcloud-netsec",
                                      licenseKey=self._licenses['vs'])

    def add_datacenter(self,name):
        """Add datacenter of the given name to the root folder. Returns
        the datacenter object"""
        # check if the datacenter exists
        dc = self.get_datacenter(name)
        if not dc:
            root = self.mor.content.rootFolder
            root.CreateDatacenter(name=name)
            dc = self.get_datacenter(name)
        return dc

    def get_datacenter(self,name=None):
        """Return all the datacenter objects as a list or a datacenter
        object of the given name"""
        objs = []
        dclist = self.mor.content.rootFolder.childEntity
        for dc in dclist:
            if not name or name == dc.name:
                objs.append(datacenter.Datacenter(self,dc))
                if name and name == dc.name:
                    break
        if name and len(objs):
            objs = objs[0]
        return objs

    def new_spec(self,spec_name):
        """Create a new spec or data type of the given name"""
        fn = getattr(vim, spec_name)
        spec = fn()
        return spec

    def add_task(self,task_mor):
        """Adds a given task to the task list maintained by this object.
        This is used for aysnc tasks, where a task is created and not
        waited for it to complete. If a call to this method is made, it
        adds the task and later can be checked if it has completed"""
        tk_obj = task.Task(self,task_mor)
        self._task_list.append(tk_obj)
        return tk_obj

    def wait_for_task(self,task_mor):
        """Wait for the give task to complete"""
        tk_obj = task.Task(self,task_mor)
        tk_obj.wait()
        return tk_obj

    def wait_for_all_tasks(self):
        """Wait for all the tasks added to this object to finish"""
        for tk_obj in self._task_list:
            tk_obj.wait()

        self._task_list = []
        return


    def change_fqdn(self, fqdn):
        # this method exists for backward compatibility
        self.change_setting('VirtualCenter.FQDN', fqdn)
        return

    def change_setting(self, name, value, value_type="string"):
        settings = self.mor.content.setting
        spec = self.new_spec('OptionValue')
        spec.key = name
        spec.value = value
        settings.UpdateOptions(changedValue=[spec])
        return

    def get_setting(self, name):
        slist = self.mor.content.setting.QueryOptions(name=name)
        val_list = []
        for opt in slist:
            val_list.append(opt.value)

        return val_list


    def reconnect(self):
        """Hack work. Get a setting from the server. If it succeeds,
        then the connection is alive. If it fails, then login
        """
        try:
            self.get_setting('instance.id')
        except:
            self._connect()
