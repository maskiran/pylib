#! /usr/bin/python

"""
SSH and SCP classes using pexpect
"""

import pexpect
import sys
import os


class SSH(object):
    """
    SSH expect class
    """
    def __init__(self, ip=None, user=None, password=None,
                 prompt='(.+)[#>$] ?', ssh_options=""):
        os.environ['TERM'] = 'dumb'
        self._ip = ip
        self._user = user
        self._password = password
        self._prompt = prompt
        self._handle = None
        self.last_output = ""
        self.last_prompt = ""
        self._ssh_options = ssh_options
        self._connect()

    def _connect(self):
        """
        SSH connect to the given ip. Once connected change the prompt of
        the session so its unique to the session and the one which
        probably does not appear in any command's output
        """
        ssh_options = self._ssh_options +\
            " -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
        cmd = "ssh %s" % ssh_options
        if self._user:
            cmd += " -l %s" % self._user
        cmd += " %s" % self._ip

        handle = pexpect.spawn(cmd, timeout=60)
        self._handle = handle
        loop_count = 0
        while True:
            # dont get into infinite loop
            if loop_count > 5:
                raise Exception('Cannot connect')
            idx = handle.expect([
                                'Are you sure',
                                '[Pp]assword',
                                self._prompt
                                ])
            if idx == 0:
                # Are you sure
                handle.sendline("yes")
                loop_count += 1
                continue
            if idx == 1:
                # password
                handle.sendline(self._password)
                loop_count += 1
                continue
            if idx == 2:
                # prompt
                self._change_prompt()
                break

    def _change_prompt(self):
        """
        Change session prompt. unset PROMPT_COMMAND, change winsize to
        10000 rows and columns so i can handle large commands without
        wrapping and send a new PS1 prompt that is username@ip
        """
        handle = self._handle
        handle.sendline("unset PROMPT_COMMAND")
        handle.expect(self._prompt)
        if self._user:
            new_prompt = "%s@%s# " % (self._user, self._ip)
        else:
            new_prompt = "%s " % self._ip
        # new_prompt = "user@ip# "
        # this changes the window size and spits out another prompt,
        # however I am changing the PS1 and will catch the new prompt,
        # so no need to get the prompt that was obtained as part of
        # window size change
        handle.setwinsize(10000, 10000)
        handle.sendline('export PS1="%s"' % new_prompt)
        handle.expect(new_prompt)
        handle.expect(new_prompt)
        self._prompt = new_prompt
        return

    def enable_log(self, read_log_fd=sys.stdout, send_log_fd=None):
        """
        Enable pexpect logging to the given read_log_fd and send_log_fd
        file descriptors
        """
        handle = self._handle
        if read_log_fd:
            handle.logfile_read = read_log_fd
        if send_log_fd:
            handle.logfile_send = send_log_fd
        self.cmd("")
        return

    def disable_log(self):
        """
        Disable expect logging
        """
        self._handle.logfile_read = None
        self._handle.logfile_send = None
        self._handle.logfile = None
        return

    def cmd(self, command, timeout=60, newline=True,
            waitfor=None):
        """
        Execute the given command on the ssh session and return the
        entire output including the prompt. If the prompt is not
        recevied within the timeout raise pexpect error. If newline is
        True the command is sent with newline otherwise no newline
        character is sent with the command. If the command returns
        something otherthan bash prompt, it can be provided as the
        'waitfor' argument. When waitfor is provided, the method either
        waits for the bash prompt or the waitfor text to appear before
        it returns. waitfor could be a text or a list of patterns to
        match
        """
        if waitfor and not isinstance(waitfor, list):
            waitfor = [waitfor]
        handle = self._handle
        if newline:
            handle.sendline(command)
        else:
            handle.send(command)
        wait_prompt = [self._prompt]
        if waitfor:
            wait_prompt.extend(waitfor)
        idx = handle.expect(wait_prompt, timeout=timeout)
        output = handle.before + handle.after
        self.last_prompt = handle.after
        if idx == 0:
            # matched bash prompt, remove it from the output
            self.last_output = output.replace(handle.after, "").strip()
        else:
            self.last_output = output
        return output

    def flush(self):
        """
        Get everything in the buffer with a timeout of 3 seconds and
        wait for timeout to occur
        """
        # flush for 3 seconds
        while True:
            idx = self._handle.expect(['.+$', pexpect.TIMEOUT, pexpect.EOF],
                                      timeout=3)
            if idx >= 1:
                break
        return

    def is_closed(self):
        """
        Check if the session is closed
        """
        self.flush()
        return self._handle.eof()


class SCP(object):
    def __init__(self, ip=None, user=None, password=None):
        self._ip = ip
        self._user = user
        self._password = password

    def _launch(self, cmd):
        handle = pexpect.spawn(cmd)
        output = ""
        while True:
            idx = handle.expect([
                                'Are you sure',
                                '[Pp]assword',
                                pexpect.EOF
                                ],
                                timeout=300)
            if idx == 0:
                # Are you sure
                output += handle.before + handle.after
                handle.sendline("yes")
                continue
            if idx == 1:
                # password
                output += handle.before + handle.after
                handle.sendline(self._password)
                continue
            output += handle.before
            break
        return output

    def put(self, local, remote):
        cmd = 'scp -r %s %s@%s:%s' % (local, self._user, self._ip, remote)
        output = self._launch(cmd)
        return output

    def get(self, remote, local):
        cmd = 'scp -r %s@%s:%s %s' % (self._user, self._ip, remote, local)
        output = self._launch(cmd)
        return output


if __name__ == "__main__":
    pc = SSH('smadabhushi.dev.eng.nutanix.com', 'smadabhushi')
    a = pc.cmd('ls')
    print "\n+++++Output start"
    print a
    print "+++++Output end\n"
    pc.cmd('touch /tmp/a')
    pc.cmd('rm -i /tmp/a', waitfor='remove')
    pc.cmd('y')
    pc.cmd('touch /tmp/a; rm -f /tmp/a', waitfor='junk')
    pc.cmd('for i in {1..10}; do echo $i >> /tmp/a; done')
    pc.cmd('ls -l /tmp/a')
    pc.cmd('cat /tmp/a')
    pc.cmd('rm -f /tmp/a')
    print ""
