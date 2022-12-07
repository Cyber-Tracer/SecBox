import os
from subprocess import Popen, PIPE, STDOUT
from multiprocessing import Process
import json
import time
import socketio
import platform
import json
import requests
import sys

base_command = "bazel run examples/seccheck:server_cc"


class systemCallMonitor:
    def __init__(self, sandbox_id) -> None:
        self.base_command = base_command
        self.sandbox_id = sandbox_id
        self.client = None
        self.ps = []
        self.arch = platform.processor()
        self.bitness = 64 if sys.maxsize > 2**32 else 32

    def run(self):
        p = Process(target=self.runInParallel, args=(
            self.monitoring_process, self.monitoring_process, "healthy", "infected"))
        p.start()
        self.ps.append(p)

    def start(self):
        self.run()
        return self

    def stop(self):
        #self.client = socketio.Client()
        #self.client.connect('http://localhost:5000', namespaces=['/sysCall'])
        healthy_logfile = "healthy" + "/" + self.sandbox_id + "_syscalls"
        infected_logfile = "infected" + "/" + self.sandbox_id + "_syscalls"

        healthy_logstring = ""
        infected_logstring = ""


        for p in self.ps:
            p.kill()

        with open(healthy_logfile, "r") as h:
            healthy_logstring = h.read()
        
        with open(infected_logfile, "r") as i:
            infected_logstring = i.read()
        
        message = {
            "ID": self.sandbox_id,
            "architecture": self.arch,
            "sysCalls": {
                "healthy": healthy_logstring,
                "infected": infected_logstring
            }
        }
        requests.post("http://localhost:5000/syscall", json=json.dumps(message))
        #self.client.emit('sysCall', json.dumps(message), namespace='/sysCall')
        print("Syscall Logs emitted")
        time.sleep(10)
        os.remove("infected" + "/" + self.sandbox_id + "_syscalls")
        os.remove("healthy" + "/" + self.sandbox_id + "_syscalls")
    

    def monitoring_process(self, infected_status):
        self.client = socketio.Client()
        #self.client.connect('http://localhost:5000', namespaces=['/sysCall'])
        print("syscall monitor started")
        cwd = os.getcwd() + "/gvisor-master/"
        command = self.base_command + " /tmp/" + \
            infected_status + "_" + \
            str(self.sandbox_id) + "_gvisor_events.sock"
        running_command = Popen(command.split(),
                                stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=cwd)
        with open(infected_status + "/" + self.sandbox_id + "_syscalls", "w+") as logfile:
            for line in running_command.stdout:
                line = line.decode("UTF-8")
                if line.startswith("E") or line.startswith("X"):
                    logfile.write(line)

    def runInParallel(self, fn1, fn2, arg1, arg2):
        fns = [fn1, fn2]
        args = [arg1, arg2]
        for index in range(len(fns)):
            p = Process(target=fns[index], args=(args[index],))
            p.start()
            self.ps.append(p)
