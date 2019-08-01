import multiprocessing, glob
from run_minizinc.runtool import *
from helpFunctions.helpFuctions import *




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
        self.timestamp = time.strftime('%y%m%d_%H%M%S', time.localtime(time.time())) # timestamp for careation of output directory
        self.rungroup = self.timestamp + "_SmacModel"
        self.instanceList = None
        self.initialCwd = initialCwd
        self.minizinc_exe = minizinc_exe
        self.maximize = maximize
        self.obj_mode = obj_mode
        self.basicCmd = [minizinc_exe, '--output-mode', 'json', '--output-objective']
        self.lpList = []
        self.setOutputDir(initialCwd)
        self.outputFile = None
        self.wrapper = self.createWrapper()
        self.totalTuningTime = None

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
            eprint('[Wrapper Debug]',args, **kwargs)

    def setOutputDir(self,dir):
        self.outputdir = dir
        self.resultOutput = dir

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
        self.vprint(self.instanceList)
        for instance in self.instanceList:
            paramList = self.default_param_to_list()
            param = self.wrapper.process_param(paramList)
            inslist = self.wrapper.seperateInstance(instance.replace('"', ''))
            cmd = self.wrapper.generate_cmd(param,self.solver,inslist,self.dll)
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
            eprint('{} Calculating Cutoff Time'.format(self.get_current_timestamp()))
            self.cutOffTime = self.instance_runtime() * 3  # Give 3 times of margin of safety for cutoff
        eprint('{} Cutoff Time set as: {}'.format(self.get_current_timestamp(),self.cutOffTime))

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
            self.vprint("call by minizinc mode, instances:",instance)
            model = ''
            datas = []
            for i in instance:
                if re.findall('.mzn', i):
                    model = os.path.abspath(i)
                else:
                    datas.append(os.path.abspath(i))

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
        eprint('{} Generate {} wrapper setting for SMAC'.format(self.get_current_timestamp(),wrapper))
        settingDic = {'solver':wrapper,'threads':self.nThreadMinizinc,\
                      'dll':self.dll,'maximize':self.maximize, \
                      'obj_mode':obj_mode, 'obj_bond':obj_bound,\
                      'verbose':self.verboseOnOff, 'envdic':envdic,\
                      'minizinc_exe':self.minizinc_exe}
        with open('wrapperSetting.json', 'w') as f:
            f.write(json.dumps(settingDic, indent=4))
    
    def pSMAC_scenario_generator(self,obj_mode,tuneTimeLimit,more_runs):
        '''
        Generate scenario file for running the smac.
        '''
        eprint('{} Generating scenario for SMAC'.format(self.get_current_timestamp()))

        writeToFile = []
        if getattr(sys, 'frozen', False):
            # we are running in a bundle
            python = '../wrappers/wrappers'
            if os.name == 'nt':
                python = '../wrappers/wrappers.exe'
        else:
            # we are running in a normal Python environment
            python = str(sys.executable) + ' -u ../wrappers.py'
        writeToFile.append('algo = {}'.format(python))
        writeToFile.append('pcs-file = {}'.format(self.pcsFile))
        writeToFile.append('execdir = .')
        if more_runs:
            writeToFile.append('deterministic = 0')
        else:
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
        files.extend(glob.glob('*.prm'))
        files.extend(glob.glob('*.log'))

        for f in files:
            os.remove(f)


    def benchmark_main(self, batch=5,rows=-3):
        '''
        Find output of smac and ready for benchmark.
        '''
        eprint('{} SMAC optimization completes'.format(self.get_current_timestamp()))
        eprint('{} Benchmarking starts'.format(self.get_current_timestamp()))
        stdout_ = glob.glob(self.outputdir + '/' + self.rungroup + '/traj-run*.txt')
        eprint("Output found: ",stdout_)
        
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
                eprint("Configuration file: ", i)
                res = [line.rstrip('\n') for line in open(i)]
                if len(res) <= 3:
                    eprint("No new incumbent found!")
                    continue
                for setting in res[rows:]:
                    eprint("Average running time of current configuration {} ".format(setting.split(',')[1]))
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
                        eprint('Average Objective:', benchquality[count])
                    else:
                        eprint('Average time:', benchtime[count])

                    count+=1

        if len(benchtime) != 0:
            eprint("Calculting base result: ")
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
                eprint('Average Objective:', benchquality['base'])
            else:
                eprint('Average time:', benchtime['base'])
        else:
            eprint("No optimal solution found!")
            print("=====UNKNOWN=====")
            return

        if not self.obj_mode:
            best_self = min(benchtime, key=benchtime.get)
        elif self.maximize:
            best_self = max(benchquality, key=benchquality.get)
        else:
            best_self = min(benchquality, key=benchquality.get)

        if best_self == 'base':
            eprint("-" * 50)
            eprint("Default setting is best")
            eprint("-" * 50)
            print("=====UNKNOWN=====")
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
        eprint('{} SMAC optimization completes'.format(self.get_current_timestamp()))
        eprint('{} Benchmarking starts'.format(self.get_current_timestamp()))
        self.vprint(self.outputdir +"/" + self.rungroup + '/traj-run*.txt')
        stdout_ = glob.glob(self.outputdir + "/"+ self.rungroup + '/traj-run*.txt')
        eprint("Output found: ", stdout_)

        benchtime = {}
        benchset = {}
        benchquality = {}

        count = 1
        for i in stdout_:
            if len(i) != 0:
                eprint("Configuration file: ", i)
                res = [line.rstrip('\n') for line in open(i)]
                if len(res) == 2:
                    eprint("No new incumbent found!")
                    continue
                for setting in res[rows:]:
                    avgtime = float(setting.split(',')[1])
                    benchtime[count] = avgtime
                    benchset[count] = setting
                    benchquality[count] = avgtime
                    if all:
                        fileName ='Setting' + str(count) + time.strftime('%y%m%d_%H%M%S]', time.localtime(time.time()))
                        outputPath = self.initialCwd+'/'+fileName
                        paramList = self.param_to_list(setting)
                        finalParam = self.wrapper.process_param(paramList, outputPath)
                    count += 1

        if len(benchtime) == 0:
            eprint("No optimal solution found!")
            print("=====UNKNOWN=====")
            return

        if not self.obj_mode:
            best_self = min(benchtime, key=benchtime.get)
        elif self.maximize:
            best_self = max(benchquality, key=benchquality.get)
        else:
            best_self = min(benchquality, key=benchquality.get)

        if best_self == 2:
            eprint("Default setting is best")
            print("=====UNKNOWN=====")
            return

        setting = benchset[best_self]

        self.output_result(setting,benchquality, benchtime, best_self)

    def output_result(self,setting,benchquality,benchtime,best_self):
        try:
            modelName = re.search("([^\\\/]+(\.mzn))",self.instanceList[0]).group(1)
            self.vprint(self.instanceList[0])
            self.vprint(modelName)
        except:
            modelName = ''
        fileName = self.timestamp +"_"+ modelName
        outputPath = self.resultOutput + "/" + fileName
        outputJson = outputPath+'Smac.pcf'

        paramList = self.param_to_list(setting)
        finalParam = self.wrapper.process_param(paramList, outputPath)
        eprint("-" * 50)
        eprint('Recommendation :\n{}'.format(finalParam))
        eprint('Running in {} threads mode'.format(self.nThreadMinizinc))
        eprint('Result: {}'.format(round(benchquality[best_self] if self.obj_mode else benchtime[best_self], 3)))
        self.param_to_json(paramList,outputJson,finalParam, benchquality[best_self] if self.obj_mode else benchtime[best_self])
        eprint("-" * 50)
        print("==========")
                    

    def param_to_list(self,setting):
        '''
        Generate parameter settings with smac output for running the minizinc. Used in benchmark. Also output parameter setting.
        '''
        arglist = []
        for i in setting.split(',')[5:]:
            tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
            if tmp[0] == 'MinizincThreads':
                self.nThreadMinizinc = int(tmp[1])
            else:
                arglist += ['-' + tmp[0], tmp[1]]
        return arglist

    def param_to_json(self,paramList,outputdir,prmPath, performance=None, tuneTool='smac'):
        '''
        Convert smac-output to json format.
        :param setting: parameter in list format
        :param outputdir:
        :return:
        '''
        if self.outputFile is not None:
            outputdir = self.outputFile
        modelName = []
        dataName = []
        for instance in self.instanceList:
            try:
                modelName.append(re.search("([^\\\/]+(\.mzn))",instance).group(1))
            except:
                pass
            try:
                dataName.append(re.search("([^\\\/]+(\.dzn))",instance).group(1))
            except:
                pass

        paramDic = {}
        paramDic['solver'] = self.solver
        paramDic['threads'] = self.nThreadMinizinc
        paramDic['models'] = modelName
        paramDic['instances'] = dataName
        paramDic['estimated average performance'] = performance
        paramDic['tune tool'] = tuneTool
        paramDic['runGroup'] = self.rungroup
        #start=outputdir
        if self.obj_mode:
            paramDic['tune mode'] = 'Objective of feasible solution'
        else:
            paramDic['tune mode'] = 'Time to optimal solution'
        paramDic['solver time limit'] = self.cutOffTime
        paramDic['parameters'] = {}
        paramDic['total tuning time'] = self.totalTuningTime
        if os.path.isfile(prmPath):
            paramDic['prm file path'] = prmPath
        else:
            paramDic['prm file path'] = None


        for name, value in zip(paramList[::2], paramList[1::2]):
            if name == '-MinizincThreads':
                self.nThreadMinizinc = value
                paramDic['threads'] = int(value)
            else:
                paramDic['parameters'][name.strip('-')] = value

        paramJson = json.dumps(paramDic, indent=4)
        with open(outputdir,'w') as f:
            f.write(paramJson)
        eprint('Output To Json Format: ', outputdir)

    
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

    '''
    Functions for Gurobi Tuning Tools
    '''

    def lp_model_generate(self,env=None):
        #convert minizinc model to mps format model, which gurobi can run directly.
        eprint('{} Start converting minizinc model to mps model'.format(self.get_current_timestamp()))
        for instance in self.instanceList:
            try:
                modelName = re.search("([^\\\/]+(\.mzn))",instance).group(1)
            except:
                modelName = ''
            try:
                dataName = re.search("([^\\\/]+(\.dzn))",instance).group(1)
            except:
                dataName = ''
            fullName = modelName+dataName+'.mps'
            inslist = self.wrapper.seperateInstance(instance.replace('"', ''))
            self.vprint(inslist)
            cmd = self.wrapper.generate_cmd(None, self.solver, inslist)
            cmd += ['--writeModel', fullName]
            self.wrapper.output_lp(cmd,1,env)
            eprint('{} mps model file generated: {}'.format(self.get_current_timestamp(),fullName))
            self.lpList.append(fullName)
        eprint('{} Output mps models done'.format(self.get_current_timestamp()))

    def grbTunePrmToList(self,filePath):
        paramList = []
        with open(filePath) as file:
            lines = [line.rstrip('\n') for line in file]

            # Remove any blank lines from  file
            lines = [x for x in lines if x != '']

            for line in lines:
                setting = line.split()
                param = setting[0]
                value = setting[1]
                paramList += ['-'+param,value]
        return paramList


    def grbTuneOutput(self):
        outputDir = self.resultOutput + "/"
        file = glob.glob('tune1.prm')
        log = glob.glob('tune1.log')
        try:
            modelName = re.search("([^\\\/]+(\.mzn))",self.instanceList[0]).group(1)
        except:
            modelName = ''
        fileName = self.timestamp+"_" + modelName
        outputPath = outputDir + fileName+'Grb.prm'
        outputPathLog = outputDir + fileName+'Grb.log'

        if len(file) == 0:
            eprint("-" * 50)
            eprint('{} No improved configuration found'.format(self.get_current_timestamp()))
            eprint("-" * 50)
            print("=====UNKNOWN=====")
            return
        for f in file:
            # remove timelimit and threads from prm file, as these parameter can be set in minizinc. we don't want set them in prm file.
            with open(f,"r") as content:
                lines = content.readlines()

            with open(f,"w") as newfile:
                for line in lines:
                    if line.find('TimeLimit') == -1 and line.find('Threads') == -1:
                        newfile.write(line)

            os.rename("./"+f, outputPath)
            eprint('Output prm file to: ', outputPath)
        for f in log:
            os.rename("./"+f, outputPathLog)
            eprint('Output log file to: ', outputPathLog)

        paramList = self.grbTunePrmToList(outputPath)
        outputPathJson = outputDir + fileName + 'GrbTune.pcf'

        self.param_to_json(paramList, outputPathJson, tuneTool='Gurobi tune tool')
        eprint("-" * 50)
        eprint('Recommendation :\n{}'.format(outputPath))
        eprint('Running in {} threads mode'.format(self.nThreadMinizinc))
        eprint("-" * 50)
        print("==========")








