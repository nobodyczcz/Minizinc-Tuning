import multiprocessing, glob
from run_minizinc.runtool import *



class Initializer():
    '''
    This class handle the initialization of tunning,
    which include prepare all required files under cache directory.
    '''

    def __init__(self,solver, cutOffTime,  verboseOnOff, pcsFile, nThreadMinizinc, insPath, dll, initialCwd, minizinc_exe,maximize, obj_mode=False):
        self.solver = solver
        self.cutOffTime = cutOffTime # cutoff time for Minizinc per run
        self.verboseOnOff = verboseOnOff # specifies the logging-verbisity
        self.pcsFile = pcsFile # parameter configuration space file
        self.nThreadMinizinc = nThreadMinizinc # number of threads allocated to per Minizinc
        self.insPath = insPath # path for file listing all instances for optimization
        self.dll = dll # path for cplex-dll
        self.timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())) + '_' + str(randint(1, 999999)) # timestamp for careation of output directory
        self.outputdir = 'runs_' + self.timestamp # output directory naming convention
        self.instanceList = None
        self.initialCwd = initialCwd
        self.minizinc_exe = minizinc_exe
        self.maximize = maximize
        self.obj_mode = obj_mode
        self.basicCmd = [minizinc_exe, '--output-mode', 'json', '--output-objective']

        self.wrapper = self.createWrapper()

    def createWrapper(self):
        if self.solver == "osicbc":
            wrapper = OsicbcWrapper(self.solver, self.nThreadMinizinc, self.verboseOnOff, self.minizinc_exe)
        elif self.solver == "cplex":
            wrapper = CplexWrapper(self.solver, self.nThreadMinizinc, self.verboseOnOff, self.minizinc_exe)
        elif self.solver == "gurobi":
            wrapper = GurobiWrapper(self.solver, self.nThreadMinizinc, self.verboseOnOff, self.minizinc_exe)

        else:
            raise Exception("Do not support solver: ", self.solver)
        return wrapper

    def vprint(self,*args, **kwargs):
        if self.verboseOnOff:
            print('[Wrapper Debug]',*args, file=sys.stderr, **kwargs)

    def get_current_timestamp(self):
        '''
        Get current timestamp
        '''
        return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))

    def instance_runtime(self):
        '''
        Run all the instances and get the running time of longgest one.
        '''
        runtime = -1
        for instance in self.instanceList:
            paramList = self.default_param_to_list()
            param = self.wrapper.process_param(paramList)
            inslist = self.wrapper.seperateInstance(instance.replace('"', ''))
            self.vprint(inslist)
            cmd = self.wrapper.generate_cmd(param,self.solver,inslist)
            status,time,quality = self.wrapper.runMinizinc_time(cmd)

            if status == "CRASHED":
                raise Exception("[Wrapper error] Run failed with default parameter")
            #print(tmp)
            if time > runtime:
                runtime = time
        return runtime

    def cut_off_time_calculation(self):
        '''
        Get cutoff time if user does not specify
        '''
        if self.cutOffTime == 0:
            print('{} Calculating Cutoff Time'.format(self.get_current_timestamp()))
            self.cutOffTime = self.instance_runtime() * 3  # Give 3 times of margin of safety for cutoff
        print('{} Cutoff Time set as: {}'.format(self.get_current_timestamp(),self.cutOffTime))

    def thread_check(self, psmac):
        '''
        Check Setting for Psmac. Raise exception if threads that psmac use larger than total
        cpu threads avaliable  
        '''
        n_cores = multiprocessing.cpu_count() # Get number of threads available in the system
        if n_cores < (psmac*self.nThreadMinizinc):
            raise Exception("{} threads found in the system. However {} threads will be used for parallel search.".format(n_cores, (self.nThreadMinizincsmac*self.nThreadMinizinc)))

    def process_instance(self,insList,programPath,isminizinc=False):
        '''
        Process instance list or path to combine the model file with instance file(s) and write to a txt file with standard format for SMAC.
        '''

        if len(insList) != 0: # If list of instance is provided
            
            instance = insList
            
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

        if isminizinc: # minizinc IDE use a different way to pass models and datas to tuning program
            model = ''
            datas = []
            for i in instance:
                if re.findall('.mzn', i):
                    model = i
                else:
                    datas.append(i)

            if len(datas) > 0:
                for data in datas:
                    theInstance = model + '|' + data
                    instanceList.append('"' + theInstance + '"')
            else:
                theInstance = model
                instanceList.append('"' + theInstance + '"')

        else:
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

        with open(programPath+'/cache/'+'instances.txt', 'w') as f:
            strings = '\n'.join(instanceList)
            strings = strings.replace('\\', '\\\\')
            f.write(strings) # Write the formated instance file to text for smac read in.
        
        self.instanceList=instanceList
        return instanceList # Return the combined file list for removal after smac optimization

    def wrapper_setting_generator(self,wrapper,obj_bound,obj_mode,envdic = None):
        '''
        The wrapper generated by this program will be directly used by SMAC.
        SMAC will run minizinc through this wrapper.
        '''
        print('{}Wrapper setting Generating {} for SMAC'.format(self.get_current_timestamp(),wrapper))
        settingDic = {'solver':wrapper,'threads':self.nThreadMinizinc,\
                      'dll':self.dll,'maximize':self.maximize, \
                      'obj_mode':obj_mode, 'obj_bond':obj_bound,\
                      'verbose':self.verboseOnOff, 'envdic':envdic,\
                      'minizinc_exe':self.minizinc_exe}
        with open('wrapperSetting.json', 'w') as f:
            f.write(json.dumps(settingDic, indent=4))
    
    def pSMAC_scenario_generator(self,obj_mode,tuneTimeLimit):
        '''
        Generate scenario file for running the smac.
        '''
        print('{} Generating scenario for SMAC'.format(self.get_current_timestamp()))

        writeToFile = []
        if getattr(sys, 'frozen', False):
            # we are running in a bundle
            python = '../wrappers/wrappers'
        else:
            # we are running in a normal Python environment
            python = str(sys.executable) + ' -u ../wrappers.py'
        writeToFile.append('algo = {}'.format(python))
        writeToFile.append('pcs-file = {}'.format(self.pcsFile))
        writeToFile.append('execdir = .')
        writeToFile.append('deterministic = 1')
        if obj_mode:
            writeToFile.append('runObj = QUALITY')
            writeToFile.append('overall_obj = MEAN')
        else:
            writeToFile.append('runObj = runtime')
            writeToFile.append('overall_obj = MEAN10')
        writeToFile.append('target_run_cputime_limit = {}'.format(self.cutOffTime))
        writeToFile.append('wallclock_limit = {}'.format(tuneTimeLimit))
        writeToFile.append('instance_file = instances.txt')
        with open('scenario_' + '.txt', 'w') as f:
            f.write('\n'.join(writeToFile))

    '''
    After tunning operations.
    '''
    def remove_tmp_files(self):
        files = glob.glob('*.py')
        files.extend(glob.glob('*.pcs'))
        files.extend(glob.glob('scenario*'))
        files.extend(glob.glob('pre_run_time_check'))
        files.extend(glob.glob('instances.txt'))
        files.extend(glob.glob('benchmark_cplex_param_cfg'))
        files.extend(glob.glob('presolved*'))
        files.extend(glob.glob('[*'))
        files.extend(glob.glob('pid*'))

        for f in files:
            os.remove(f)


    def benchmark_main(self, batch=5,rows=-3):
        '''
        Find output of smac and ready for benchmark.
        '''
        print('{} SMAC optimization completes'.format(self.get_current_timestamp()))
        print('{} Benchmarking starts'.format(self.get_current_timestamp()))
        stdout_ = glob.glob('./smac-output/'+self.outputdir+'/traj-run*.txt')
        print("Output found: ",stdout_)
        
        self.run_benchmark(batch, stdout_,rows)

    def run_benchmark(self, batch, stdout_,rows):
        '''
        Run benchmark for each configuration found in smac output. Choose the best one and output it to user directory.
        '''
        benchtime = {}
        benchquality = {}
        benchset = {}
        count = 1
        self.wrapper.cutoff = self.cutOffTime
        for i in stdout_:
            if len(i) != 0:
                print("Configuration file: ", i)
                res = [line.rstrip('\n') for line in open(i)]
                if len(res) <= 3:
                    print("No new incumbent found!")
                    continue
                for setting in res[rows:]:
                    print("Average running time of current configuration {} ".format(setting.split(',')[1]))
                    avgtime = []
                    avgquality = []
                    for instance in self.instanceList:
                        paramList = self.param_to_list(setting)
                        param = self.wrapper.process_param(paramList)
                        inslist = self.wrapper.seperateInstance(instance.replace('"', ''))
                        cmd = self.wrapper.generate_cmd(param, self.solver, inslist)
                        outputtime, quality = self.average_output(batch, cmd)
                        avgtime.append(outputtime)
                        avgquality.append(quality)
                    benchtime[count] = sum(avgtime)/len(avgtime)
                    benchset[count] = setting
                    benchquality[count] = sum(avgquality)/len(avgquality)
                    if self.obj_mode:
                        print('Average Objective:', avgquality)
                    else:
                        print('Average time:', avgtime)

                    count+=1

        if len(benchtime) != 0:
            print("Calculting base result: ")
            avgtime=[]
            avgquality=[]
            for instance in self.instanceList:
                paramList = self.default_param_to_list()
                param = self.wrapper.process_param(paramList)
                inslist = self.wrapper.seperateInstance(instance.replace('"', ''))
                cmd = self.wrapper.generate_cmd(param, self.solver, inslist)
                outputtime, quality = self.average_output(1,cmd) #usally base is very slow, so only run 1 time for base time.
                avgtime.append(outputtime)
                avgquality.append(quality)
            benchtime['base'] = sum(avgtime)/len(avgtime)
            benchquality['base'] = sum(avgquality)/len(avgquality)
            if self.obj_mode:
                print('Average Objective:', avgquality)
            else:
                print('Average time:', avgtime)
        else:
            print("No optimal solution found!")
            return

        if not self.obj_mode:
            best_self = min(benchtime, key=benchtime.get)
        elif self.maximize:
            best_self = max(benchquality, key=benchquality.get)
        else:
            best_self = min(benchquality, key=benchquality.get)

        if best_self == 'base':
            print("=" * 50)
            print("Default setting is best")
            print("=" * 50)
            return

        setting = benchset[best_self]
        self.output_result(setting,benchquality, benchtime, best_self)


    def average_output(self, batch, cmd):
        '''
        run minizinc for batch times. calculate average runtime. Used in benchmark
        '''
        avgtime = 0
        avgquality = 0
        for j in range(batch):
            if self.obj_mode:
                status, runtime, quality = self.wrapper.runMinizinc_obj_mode(cmd)
            else:
                status, runtime, quality = self.wrapper.runMinizinc_time(cmd)
            avgtime += runtime
            avgquality += quality

        avgtime /= batch
        avgquality /= batch
        return avgtime, avgquality
    
    def noBnechOutput(self,rows=-2,all=False):
        '''
        Find output of smac and ready for benchmark.
        '''
        print('{} SMAC optimization completes'.format(self.get_current_timestamp()))
        print('{} Benchmarking starts'.format(self.get_current_timestamp()))
        stdout_ = glob.glob('./smac-output/' + self.outputdir + '/traj-run*.txt')
        print("Output found: ", stdout_)

        benchtime = {}
        benchset = {}
        benchquality = {}

        count = 1
        for i in stdout_:
            if len(i) != 0:
                print("Configuration file: ", i)
                res = [line.rstrip('\n') for line in open(i)]
                if len(res) == 2:
                    print("No new incumbent found!")
                    continue
                for setting in res[rows:]:
                    avgtime = float(setting.split(',')[1])
                    benchtime[count] = avgtime
                    benchset[count] = setting
                    benchquality[count] = avgtime
                    if all:
                        fileName ='Setting' + str(count) + time.strftime('[%Y%m%d%H%M%S]', time.localtime(time.time()))
                        outputPath = self.initialCwd+'/'+fileName
                        paramList = self.param_to_list(setting)
                        finalParam = self.wrapper.process_param(paramList, outputPath)
                    count += 1

        if len(benchtime) == 0:
            print("No optimal solution found!")
            return

        if not self.obj_mode:
            best_self = min(benchtime, key=benchtime.get)
        elif self.maximize:
            best_self = max(benchquality, key=benchquality.get)
        else:
            best_self = min(benchquality, key=benchquality.get)

        if best_self == 2:
            print("Default setting is best")
            return

        setting = benchset[best_self]

        self.output_result(setting,benchquality, benchtime, best_self)

    def output_result(self,setting,benchquality,benchtime,best_self):
        try:
            modelName = re.search("([^\\\/]+(.mzn))",self.instanceList[0]).group(1)
        except:
            modelName = ''
        fileName = time.strftime('[%Y%m%d%H%M%S]', time.localtime(time.time()))+ modelName
        outputPath = self.initialCwd + '/' + fileName
        outputJson = outputPath+'.json'
        paramList = self.param_to_list(setting)
        finalParam = self.wrapper.process_param(paramList, outputPath)
        print("=" * 50)
        print('Recommendation :\n{}'.format(finalParam))
        print('Running in {} threads mode'.format(self.nThreadMinizinc))
        print('Result: {}'.format(round(benchquality[best_self] if self.obj_mode else benchtime[best_self], 3)))
        self.param_to_json(setting,outputJson)
        print("=" * 50)
                    

    def param_to_list(self,setting):
        '''
        Generate parameter settings for running the minizinc. Used in benchmark. Also output parameter setting.
        '''
        arglist = []
        for i in setting.split(',')[5:]:
            tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
            if tmp[0] == 'MinizincThreads':
                self.nThreadMinizinc = int(tmp[1])
            else:
                arglist += ['-' + tmp[0], tmp[1]]
        return arglist

    def param_to_json(self,setting,outputdir):
        modelName = []
        dataName = []
        for instance in self.instanceList:
            try:
                modelName.append(re.search("([^\\\/]+(.mzn))",instance).group(1))
            except:
                pass
            try:
                dataName.append(re.search("([^\\\/]+(.dzn))",instance).group(1))
            except:
                pass

        paramDic = {}
        paramDic['solver'] = self.solver
        paramDic['threads'] = self.nThreadMinizinc
        paramDic['models'] = modelName
        paramDic['instances'] = dataName
        paramDic['paramters'] = {}
        for i in setting.split(',')[5:]:
            tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
            if tmp[0] == 'MinizincThreads':
                self.nThreadMinizinc = int(tmp[1])
                paramDic['threads'] = int(tmp[1])
            else:
                paramDic['paramters'][tmp[0]] = tmp[1]
        paramJson = json.dumps(paramDic, indent=4)
        with open(outputdir,'w') as f:
            f.write(paramJson)
        print('Output To Json Format: ', outputdir)


    
    def default_param_to_list(self):
        '''
        Read SMAC pcs configration file and get default parameter settings from the parameter configuration space
        '''
        lines = [line.rstrip('\n') for line in open(self.pcsFile)]
        paramList = []

        for line in lines:
            if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
                default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
                paramList.append('-' + line.split()[0])
                paramList.append(str(default_val))
        return paramList
