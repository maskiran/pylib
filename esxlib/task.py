import time
import updatemor

class Task:

    def __init__(self,server_obj,task_mor=None):
        self._server = server_obj
        self.mor = task_mor

    def wait(self,state=None):
        while True:
            try:
                if self.mor.info.state == "success" or\
                        self.mor.info.state == "error":
                    break
            except:
                # the taks might have already been deleted from the
                # system, assume it has completed
                print "The task probably completed, could not find "+\
                    "it on the server"
                break
            else:
                time.sleep(2)
                continue
        return

    def __str__(self):
        if hasattr(self.mor, 'info'):
            return str(self.mor.info)
        return "No task details available"

    def result(self):
        if hasattr(self.mor.info,'result'):
            return self.mor.info.result

    def update(self):
        updatemor.update(self)

