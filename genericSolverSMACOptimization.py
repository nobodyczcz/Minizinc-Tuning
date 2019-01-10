import sys, os, re, multiprocessing, subprocess, psutil, time, inspect
from subprocess import Popen, PIPE
from random import randint
filename = inspect.getframeinfo(inspect.currentframe()).filename
path = os.path.dirname(os.path.abspath(filename))

class GenericSolverBase():
    '''
    Doc

    '''
    def __init__(self, solverFlag, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll):

        self.solverFlag = solverFlag # solver flag either be 0 (CBC) or 1 (CPLEX)
        self.cutOffTime = cutOffTime # cutoff time for Minizinc per run
        self.tuneTimeLimit = tuneTimeLimit # total time budget for optimization
        self.verboseOnOff = verboseOnOff # specifies the logging-verbisity
        self.pcsFile = pcsFile # parameter configuration space file
        self.nThreadMinizinc = nThreadMinizinc # number of threads allocated to per Minizinc
        self.insPath = insPath # path for file listing all instances for optimization
        self.insList = insList # list of instances
        self.cplex_dll = cplex_dll # path for cplex-dll
        self.timestamp = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(time.time())) + '_' + str(randint(1, 999999)) # timestamp for careation of output directory
        self.outputdir = 'runs_' + self.timestamp # output directory naming convention

    def run_cmd(self, cmd):
        '''
        Excecute command line arguments in the background
        '''
        io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        (stdout_, stderr_) = io.communicate()
        #io.wait()
        #if len(stdout_) == 0:
        #    raise Exception(stderr_.decode('utf-8'))
        #else:
        #    return stdout_, stderr_
        return stdout_, stderr_

    def get_current_timestamp(self):
        '''
        Get current timestamp
        '''

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
        
        #print('list',self.insList)
        #print('path',self.insPath)
        
        if len(self.insList) != 0: # If list of instance is provided
            
            instance = re.findall('([^\s\.]+\.mzn(?:\s[^\s]+\.dzn)+)+', ' '.join(self.insList))
            #print(instance)
            
        elif self.insPath != None: # If instance input file is provided
            try:
                
                instance = [line.rstrip('\n') for line in open(self.insPath)]
                
            except FileNotFoundError:
                raise Exception("FileNotFoundError: No such file or directory")
        else:
            raise Exception('No path or list of instance is passed.')
            
        if len(instance) == 0:
            raise Exception("instance list is empty!")
        instanceList = []
        for i in instance:

            if len(re.findall('([^\.\s]+\.mzn)(?:\s)', i)) > 1: # Require one model file in each line
                raise Exception('More than one model file found in the same line.')
            elif len(re.findall('^[^\.\s]+\.mzn', i)) == 0: # Require model file at first of each line
                raise Exception('Model file must come first in each line.')

            for j in i.split()[1:]:
                #newName = i.split()[0].split('.')[0] + '_' + j.split('.')[0] + '.mzn' # Get name of combined model file
                newName = i.split()[0].split('.')[0] + '_' + re.search('([^\s]+)(?:\.dzn)', j).group(1) + '.mzn' # Get name of combined model file
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
        '''
        Get cutoff time if user does not specify
        '''

        if self.cutOffTime == 0:
            self.cutOffTime = self.instance_runtime() * 2 # Give 5 times of margin of safety for cutoff
        print('{} Calculating Cutoff Time'.format(self.get_current_timestamp()))
        print("{} Cutoff Time: {} s".format(self.get_current_timestamp(), round(self.cutOffTime, 3)))


    def default_param_config_generation(self):
        '''
        Read default parameters from the parameter configuration space
        '''

        lines = [line.rstrip('\n') for line in open(self.pcsFile)]
        paramList = []

        for line in lines:
            if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
                default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
                if self.solverFlag == 0:
                    paramList.append('-' + line.split()[0] + ' ' + str(default_val))
                else:
                    paramList.append(line.split()[0] + '\t' + str(default_val))
        # For CBC solver
        if self.solverFlag == 0:
            return ' '.join(paramList)
        # For CPLEX solver
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
            cmd += 'cplex ' + instance + ' --readParam pre_run_time_check' + ' --cplex-dll ' + str(self.cplex_dll)
        #print('cmd:', cmd)

        (stdout_, stderr_) = self.run_cmd(cmd)

        if self.verboseOnOff:
            print(stdout_.decode('utf-8'), end='')
            print(stderr_.decode('utf-8'), end='')

        
        if re.search(b'time elapsed:', stdout_):
            
            runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
            return runtime
        else:
            raise Exception("No solution")
            


    def instance_runtime(self):

        runtime = -1
        for instance in self.process_instance():
            #print(instance)
            tmp = self.run_solver(instance)
            #print(tmp)
            if tmp > runtime:
                runtime = tmp
        return runtime



class GenericSolverExpansion(GenericSolverBase):

    def __init__(self, solverFlag, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll):

        super().__init__(solverFlag, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll)
        self.nSMAC = super().process_thread()
        self.instanceList = super().process_instance()


    def psmac_args(self):

        cmd = []
        #(stdout_, stderr_) = self.run_cmd('which smac')
        #if len(stdout_) == 0:
        #    raise Exception("SMAC path not found in environment.")
        #else:
        #    smac_path = stdout_.decode('utf-8').strip('\n')

        smac_path = '/home/user/Desktop/smac-v2.10.03-master-778/smac'
        
        for i in range(self.nSMAC):
            tmp = ''
            if self.solverFlag == 0:
                tmp += '( ' + smac_path + ' --scenario-file scenario_0.txt --seed ' + str(randint(1, 999999)) + ' --shared-model-mode True ' + '--rungroup ' + self.outputdir + ' --validation false'
                if self.verboseOnOff:
                    tmp += ' --console-log-level DEBUG)'
                else:
                    tmp += ')'
                cmd.append(tmp)
            elif self.solverFlag == 1:
                tmp += '( ' + smac_path + ' --scenario-file scenario_' + str(i) + '.txt --seed ' + str(randint(1, 999999)) + ' --shared-model-mode True ' + '--rungroup ' + self.outputdir + ' --validation false'
                if self.verboseOnOff:
                    tmp += ' --console-log-level DEBUG)'
                else:
                    tmp += ')'
                cmd.append(tmp)
        return ' & '.join(cmd)


    def psamc_exe(self):

        cmd = self.psmac_args()
        #print('cmd:', cmd)
        print('{} SMAC optimization starts'.format(self.get_current_timestamp()))
        io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)

        while io.poll() is None:
            line = io.stdout.readline()
            print(line.decode('utf-8'), end ="")


    def run_minizinc(self, batch, instance, runmode, arglist, cplex_param):
        avgtime = 0
        for j in range(batch):
            #print('running batch', j + 1)
            if self.solverFlag == 0:

                if runmode == 0:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver osicbc ' + instance
                else:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver osicbc ' + instance + ' --cbcArgs ' + '"' + arglist + '"'
            elif self.solverFlag == 1:

                if runmode == 0:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver cplex ' + instance + ' --cplex-dll ' + self.cplex_dll
                else:
                    cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' -s --solver cplex ' + instance + ' --readParam ' + cplex_param + ' ' + ' --cplex-dll ' + self.cplex_dll
            #print(cmd)

            stdout_, _ = self.run_cmd(cmd)

            avgtime += float(re.search(b'(?:time=)(\d+\.\d+)', stdout_).group(1))
        avgtime /= batch
        print('Average Time:', avgtime)
        return avgtime


    def run_benchmark(self, batch, instance, stdout_):
        benchmark = {}
        for i in stdout_.split(b'\n'):
            #print(i)
            if len(i) != 0:
                res = [line.rstrip('\n') for line in open(stdout_.split(b'\n')[0].decode('utf-8'))]

                if len(res) == 2:
                    print("No new incumbent found!")
                    continue

                if self.solverFlag == 0:
                    arglist = ''
                elif self.solverFlag == 1:
                    param = 'CPLEX Parameter File Version 12.6\n'

                for i in res[-1].split(',')[5:]:
                    tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
                    if self.solverFlag == 0:
                        arglist += '-' + tmp[0] + ' ' + tmp[1] + ' '
                    elif self.solverFlag == 1:
                        param += tmp[0] + '\t' + tmp[1] + '\n'
                if self.solverFlag == 1:
                    with open('benchmark_cplex_param_cfg', 'w') as f:
                        f.write(param)


                if self.solverFlag == 0:
                    #print(arglist)
                    avgtime = self.run_minizinc(batch, instance, 1, arglist, '')
                    benchmark[arglist] = avgtime

                elif self.solverFlag == 1:
                    #print(param)
                    avgtime = self.run_minizinc(batch, instance, 1, '', 'benchmark_cplex_param_cfg')
                    benchmark[param] = avgtime

        if self.solverFlag == 0 and len(benchmark) != 0:
            avgtime = self.run_minizinc(batch, instance, 0, '', '')
            benchmark['base'] = avgtime
        elif self.solverFlag == 1 and len(benchmark) != 0:
            avgtime = self.run_minizinc(batch, instance, 0, '', '')
            benchmark['base'] = avgtime
        else:
            print("No optimal solution found!")
            return
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
            cmd = 'find ' + os.path.join('./smac-output', self.outputdir) + ' -name traj-run*.txt'
            stdout_, _ = self.run_cmd(cmd)
            self.run_benchmark(batch, instance, stdout_)


    def remove_tmp_files(self):
        cmd = 'rm -R cplex_wrapper_?.py cbc_wrapper_?.py scenario* pre_run_time_check instances.txt benchmark_cplex_param_cfg tmpParamRead* __py* presolved* ' + ' '.join(self.instanceList)
        self.run_cmd(cmd)


class CPLEX(GenericSolverExpansion):

    def __init__(self, solverFlag, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll):
        super().__init__(solverFlag, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll)

    def pSMAC_wrapper_generator(self):
        print('{} Generating CPLEX wrapper for SMAC'.format(self.get_current_timestamp()))
        for i in range(self.nSMAC):
            writeToFile = []
            writeToFile.append('import sys')
            writeToFile.append('sys.path.insert(0, "{}")'.format(path))
            writeToFile.append('from genericSolverSMACOptimization import cplex_wrapper')
            writeToFile.append('cplex_wrapper({}, {}, "{}")'.format(i, self.nThreadMinizinc, self.cplex_dll))
            with open('cplex_wrapper_' + str(i) + '.py', 'w') as f:
                f.write('\n'.join(writeToFile))

    def pSMAC_scenario_generator(self):
        print('{} Generating CPLEX scenario for SMAC'.format(self.get_current_timestamp()))
        for i in range(self.nSMAC):
            writeToFile = []
            writeToFile.append('algo = python -u ./cplex_wrapper_{}.py'.format(i))
            writeToFile.append('pcs-file = ./{}'.format(self.pcsFile))
            writeToFile.append('execdir = .')
            writeToFile.append('deterministic = 1')
            writeToFile.append('runObj = runtime')
            writeToFile.append('overall_obj = MEAN10')
            writeToFile.append('target_run_cputime_limit = {}'.format(self.cutOffTime))
            writeToFile.append('wallclock_limit = {}'.format(self.tuneTimeLimit))
            writeToFile.append('instance_file = instances.txt')
            with open('scenario_' + str(i) + '.txt', 'w') as f:
                f.write('\n'.join(writeToFile))
                #print('scenario_' + str(i) + '.txt')




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

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit ' + str(cutoff * 1000) + ' --solver cplex ' + instance     + ' --readParam tmpParamRead_' + str(n)     + ' --cplex-dll ' + cplex_dll


    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    #io.wait()

    #eprint("stdout:", stdout_.decode('utf-8'), "\nstderr:", stderr_.decode('utf-8'))


    status = "CRASHED"
    runtime = 99999

    if re.search(b'time elapsed:', stdout_):
        runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
        status = "SUCCESS"
    elif re.search(b'=====UNKNOWN=====', stdout_):
        runtime = cutoff
        status = "TIMEOUT"

    print('Result of this algorithm run: {}, {}, {}, 0, {}, {}'.format(status, runtime, runlength, seed, specifics))


def cbc_wrapper(n_thread):

    instance = sys.argv[1]
    specifics = sys.argv[2]
    cutoff = int(float(sys.argv[3]) + 1) # runsolver only rounds down to integer
    runlength = int(sys.argv[4])
    seed = int(sys.argv[5])
    params = sys.argv[6:]

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit ' \
    + str(cutoff * 1000) + ' --solver osicbc ' + instance + ' --cbcArgs "'

    for name, value in zip(params[::2], params[1::2]):
        cmd += ' ' + name + ' ' + value
    cmd += '"'

    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    
    status = "CRASHED"
    runtime = 99999
    
    
    try:
        (stdout_, stderr_) = io.communicate(timeout=cutoff)

        eprint("stdout:", stdout_.decode('utf-8'), "\nstderr:", stderr_.decode('utf-8'))
        
        if re.search(b'time elapsed:', stdout_):
            runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
            status = "SUCCESS"
        elif re.search(b'=====UNKNOWN=====', stdout_):
            runtime = cutoff
            status = "TIMEOUT"        
        
    except subprocess.TimeoutExpired:
        print("timeoutttttttttttttttttt")
        kill(io.pid)
        runtime = cutoff
        status = "TIMEOUT"

    print('Result of this algorithm run: {}, {}, {}, 0, {}, {}'.format(status, runtime, runlength, seed, specifics))

class CBC(GenericSolverExpansion):

    def __init__(self, solverFlag, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll):
        super().__init__(solverFlag, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll)

    def pSMAC_wrapper_generator(self):
        print('{} Generating CBC wrapper for SMAC'.format(self.get_current_timestamp()))
        for i in range(1):
            writeToFile = []
            writeToFile.append('import sys')
            writeToFile.append('sys.path.insert(0, "{}")'.format(path))
            writeToFile.append('from genericSolverSMACOptimization import cbc_wrapper')
            writeToFile.append('cbc_wrapper({})'.format(self.nThreadMinizinc))
            with open('cbc_wrapper_' + str(i) + '.py', 'w') as f:
                f.write('\n'.join(writeToFile))

    def pSMAC_scenario_generator(self):
        print('{} Generating CBC scenario for SMAC'.format(self.get_current_timestamp()))
        for i in range(1):
            writeToFile = []
            writeToFile.append('algo = python -u ./cbc_wrapper_{}.py'.format(i))
            writeToFile.append('pcs-file = ./{}'.format(self.pcsFile))
            writeToFile.append('execdir = .')
            writeToFile.append('deterministic = 1')
            writeToFile.append('runObj = runtime')
            writeToFile.append('overall_obj = MEAN10')
            writeToFile.append('target_run_cputime_limit = {}'.format(self.cutOffTime))
            writeToFile.append('wallclock_limit = {}'.format(self.tuneTimeLimit))
            writeToFile.append('instance_file = instances.txt')
            with open('scenario_' + str(i) + '.txt', 'w') as f:
                f.write('\n'.join(writeToFile))

def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
