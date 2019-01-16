import sys, os, re, multiprocessing, psutil, time, inspect
from subprocess import Popen, PIPE
from random import randint

class initializer():
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
            print(instance)
            
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
        modelCount=0
        for i in instance:
            if len(re.findall('([^\.\s]+\.mzn)(?:\s)', i)) > 1: # Require one model file in each line
                raise Exception('More than one model file found in the same line.')
            elif len(re.findall('^[^\.\s]+\.mzn', i)) == 0: # Require model file at first of each line
                raise Exception('Model file must come first in each line.')

            dataCount=0
            model = i.split()[0]
            data = i.split()[1:]
            model = os.path.expanduser(model)
            model = os.path.normpath(model)
            with open(model) as modelFile:
                modelData=modelFile.read()
                if len(data) > 0:
                    for j in data:
                        newName = 'model'+ str(modelCount) +'data'+str(dataCount)+'.mzn' # Get name of combined model file
                        print(newName)
                        dataPath = os.path.expanduser(j)
                        dataPath = os.path.normpath(dataPath)
                        with open(self.programPath+'/cache/'+newName, 'w') as outfile:
                            with open(dataPath) as infile:
                                outfile.write(infile.read())
                                outfile.write(modelData)
                        #print(stdout_)
                        instanceList.append(newName)
                        dataCount+=1
                else:
                    newName="model"+str(modelCount)+'.mzn'
                    with open(self.programPath+'/cache/'+newName, 'w') as outfile:
                        outfile.write(modelData)
                    instanceList.append(newName)
                    dataCount+=1

            modelCount+=1
        with open(self.programPath+'/cache/'+'instances.txt', 'w') as f:
            f.write('\n'.join(instanceList)) # Write the formated instance file to text for smac read in.
        
        self.instanceList=instanceList
        return instanceList # Return the combined file list for removal after smac optimization
    '''
    After tunning operations.
    '''
    def remove_tmp_files(self):
        cmd = 'rm -R cplex_wrapper_?.py cbc_wrapper_?.py *.pcs scenario* pre_run_time_check instances.txt benchmark_cplex_param_cfg tmpParamRead* __py* presolved* ' + ' '.join(self.instanceList)
        self.run_cmd(cmd)

    def benchmark_main(self, batch=5):
        print('{} SMAC optimization completes'.format(self.get_current_timestamp()))
        print('{} Benchmarking starts'.format(self.get_current_timestamp()))
        cmd = 'find ' + os.path.join('./smac-output', self.outputdir) + ' -name traj-run*.txt'
        print("Find result file: ", cmd)
        stdout_, _ = self.run_cmd(cmd)
        print("Output found: ",stdout_)
        
        for instance in self.instanceList:
            self.run_benchmark(batch, instance, stdout_)

    def run_benchmark(self, batch, instance, stdout_):
        benchmark = {}
        benchres = {}
        for i in stdout_.split(b'\n'):
            #print(i)
            if len(i) != 0:
                res = [line.rstrip('\n') for line in open(stdout_.split(b'\n')[0].decode('utf-8'))]
                print("Run to go: ", res)
                if len(res) == 2:
                    print("No new incumbent found!")
                    continue
                params = self.param_generate(res)
                cmd = self.cmd_generate(instance, 1, params)
                avgtime = self.run_minizinc(batch,cmd )
                benchmark[i] = avgtime
                benchres[i] = res
                print('Average Time:', avgtime)

        if len(benchmark) != 0:
            cmd = self.cmd_generate(instance,0, '')
            avgtime = self.run_minizinc(batch,cmd)
            benchmark['base'] = avgtime
            print('Base Time:', avgtime)

        else:
            print("No optimal solution found!")
            return
        #print(benchmark)
        best_args = min(benchmark, key=benchmark.get)
        the_res = benchres[best_args]
        finalParam = self.param_generate(the_res,self.initialCwd+'/'+instance)
        print("=" * 50)
        print('Recommendation for {} :\n{}'.format(instance,finalParam))
        print('Runtime: {}s'.format(round(benchmark[best_args], 3)))
        print("=" * 50)

    def run_minizinc(self, batch, cmd):
        avgtime = 0
        for j in range(batch):            
            stdout_, stderr_ = self.run_cmd(cmd)

            if re.search(b'time elapsed:', stdout_):
                avgtime += float(re.search(b'(?:time=)(\d+\.\d+)', stdout_).group(1))
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



class cbcInitial(initializer):
    def __init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd):
        initializer.__init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd)
    
    def param_generate(self,res,output=None):
        arglist = ''
        for i in res[-1].split(',')[5:]:
            tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
            arglist += '-' + tmp[0] + ' ' + tmp[1] + ' '
        if output is not None:
            with open(output+'cbc_param_config','w') as f:
                f.write(arglist)
        return arglist

    def cmd_generate(self,instance, runmode, params):
        cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' --output-time -s --solver osicbc ' + instance
        if runmode == 1:
            cmd = cmd + ' --cbcArgs ' + '"' + params + '"'
        return cmd


    def default_param_config_generation(self):
        '''
        Read default parameters from the parameter configuration space
        '''
        lines = [line.rstrip('\n') for line in open(self.pcsFile)]
        paramList = []

        for line in lines:
            if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
                default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
                paramList.append('-' + line.split()[0] + ' ' + str(default_val))

        return ' '.join(paramList)
        
    
    def pSMAC_wrapper_generator(self):
        '''
        The wrapper generated by this program will be directly used by SMAC.
        SMAC will run minizinc through this wrapper.
        '''
        print('{} Generating CBC wrapper for SMAC'.format(self.get_current_timestamp()))
        for i in range(1):
            writeToFile = []
            writeToFile.append('import sys')
            writeToFile.append('sys.path.insert(0, "{}")'.format(self.programPath))
            writeToFile.append('from wrappers import cbc_wrapper')
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

class cplexInitial(initializer):
    def __init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd):
        initializer.__init__(self, cutOffTime, tuneTimeLimit, verboseOnOff, pcsFile, nThreadMinizinc, insPath, insList, cplex_dll,programPath,psmac,initialCwd)
    
    def param_generate(self,res,output=None):
        param = 'CPLEX Parameter File Version 12.6\n'
        for i in res[-1].split(',')[5:]:
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
        cmd = 'minizinc -p' + str(self.nThreadMinizinc) + ' --output-time -s --solver cplex ' + instance + ' --cplex-dll ' + self.cplex_dll
        if runmode == 1:
            cmd = cmd + ' --readParam ' + params + ' '
        return cmd

    def default_param_config_generation(self):
        '''
        Read default parameters from the parameter configuration space
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
    
    def pSMAC_wrapper_generator(self):
        '''
        The wrapper generated by this program will be directly used by SMAC.
        SMAC will run minizinc through this wrapper.
        '''
        print('{} Generating CPLEX wrapper for SMAC'.format(self.get_current_timestamp()))
        for i in range(self.psmac):
            writeToFile = []
            writeToFile.append('import sys')
            writeToFile.append('sys.path.insert(0, "{}")'.format(self.programPath))
            writeToFile.append('from wrappers import cplex_wrapper')
            writeToFile.append('cplex_wrapper({}, {}, "{}")'.format(i, self.nThreadMinizinc, self.cplex_dll))
            with open('cplex_wrapper_' + str(i) + '.py', 'w') as f:
                f.write('\n'.join(writeToFile))

    def pSMAC_scenario_generator(self):
        print('{} Generating CPLEX scenario for SMAC'.format(self.get_current_timestamp()))
        for i in range(self.psmac):
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