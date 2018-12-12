# coding: utf-8

# In[22]:


import sys, os, re
import multiprocessing
from subprocess import Popen, PIPE
from random import randint
import pandas as pd
import time
# In[23]:


class GenericSolverBase():
    '''
    Doc

    '''
    def __init__(self, solverFlag, cutOFFTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll):

        self.solverFlag = solverFlag
        self.cutOFFTime = cutOFFTime
        self.tuneTimeLimit = tuneTimeLimit
        self.verboseOnOff = verboseOnOff
        self.pcsFile = pcsFile
        self.nThreadMinizinc = nThreadMinizinc
        self.insPath = insPath
        self.insList = insList
        self.cplex_dll = cplex_dll
        self.timestamp = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(time.time())) + '_' + str(randint(1, 999999))
        self.outputdir = 'runs_' + self.timestamp

    def runCmd(self, cmd):
        io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        (stdout_, stderr_) = io.communicate()
        io.wait()
        #if len(stdout_) == 0:
        #    raise Exception(stderr_.decode('utf-8'))
        #else:
        #    return stdout_, stderr_
        return stdout_, stderr_
    def get_current_timestamp(self):
        return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))

    def process_thread(self):

        '''
        Compute number of smac that can run in parallel given the user input
        '''

        n_cores = multiprocessing.cpu_count() # Get number of threads available in the system

        if self.nThreadMinizinc == 1: # Each SMAC occupies one thread
            return n_cores # Return #SMAC and #thread for Minizinc
        elif self.nThreadMinizinc < n_cores and n_cores % self.nThreadMinizinc == 0: # Each SMAC occupies n_thread specified by user
            return n_cores / self.nThreadMinizinc # Return #SMAC and #thread for Minizinc
        else:
            raise Exception("{} threads found in the system. However {} threads specified by user.".format(n_cores, self.nThreadMinizinc))


    def process_instance(self):
        '''
        Process instance list or path to combine the model file with instance file(s) and write to a txt file with standard format for SMAC.

        '''

        if self.insList != None: # If list of instance is provided
            instance = re.findall('([^\s\.]+\.mzn(?:\s[^\.]+\.dzn)+)+', ' '.join(self.insList))
        elif self.insPath != None: # If instance input file is provided
            try:
                instance = [line.rstrip('\n') for line in open(self.insPath)]
            except FileNotFoundError:
                raise Exception("FileNotFoundError: No such file or directory")
        else:
            raise Exception('No path or list of instance is passed.')

        instanceList = []
        for i in instance:

            if len(re.findall('[^\.\s]+\.mzn', i)) > 1: # Require one model file in each line
                raise Exception('More than one model file found in the same line.')
            elif len(re.findall('^[^\.\s]+\.mzn', i)) == 0: # Require model file at first of each line
                raise Exception('Model file must come first in each line.')

            for j in i.split()[1:]:
                newName = i.split()[0].split('.')[0] + '_' + j.split('.')[0] + '.mzn' # Get name of combined model file
                #print("cat " + i.split()[0] + " " + j + " > " + newName)
                cmd = "cat " + i.split()[0] + " " + j + " > " + newName # Prepare the shell script for concat
                io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE) # Excecute concat
                (stdout_, stderr_) = io.communicate()
                #print(stdout_)
                instanceList.append(newName)

        with open('instances.txt', 'w') as f:
            f.write('\n'.join(instanceList)) # Write the formated instance file to text for smac read in.

        return instanceList # Return the combined file list for removal after smac optimization

    def cut_off_time_calculation(self):

        if self.cutOFFTime == 0:
            self.cutOFFTime = self.instance_runtime() * 5
        print('{} Calculating Cutoff Time'.format(self.get_current_timestamp()))
        print("{} Cutoff Time: {} s".format(self.get_current_timestamp(), round(self.cutOFFTime, 3)))



    def default_param_config_generation(self):

        lines = [line.rstrip('\n') for line in open(self.pcsFile)]
        paramList = []

        for line in lines:
            if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
                default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
                if self.solverFlag == 0:
                    paramList.append('-' + line.split()[0] + ' ' + str(default_val))
                else:
                    paramList.append(line.split()[0] + '\t' + str(default_val))
        if self.solverFlag == 0:
            return ' '.join(paramList)
        elif self.solverFlag == 1:
            paramList.insert(0, 'CPLEX Parameter File Version 12.6')
            with open('pre_run_time_check', 'w') as f:
                f.write('\n'.join(paramList))


    def run_solver(self, instance):

        cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --output-time --solver '
        args = self.default_param_config_generation()

        if self.solverFlag == 0:
            cmd += 'osicbc ' + instance + ' --cbcArgs "' + args + '"'
        elif self.solverFlag == 1:
            cmd += 'cplex ' + instance + ' --readParam pre_run_time_check' +             ' --cplex-dll ' + str(self.cplex_dll)
        #print('cmd:', cmd)

        (stdout_, stderr_) = self.runCmd(cmd)

        if self.verboseOnOff:
            print(stdout_.decode('utf-8'), end='')
            print(stderr_.decode('utf-8'), end='')

        if re.search(b'time elapsed:', stdout_):
            runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
            return runtime


    def instance_runtime(self):

        runtime = -1
        for instance in self.process_instance():
            #print(instance)
            tmp = self.run_solver(instance)
            #print(tmp)
            if tmp > runtime:
                runtime = tmp
        return runtime


# In[34]:


class GenericSolverExpansion(GenericSolverBase):

    def __init__(self, solverFlag, cutOFFTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll):

        super().__init__(solverFlag, cutOFFTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll)
        self.nSMAC = super().process_thread()
        self.instanceList = super().process_instance()


    def psmac_args(self):

        cmd = []
        (stdout_, stderr_) = self.runCmd('which smac')
        if len(stdout_) == 0:
            raise Exception("SMAC path not found in environment.")
        else:
            smac_path = stdout_.decode('utf-8').strip('\n')

        for i in range(self.nSMAC):
            tmp = ''
            if self.solverFlag == 0:
                tmp += '(python ' + smac_path + ' --scenario scenario.txt --seed ' + str(randint(1, 999999)) +                ' --shared_model True ' + '--output_dir ' + self.outputdir + ' --input_psmac_dirs ' + self.outputdir + '/run*'
                if self.verboseOnOff:
                    tmp += ' --verbose DEBUG)'
                else:
                    tmp += ')'
                cmd.append(tmp)
            elif self.solverFlag == 1:
                tmp += '(python ' + smac_path + ' --scenario scenario_' + str(i) + '.txt --seed ' + str(randint(1, 999999)) +                ' --shared_model True ' + '--output_dir ' + self.outputdir + ' --input_psmac_dirs ' + self.outputdir + '/run*'
                if self.verboseOnOff:
                    tmp += ' --verbose DEBUG)'
                else:
                    tmp += ')'
                cmd.append(tmp)
        return ' & '.join(cmd)


    def psamc_exe(self):

        cmd = self.psmac_args()
        #print('cmd:', cmd)
        print('{} SMAC optimization starts'.format(self.get_current_timestamp()))
        io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        if self.verboseOnOff:
            while io.poll() is None:
                line = io.stdout.readline()
                print(line.decode('utf-8'), end ="")
        else:
            io.wait()




    def runMinizinc(self, batch, instance, runmode, arglist, cplex_param):
        avgtime = 0
        for j in range(batch):
            #print('running batch', j + 1)
            if self.solverFlag == 0:

                if runmode == 0:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver osicbc ' + instance
                else:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver osicbc ' + instance + ' --cbcArgs ' + '"' + arglist + '"'
            else:

                if runmode == 0:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver cplex ' + instance + ' --cplex-dll ' + self.cplex_dll
                else:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver cplex ' + instance + ' --readParam '                     + cplex_param + ' ' + ' --cplex-dll ' + self.cplex_dll
            #print(cmd)

            stdout_, _ = self.runCmd(cmd)

            avgtime += float(re.search(b'(?:time=)(\d+\.\d+)', stdout_).group(1))
        avgtime /= batch
        print('Average Time:', avgtime)
        return avgtime


    def runBenchmark(self, batch, instance, stdout_):
        benchmark = {}
        for i in stdout_.split(b'\n'):
            #print(i)
            if len(i) != 0:
                df = pd.read_csv(i.decode('utf-8'))
                df.reset_index(inplace=True)
                #print(df.iloc[-1][5:].values)
                if self.solverFlag == 0:
                    arglist = ''
                else:
                    param = 'CPLEX Parameter File Version 12.6\n'

                for i in df.iloc[-1][5:].values:
                    tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
                    if self.solverFlag == 0:
                        arglist += '-' + tmp[0] + ' ' + tmp[1] + ' '
                    else:
                        param += tmp[0] + '\t' + tmp[1] + '\n'
                if self.solverFlag != 0:
                    with open('benchmark_cplex_param_cfg', 'w') as f:
                        f.write(param)


                if self.solverFlag == 0:
                    #print(arglist)
                    avgtime = self.runMinizinc(batch, instance, 1, arglist, '')
                    benchmark[arglist] = avgtime

                else:
                    #print(param)
                    avgtime = self.runMinizinc(batch, instance, 1, '', 'benchmark_cplex_param_cfg')
                    benchmark[param] = avgtime

        if self.solverFlag == 0:
            avgtime = self.runMinizinc(batch, instance, 0, '', '')
            benchmark['base'] = avgtime
        else:
            avgtime = self.runMinizinc(batch, instance, 0, '', '')
            benchmark['base'] = avgtime
        #print(benchmark)
        best_args = min(benchmark, key=benchmark.get)
        print("=" * 50)
        print('Recommendation:\n{}'.format(best_args))
        print('Runtime: {}s'.format(round(benchmark[best_args], 3)))
        print("=" * 50)

    def benchmark_main(self, batch=5):
        print('{} SMAC optimization completes'.format(self.get_current_timestamp()))
        print('{} Benchmarking starts'.format(self.get_current_timestamp()))
        for instance in self.instanceList:
            cmd = 'find . -name traj_old.csv'
            stdout_, _ = self.runCmd(cmd)
            self.runBenchmark(batch, instance, stdout_)


    def remove_tmp_files(self):
        #print('{} KeyboardInterrupt has been caught. Cleaning up...'.format(self.get_current_timestamp()))
        cmd = 'rm cplex_wrapper_?.py scenario* pre_run_time_check instances.txt benchmark_cplex_param_cfg tmpParamRead* ' + ' '.join(self.instanceList)
        self.runCmd(cmd)

# In[25]:


class CPLEX(GenericSolverExpansion):

    def __init__(self, solverFlag, cutOFFTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll):
        super().__init__(solverFlag, cutOFFTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll)

    def pSMAC_wrapper_generator(self):
        print('{} Generating CPLEX wrapper for SMAC'.format(self.get_current_timestamp()))
        for i in range(self.nSMAC):
            writeToFile = []
            writeToFile.append('from OOP_IMPL import cplex_wrapper')
            writeToFile.append('cplex_wrapper({}, {}, "{}")'.format(i, self.nThreadMinizinc, self.cplex_dll))
            with open('cplex_wrapper_' + str(i) + '.py', 'w') as f:
                f.write('\n'.join(writeToFile))

    def pSMAC_scenario_generator(self):
        print('{} Generating CPLEX scenario for SMAC'.format(self.get_current_timestamp()))
        for i in range(self.nSMAC):
            writeToFile = []
            writeToFile.append('algo = python -u ./cplex_wrapper_{}.py'.format(i))
            writeToFile.append('paramfile = ./{}'.format(self.pcsFile))
            writeToFile.append('execdir = .')
            writeToFile.append('deterministic = 0')
            writeToFile.append('run_obj = runtime')
            writeToFile.append('overall_obj = PAR10')
            writeToFile.append('cutoff_time = {}'.format(self.cutOFFTime))
            writeToFile.append('wallclock-limit = {}'.format(self.tuneTimeLimit))
            writeToFile.append('instance_file = instances.txt')
            with open('scenario_' + str(i) + '.txt', 'w') as f:
                f.write('\n'.join(writeToFile))
                #print('scenario_' + str(i) + '.txt')


# In[26]:


def cplex_wrapper(n, n_thread, cplex_dll):

    instance = sys.argv[1]
    specifics = sys.argv[2]
    cutoff = int(float(sys.argv[3]) + 1) # runsolver only rounds down to integer
    runlength = int(sys.argv[4])
    seed = int(sys.argv[5])
    params = sys.argv[6:]


    paramfile = 'CPLEX Parameter File Version 12.6\n'

    for name, value in zip(params[::2], params[1::2]):
        paramfile += name.strip('-') + '\t' + value + '\n'

    with open('tmpParamRead_' + str(n) , 'w') as f:
        f.write(paramfile)

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit '     + str(cutoff * 1000) + ' --solver cplex ' + instance     + ' --readParam tmpParamRead_' + str(n)     + ' --cplex-dll ' + cplex_dll

    #print(cmd)

    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    io.wait()

    print(stdout_.decode('utf-8'), end='')
    print(stderr_.decode('utf-8'), end='')
    status = "CRASHED"
    runtime = 99999

    if re.search(b'time elapsed:', stdout_):
        runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
        status = "SUCCESS"
    elif re.search(b'=====UNKNOWN=====', stdout_):
        runtime = cutoff
        status = "TIMEOUT"

    print('Result for SMAC: {}, {}, {}, 0, {}, {}'.format(status, runtime, runlength, seed, specifics))
