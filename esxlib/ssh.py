#import paramiko
import re

class Client:
    
    def __init__(self,host,user,password):
        self._host = host
        self._user = user
        self._password = password
        self._client = None
        self._connect()

    def execute(self,cmd):
        """ execute a command 'cmd' on the shell of the host """
        stdin,stdout,stderr = self._client.exec_command(cmd)
        return (stdout,stderr)

    def get_ssl_thumbprint(self):
        cmd = "openssl x509 -in /etc/vmware/ssl/rui.crt \
                -fingerprint -sha1 -noout"
        out,err = self.execute(cmd)
        line = out.readline().strip()
        obj = re.search("SHA1 Fingerprint=(.+)",line)
        fp = obj.group(1)
        return fp

    def _connect(self):
        cl = paramiko.SSHClient()
        cl.load_system_host_keys()
        cl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cl.connect(self._host,username=self._user,
            password=self._password)
        self._client = cl
        return

    def close(self):
        self._client.close()

