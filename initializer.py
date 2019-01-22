import sys, os, re, multiprocessing, psutil, time, inspect,shlex
from subprocess import Popen, PIPE, TimeoutExpired
from random import randint


class Initializer():
    '''
    This class handle the initialization of tunning,
    which include prepare all required files under cache directory.
    '''

    def __init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd):
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
        self.programPath = programPath
        self.psmac = psmac
        self.instanceList = None
        self.initialCwd = initialCwd
    

    def get_current_timestamp(self):
        '''
        Get current timestamp
        '''
        return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))

    def run_cmd(self, cmd,cutOffTime=None):
        '''
        Excecute command line arguments in the background
        '''
        cmd = shlex.split(cmd)
        io = Popen(cmd, stdout=PIPE, stderr=PIPE)
        try:
            if cutOffTime is not None:
                (stdout_, stderr_) = io.communicate(timeout=cutOffTime)
                
            else:
                (stdout_, stderr_) = io.communicate()
            #io.wait()
            #if len(stdout_) == 0:
            #    raise Exception(stderr_.decode('utf-8'))
            #else:
            #    return stdout_, stderr_
            
        except TimeoutExpired as e:
            io.kill()
            print('Time out')
        return stdout_, stderr_

    def run_solver(self,instance):
        '''
        run solver is different for each solver, define it in child class.
        '''
        raise NotImplementedError("Must override methodB")

    def instance_runtime(self):
        '''
        Run all the instances and get the running time of longgest one.
        '''
        runtime = -1
        for instance in self.instanceList:
            #print(instance)
            #tmp = self.run_solver(instance)
            cmd = self.cmd_generate(instance,1,self.default_param_config_generation())
            tmp = self.run_minizinc(1,cmd)
            #print(tmp)
            if tmp > runtime:
                runtime = tmp
        return runtime

    def cut_off_time_calculation(self):
        '''
        Get cutoff time if user does not specify
        '''
        print('{} Calculating Cutoff Time'.format(self.get_current_timestamp()))
        if self.cutOffTime == 0:
            self.cutOffTime = self.instance_runtime() * 3 # Give 3 times of margin of safety for cutoff
        print("done")
        print('CutoffTime set as: ',self.cutOffTime)

    def process_thread(self):
        '''
        Check Setting for Psmac. Raise exception if threads that psmac use larger than total
        cpu threads avaliable  
        '''
        n_cores = multiprocessing.cpu_count() # Get number of threads available in the system
        if n_cores < (self.psmac*self.nThreadMinizinc):
            raise Exception("{} threads found in the system. However {} threads will be used for parallel search.".format(n_cores, (self.psmac*self.nThreadMinizinc)))

    def process_instance(self):
        '''
        Process instance list or path to combine the model file with instance file(s) and write to a txt file with standard format for SMAC.
        '''
        
        #print('list',self.insList)
        #print('path',self.insPath)
        
        if len(self.insList) != 0: # If list of instance is provided
            
            instance = self.insList
            
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

            model = i.split()[0]
            data = i.split()[1:]
            model = os.path.expanduser(model)
            model = os.path.abspath(model)

            if len(data) > 0:
                for j in data:
                    dataPath = os.path.expanduser(j)
                    dataPath = os.path.abspath(dataPath)
                    theInstance = model+'|'+dataPath
                    instanceList.append('"'+theInstance+'"')
            else:
                theInstance = model
                instanceList.append('"'+theInstance+'"')

        with open(self.programPath+'/cache/'+'instances.txt', 'w') as f:
            f.write('\n'.join(instanceList)) # Write the formated instance file to text for smac read in.
        
        self.instanceList=instanceList
        return instanceList # Return the combined file list for removal after smac optimization

    def pSMAC_wrapper_generator(self,wrapper):
        '''
        The wrapper generated by this program will be directly used by SMAC.
        SMAC will run minizinc through this wrapper.
        '''
        print('{} Generating {} for SMAC'.format(self.get_current_timestamp(),wrapper))
        writeToFile = []
        writeToFile.append('import sys')
        writeToFile.append('sys.path.insert(0, "{}")'.format(self.programPath))
        writeToFile.append('from wrappers import '+wrapper)
        writeToFile.append('{}({}, "{}")'.format(wrapper,self.nThreadMinizinc, self.cplex_dll))
        with open(wrapper+'_' + '.py', 'w') as f:
            f.write('\n'.join(writeToFile))
    
    def pSMAC_scenario_generator(self,wrapper):
        '''
        Generate scenario file for running the smac.
        '''
        print('{} Generating scenario for SMAC'.format(self.get_current_timestamp()))
        python = sys.executable
        writeToFile = []
        writeToFile.append('algo = {} -u ./{}_.py'.format(python,wrapper))
        writeToFile.append('pcs-file = ./{}'.format(self.pcsFile))
        writeToFile.append('execdir = .')
        writeToFile.append('deterministic = 1')
        writeToFile.append('runObj = runtime')
        writeToFile.append('overall_obj = MEAN10')
        writeToFile.append('target_run_cputime_limit = {}'.format(self.cutOffTime))
        writeToFile.append('wallclock_limit = {}'.format(self.tuneTimeLimit))
        writeToFile.append('instance_file = instances.txt')
        with open('scenario_' + '.txt', 'w') as f:
            f.write('\n'.join(writeToFile))

    '''
    After tunning operations.
    '''
    def remove_tmp_files(self):
        cmd = 'rm -R cplex_wrapper_?.py cbc_wrapper_?.py *.pcs scenario* pre_run_time_check instances.txt benchmark_cplex_param_cfg tmpParamRead* __py* presolved* '
        self.run_cmd(cmd)

    def benchmark_main(self, batch=5,rows=-3):
        '''
        Find output of smac and ready for benchmark.
        '''
        print('{} SMAC optimization completes'.format(self.get_current_timestamp()))
        print('{} Benchmarking starts'.format(self.get_current_timestamp()))
        cmd = 'find ' + os.path.join('./smac-output', self.outputdir) + ' -name traj-run*.txt'
        print("Find result file: ", cmd)
        stdout_, _ = self.run_cmd(cmd)
        print("Output found: ",stdout_)
        
        for instance in self.instanceList:
            self.run_benchmark(batch, instance, stdout_,rows)

    def run_benchmark(self, batch, instance, stdout_,rows):
        '''
        Run benchmark for each configuration found in smac output. Choose the best one and output it to user directory.
        '''
        benchmark = {}
        benchset = {}
        count = 1
        for i in stdout_.split(b'\n'):
            if len(i) != 0:
                print("Configuration file: ", i)
                res = [line.rstrip('\n') for line in open(i.decode('utf-8'))]
                if len(res) == 2:
                    print("No new incumbent found!")
                    continue
                for setting in res[rows:]:
                    print("Current Configeration: ",setting)
                    params = self.param_generate(setting)
                    cmd = self.cmd_generate(instance, 1, params)
                    try:
                        avgtime = self.run_minizinc(batch,cmd,self.cutOffTime )
                        benchmark[count] = avgtime
                        benchset[count] = setting
                        print('Average Time:', avgtime)
                    except:
                        print('No solution. Could be out of time limit.')
                    count+=1

        if len(benchmark) != 0:
            print("Calculting base time: ")
            cmd = self.cmd_generate(instance,0, '')
            avgtime = self.run_minizinc(1,cmd,self.cutOffTime) #usally base is very slow, so only run 1 time for base time.
            benchmark['base'] = avgtime
            print('Base Time:', avgtime)
        else:
            print("No optimal solution found!")
            return
        #print(benchmark)
        best_args = min(benchmark, key=benchmark.get)
        if best_args == 'base':
            print("Default setting is best")
            return
        setting = benchset[best_args]
        modelName = re.search("([^\/]+(.mzn))",instance).group(1)
        dataName = re.search("([^\/]+(.dzn))",instance).group(1)
        fileName = modelName + dataName + time.strftime('[%Y%m%d%H%M%S]', time.localtime(time.time()))
        finalParam = self.param_generate(setting,self.initialCwd+'/'+fileName)
        print("=" * 50)
        print('Recommendation for {} :\n{}'.format(instance,finalParam))
        print('Runtime: {}s'.format(round(benchmark[best_args], 3)))
        print("=" * 50)

    def run_minizinc(self, batch, cmd,cutOffTime=None):
        '''
        run minizinc for batch times. calculate average runtime. Used in benchmark
        '''
        avgtime = 0
        for j in range(batch):            
            t=time.time()
            stdout_, stderr_ = self.run_cmd(cmd,cutOffTime)
            if re.search(b'time elapsed:', stdout_):
                
                avgtime += time.time()-t
            else:
                print(stderr_)
                raise Exception("No solution")
        avgtime /= batch
        return avgtime

    def param_generate(self, res,output=None):
        raise Exception("Must overide param_generate in child class")
    
    def cmd_generate(self,instance, runmode, params):
        raise Exception("Must overide cmd_generate in child class")
    
    def default_param_config_generation(self):
        raise Exception("Must overide default_param_config_generation in child class")



class CbcInitial(Initializer):
    def __init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd):
        Initializer.__init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd)
    
    def param_generate(self,setting,output=None):
        '''
        Generate parameter settings for running the minizinc. Used in benchmark. Also output parameter setting.
        '''
        arglist = ''
        for i in setting.split(',')[5:]:
            tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
            arglist += '-' + tmp[0] + ' ' + tmp[1] + ' '
        if output is not None:
            with open(output+'cbc_param_config','w') as f:
                f.write(arglist)
        return arglist

    def cmd_generate(self,instance, runmode, params):
        '''
        Generate the commands used for run minizinc
        '''
        temp = instance.replace('"','').split('|')
        instance = ''
        for i in temp:
            i = '"'+i+'" '
            instance = instance + i
        cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' --output-time -s --solver osicbc ' + instance
        if runmode == 1:
            cmd = cmd + ' --cbcArgs ' + '"' + params + '"'
        return cmd


    def default_param_config_generation(self):
        '''
        Read SMAC pcs configration file and get default parameter settings from the parameter configuration space
        '''
        lines = [line.rstrip('\n') for line in open(self.pcsFile)]
        paramList = []

        for line in lines:
            if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
                default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
                paramList.append('-' + line.split()[0] + ' ' + str(default_val))

        return ' '.join(paramList)

class CplexInitial(Initializer):
    def __init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd):
        Initializer.__init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd)
    
    def param_generate(self,setting,output=None):
        '''
        Generate parameter setting files for running the minizinc. Used in benchmark.Also output parameter setting.
        '''
        param = 'CPLEX Parameter File Version 12.6\n'
        for i in setting.split(',')[5:]:
            tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
            param += tmp[0] + '\t' + tmp[1] + '\n'

        with open('benchmark_cplex_param_cfg', 'w') as f:
            f.write(param)

        if output is not None:
            with open(output+'cplex_param_cfg','w') as f:
                f.write(param)
            return output+'cplex_param_cfg'
        return 'benchmark_cplex_param_cfg'
    
    def cmd_generate(self,instance, runmode, params):
        '''
        Generate the commands used for run minizinc
        '''
        temp = instance.replace('"','').split('|')
        instance = ''
        for i in temp:
            i = '"'+i+'" '
            instance = instance + i
        cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' --output-time -s --solver cplex ' + instance + ' --cplex-dll ' + self.cplex_dll
        if runmode == 1:
            cmd = cmd + ' --readParam ' + params + ' '
        return cmd

    def default_param_config_generation(self):
        '''
        Read SMAC pcs configration file and get default parameter settings from the parameter configuration space
        '''

        lines = [line.rstrip('\n') for line in open(self.pcsFile)]
        paramList = []

        for line in lines:
            if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
                default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
                paramList.append(line.split()[0] + '\t' + str(default_val))

        paramList.insert(0, 'CPLEX Parameter File Version 12.6')
        with open('pre_run_time_check', 'w') as f:
            f.write('\n'.join(paramList))
        return "pre_run_time_check"


class GurobiInitial(Initializer):
    def __init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,
                 programPath, psmac, initialCwd):
        Initializer.__init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList,
                             cplex_dll, programPath, psmac, initialCwd)

    def param_generate(self, setting, output=None):
        '''
        Generate parameter setting files for running the minizinc. Used in Benchmark. Also output parameter setting.
        '''
        fileName = 'benchmark_gurobi_param_cfg'
        param = '# Parameter Setting for Gurobi\n'
        for i in setting.split(',')[5:]:
            tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
            param += tmp[0] + '\t' + tmp[1] + '\n'

        with open(fileName, 'w') as f:
            f.write(param)

        if output is not None:
            with open(output + fileName, 'w') as f:
                f.write(param)
            return output + fileName
        return fileName

    def cmd_generate(self, instance, runmode, params):
        '''
        Generate the commands used for run minizinc
        '''
        temp = instance.replace('"', '').split('|')
        instance = ''
        for i in temp:
            i = '"' + i + '" '
            instance = instance + i
        cmd = 'minizinc -p' + str(
            self.nThreadMinizinc) + ' --output-time -s --solver gurobi ' + instance
        if runmode == 1:
            cmd = cmd + ' --readParam ' + params + ' '
        return cmd

    def default_param_config_generation(self):
        '''
        Read SMAC pcs configration file and get default parameter settings from the parameter configuration space
        '''

        lines = [line.rstrip('\n') for line in open(self.pcsFile)]
        paramList = []

        for line in lines:
            if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
                default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
                paramList.append(line.split()[0] + '\t' + str(default_val))

        paramList.insert(0, '# Parameter Setting for Gurobi')
        with open('pre_run_time_check', 'w') as f:
            f.write('\n'.join(paramList))
        return "pre_run_time_check"
