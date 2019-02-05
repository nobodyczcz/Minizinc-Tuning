from random import randint
from subprocess import Popen, PIPE, run
import time, shlex


class Tunning():
    def __init__(self,verboseOnOff,nSMAC,outputdir,smacPath):
        self.smac_path = smacPath
        self.verboseOnOff = verboseOnOff
        self.nSMAC = nSMAC
        self.outputdir = outputdir
        if nSMAC == 1:
            self.psmac = "False"
        else:
            self.psmac = "True"
    
    def get_current_timestamp(self):
        '''
        Get current timestamp
        '''
        return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))

    def runSmac(self):
        '''
        Run SMAC
        '''
        args = self.psmac_args()
        child_processes=[]
        for arg in args:
            print(arg)
            cmd = shlex.split(arg)
            time.sleep(5)
            print('{} SMAC optimization starts'.format(self.get_current_timestamp()))
            io = Popen(cmd)
            child_processes.append(io)

        # while child_processes[-1].poll() is None:
        #     for process in child_processes:
        #         line = process.stdout.readline()
        #         print('[',str(process.pid),']', line.decode('utf-8'), end ="")
        for process in child_processes:
            process.communicate()



    def psmac_args(self):
        '''
        Prepare the commands for running smac
        '''
        cmd = []
        # (stdout_, stderr_) = self.run_cmd('which smac')
        # if len(stdout_) == 0:
        #    raise Exception("SMAC path not found in environment.")
        # else:
        #    self.smac_path = stdout_.decode('utf-8').strip('\n')

        for i in range(self.nSMAC):
            tmp = ''
            tmp += '"' + self.smac_path + '" --scenario-file scenario_.txt --seed ' + str(randint(1, 999999)) \
                   + ' --shared-model-mode ' + self.psmac + ' --shared-model-mode-frequency 100 --rungroup ' + self.outputdir\
                   + ' --cli-listen-for-updates false --validation false'
            if self.verboseOnOff:
                tmp += ' --console-log-level DEBUG'
            cmd.append(tmp)

        return cmd


