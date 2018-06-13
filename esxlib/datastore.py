import updatemor


class Datastore:
    """Class to manage the host system's datastore"""

    def __init__(self,server_obj,host_obj,datastore_mor):
        self._server = server_obj
        self._host = host_obj
        self.mor = datastore_mor

    def get_moid(self, stringify=True):
        moid = self.mor._moId
        if stringify:
            moid = str(moid)
        return moid

    def delete(self):
        """Delete the current datastore"""
        self._host.mor.configManager.datastoreSystem.RemoveDatastore(datastore=self.mor)
        pass

    def search(self, pattern, folder=None, refresh=False):
        if refresh:
            self.refresh()
        spec = self._server.new_spec('HostDatastoreBrowserSearchSpec')
        spec.matchPattern = [pattern]
        dsp = "["+self.mor.name+"]"
        if folder:
            dsp += folder
        tk = self.mor.browser.SearchDatastore_Task(datastorePath=dsp,
                searchSpec=spec)
        tk = self._server.wait_for_task(tk)
        result = tk.result()
        paths = []
        if hasattr(result,'file'):
            for f in result.file:
                # if folder is not specified, append space between
                # resulr folder and path
                path = result.folderPath
                if not folder:
                    path += " "
                path += f.path
                paths.append(path)
        return paths

    def refresh(self):
        self.mor.RefreshDatastore()
        self.mor.RefreshDatastoreStorageInfo()
        return

    def update(self):
        updatemor.update(self)
