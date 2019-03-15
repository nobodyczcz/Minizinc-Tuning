import threading
from random import randint
from subprocess import Popen
from helpFunctions.helpFuctions import *



class Tunning():
    def __init__(self,verboseOnOff,nSMAC,outputdir,smacPath,rungroup):
        self.smac_path = smacPath
        self.verboseOnOff = verboseOnOff
        self.nSMAC = nSMAC
        self.outputdir = outputdir
        self.rungroup = rungroup
        if nSMAC > 1:
            self.psmac = "true"
        else:
            self.psmac = "false"
    
    def get_current_timestamp(self):
        '''
        Get current timestamp
        '''
        return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))

    def vprint(self,*args, **kwargs):
        if self.verboseOnOff:
            eprint('[Tuning Debug]',*args, **kwargs)

    def runSmac(self,timelimit,env=None,restore=None):
        '''
        Run SMAC
        '''
        args = self.psmac_args(restore)
        child_processes=[]

        # progress = threading.Thread(target=printPorgress, args=(timelimit,))
        # progress.start()
        t = time.time()
        for arg in args:
            self.vprint(arg)
            cmd = arg
            time.sleep(1)
            eprint('{} SMAC optimization starts'.format(self.get_current_timestamp()))
            io = Popen(cmd, env = env)
            child_processes.append(io)


        while child_processes[-1].poll() is None:
            progress = round(((time.time() - t) / timelimit) * 100, 2)
            pprint("%%%mzn-progress", progress if progress < 100 else 100)

            time.sleep(2)
        #     for process in child_processes:
        #         line = process.stdout.readline()
        #         print('[',str(process.pid),']', line.decode('utf-8'), end ="")
        for process in child_processes:
            process.communicate()

    def psmac_args(self,restore = None):
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

            tmp = [self.smac_path, "--scenario-file", "scenario_.txt", "--seed", str(randint(1, 999999)), \
                   "--shared-model-mode", str(self.psmac), "--shared-model-mode-frequency", "100", "--output-dir",\
                   self.outputdir, "--rungroup", self.rungroup, "--cli-listen-for-updates", "false", "--validation", "false"]
            if restore is not None:
                tmp += ["--restore-scenario", restore[i]]

            if self.verboseOnOff:
                tmp += ["--console-log-level", "DEBUG"]
            cmd.append(tmp)

        return cmd

    """
    Functions for Gurobi Tuning tool.
    """

    def grbtune_cmd(self,tuneTime,solverTimeLimit,more_runs,obj_mode,modelList,threads):
        tuneTimeLimit = "TuneTimeLimit="+str(tuneTime)
        timeLimit =  "TimeLimit="+str(solverTimeLimit)
        if self.verboseOnOff:
            tuneOutput = "TuneOutput=2"
        else:
            tuneOutput = "TuneOutput=1"

        tuneResults = "TuneResults=-1"
        tuneThreads =  "Threads="+str(threads)

        if obj_mode:
            tuneCriterion = "TuneCriterion=2"
        else:
            tuneCriterion = "TuneCriterion=-1"

        cmd = ["grbtune", tuneCriterion, tuneTimeLimit,timeLimit,tuneOutput,tuneResults,tuneThreads]

        if more_runs:
            tuneTrials="TuneTrials=3"
            cmd.append(tuneTrials)
        else:
            tuneTrials = "TuneTrials=1"
            cmd.append(tuneTrials)
        cmd += modelList
        return cmd

    def runGrbtune(self, cmd, timelimit, env=None):
        '''
        Run SMAC
        '''
        time.sleep(1)
        eprint("{} Gurobi Tune Tool optimization starts".format(self.get_current_timestamp()))
        self.vprint("Execute command: ",cmd)

        t = time.time()
        io = Popen(cmd, env = env)

        while io.poll() is None:
            progress = round(((time.time() - t) / timelimit) * 100, 2)
            pprint("%%%mzn-progress", progress if progress < 100 else 100)
            time.sleep(2)

        io.communicate()


