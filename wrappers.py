import sys, os, re, time, json
from subprocess import Popen, PIPE, TimeoutExpired
from random import randint

'''
This file store the wrapper of solvers which will be directly called by SMAC.
'''


def eprint( *args, **kwargs):
    """
    A help funtion that print to stderr
    """
    print(*args, file=sys.stderr, **kwargs)

class Wrapper():
    def __init__(self, solver, threads, verbose):
        self.instance = self.seperateInstance(sys.argv[1])
        self.specifics = sys.argv[2]
        self.cutoff = int(float(sys.argv[3]) + 1)  # runsolver only rounds down to integer
        self.runlength = int(sys.argv[4])
        self.seed = int(sys.argv[5])
        self.params = sys.argv[6:]
        self.time_limit = 0
        self.solver = solver
        self.threads = threads
        self.basicCmd = ['minizinc', '-s', '--output-time', '--solver', solver] + self.instance
        self.verbose = verbose

    def vprint(self,*args, **kwargs):
        if self.verbose:
            print('[Wrapper Debug]',*args, file=sys.stderr, **kwargs)
    def get_current_timestamp(self):
        '''
        Get current timestamp
        '''
        return time.strftime('[%Y%m%d%H%M%S]', time.localtime(time.time()))

    def seperateInstance(self,instance):
        '''
        Handle the instance input from argument
        '''
        temp = instance.split('|')
        instance = []
        for i in temp:
            instance.append(i)
        return instance

    def runMinizinc_obj_cut(self,cmd,maximize,obj_bound=None):
        """
        The function will execute the command line and return running result.
        :param cmd: the command line will be executed
        :param cutoff: cut off time of each run
        :return: status, runtime, quality
        """
        t = time.time()

        cmd += ['--time-limit', str(self.cutoff*1000), '-a']
        self.vprint('[Wraper out]', cmd)
        io = Popen(cmd, stdout=PIPE, stderr=PIPE)

        try:
            pidFile = "pid"+str(io.pid)
            with open(pidFile, 'w') as f:
                f.write(str(io.pid))
        except:
            pass

        status = None
        quality = None
        runtime = self.cutoff
        try:
            while io.poll() is None:
                line = io.stdout.readline().decode('utf-8')
                try:
                    quality = float(re.search('(?:%%mzn-stat objective=)((\d+\.\d+)|(\d+))', line).group(1))
                    self.vprint('[Minizinc Out] Find mzn-stat objective=', str(quality))
                    self.vprint('[Minizinc Out] the line', str(line))

                    runtime = time.time() - t
                except:
                    pass
                if obj_bound is not None:
                    if maximize and quality is not None:
                        if quality >= obj_bound:
                            status = 'SUCCESS'
                            self.vprint('[Wrapper] Reach Obj bound:', str(quality))
                            break
                    elif quality is not None:
                        if quality <= obj_bound:
                            status = 'SUCCESS'
                            self.vprint('[Wrapper] Reach Obj bound:', str(quality))
                            break
            io.terminate()
            (stdout_, stderr_) = io.communicate()
            if status == 'SUCCESS':
                if maximize:
                    quality = -quality
            else:
                status = 'TIMEOUT'
                quality = 1.0E9
                runtime = self.cutoff

        except:
            io.terminate()
            status = "CRASHED"
            runtime = self.cutoff
            quality = 1.0E9
        finally:
            try:
                os.remove(pidFile)
            except:
                pass
        return status, runtime, quality

    def runMinizinc_time(self,cmd,maximize):
        t = time.time()
        self.vprint('[Wraper out]', cmd)

        io = Popen(cmd, stdout=PIPE, stderr=PIPE)

        try:
            pidFile = "pid" + str(io.pid)
            with open(pidFile, 'w') as f:
                f.write(str(io.pid))
        except:
            pass

        status = None
        quality = None
        runtime = self.cutoff

        try:
            (stdout_, stderr_) = io.communicate(timeout=self.cutoff)

            self.vprint('[MiniZinc out] ', stdout_.decode('utf-8'))
            runtime = time.time() - t

            if re.search(b'time elapsed:', stdout_):
                status = "SUCCESS"
                quality = float(re.search(b'(?:%%mzn-stat objective=)((\d+\.\d+)|(\d+))', stdout_).group(1))
                self.vprint('[Wrapper] Run success')
                self.vprint('[Wrapper] run time ', str(runtime))

                if maximize:
                    quality = -quality

            elif re.search(b'=====UNKNOWN=====', stdout_):
                self.vprint('[MiniZinc Warn][UNKNOWN][stderr]', stderr_.decode('utf-8'))
                status = "CRASHED"
                quality = 1.0E9
                runtime = self.cutoff

        except TimeoutExpired as e:
            self.vprint('[Wrapper Err] Timeout')
            io.terminate()
            status = "TIMEOUT"
            runtime = self.cutoff
            quality = 1.0E9
        finally:
            try:
                os.remove(pidFile)
            except:
                pass
        return status, runtime, quality

    def runMinizinc_obj_mode(self,cmd,maximize):
        t = time.time()
        cmd += ['--time-limit', str(self.cutoff * 1000)]
        self.vprint('[Wraper out]', cmd)
        io = Popen(cmd, stdout=PIPE, stderr=PIPE)

        try:
            pidFile = "pid" + str(io.pid)
            with open(pidFile, 'w') as f:
                f.write(str(io.pid))
        except:
            pass

        status = None
        quality = None
        runtime = self.cutoff

        try:
            (stdout_, stderr_) = io.communicate()
            self.vprint('[MiniZinc out] ', stdout_.decode('utf-8'))

            if re.search(b'time elapsed:', stdout_):
                status = "SUCCESS"
                runtime = float(re.search(b'(?:mzn-stat time=)((\d+\.\d+)|(\d+))', stdout_).group(1))
                quality = float(re.search(b'(?:mzn-stat objective=)((\d+\.\d+)|(\d+))', stdout_).group(1))
                self.vprint('[Wrapper] Run success')
                self.vprint('[Wrapper] run time ', str(runtime))
                self.vprint('[Wrapper] quality ', str(quality))

                if maximize:
                    quality = -quality

            elif re.search(b'=====UNKNOWN=====', stdout_):
                eprint('[MiniZinc Warn][UNKNOWN] ', stderr_.decode('utf-8'))
                status = "TIMEOUT"
                quality = 1.0E9
                runtime = self.cutoff

        except Exception as e:
            self.vprint('[Wrapper Exception] ', e)
            io.terminate()
            status = "Crashed"
            runtime = self.cutoff
            quality = 1.0E9
        finally:
            try:
                os.remove(pidFile)
            except:
                pass
        return status, runtime, quality


    def process_param(self):
        raise Exception('Must override this method')

    def generate_cmd(self, tempParam, cplex_dll=None):
        cmd = self.basicCmd + ['-p', str(self.threads)]
        cmd += ['--readParam', tempParam]
        if cplex_dll is not None:
            cmd += ['--cplex-dll', cplex_dll]
        return cmd

class CplexWrapper(Wrapper):
    def __init__(self, solver, threads):
        Wrapper.__init__(self, solver, threads)

    def process_param(self):
        # Prepare temp parameter file
        paramfile = 'CPLEX Parameter File Version 12.6\n'
        for name, value in zip(self.params[::2], self.params[1::2]):
            if name == '-MinizincThreads':
                self.threads = value
            else:
                paramfile += name.strip('-') + '\t' + value + '\n'
        tempParam = self.get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam, 'w') as f:
            f.write(paramfile)
        return tempParam

class OsicbcWrapper(Wrapper):
    def __init__(self, solver, threads):
        Wrapper.__init__(self, solver, threads)

    def process_param(self):
        # Prepare temp parameter file
        args = ''
        for name, value in zip(self.params[::2], self.params[1::2]):
            if name == '-MinizincThreads':
                self.threads = value
            else:
                args += ' ' + name + ' ' + value
        return args

class GurobiWrapper(Wrapper):
    def __init__(self, solver, threads):
        Wrapper.__init__(self, solver, threads)

    def process_param(self):
        # Prepare temp parameter file
        paramfile = '# Parameter Setting for Gruobi\n'
        for name, value in zip(self.params[::2], self.params[1::2]):
            if name == '-MinizincThreads':
                self.threads = value
            else:
                paramfile += name.strip('-') + '\t' + value + '\n'
        tempParam = self.get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam, 'w') as f:
            f.write(paramfile)
        return tempParam



if __name__=="__main__":
    try:
        with open('wrapperSetting.json') as file:
            jsonData = json.load(file)

        solver = jsonData['solver']
        threads = jsonData['threads']
        dll = jsonData['cplex_dll']
        maximize = jsonData['maximize']
        obj_mode = jsonData['obj_mode']
        obj_bound = jsonData['obj_bond']
        verbose = jsonData['verbose']

        if solver == 'cplex':
            wrapper = CplexWrapper(solver, threads,verbose)
        elif solver == 'osicbc':
            wrapper = OsicbcWrapper(solver, threads,verbose)
        elif solver == 'gurobi':
            wrapper = GurobiWrapper(solver, threads,verbose)
        else:
            raise Exception('[Wrapper Error] Solver do not exist')
        wrapper.vprint('[Wrapper Debug] Read Wrapper setting',jsonData)
        tempParam = wrapper.process_param()
        cmd = wrapper.generate_cmd(tempParam,dll)

        if obj_mode:
            status, runtime, quality = wrapper.runMinizinc_obj_mode(cmd, maximize)
        elif obj_bound is not None:
            status, runtime, quality = wrapper.runMinizinc_obj_cut(cmd, maximize, obj_bound)
        else:
            status, runtime, quality = wrapper.runMinizinc_time(cmd, maximize)

        try:
            os.remove(tempParam)
        except:
            pass
        wrapper.vprint('[Wrapper Debug] Run Finish ',status,' ', runtime,' ', quality)
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, wrapper.runlength, quality, wrapper.seed,
                                                                            wrapper.specifics))

    except FileNotFoundError as e:
        eprint('[Wrapper Error] Failed when loading wrapperSetting', e)
        status = "CRASHED"
        runtime = 99999
        quality = 1.0E9
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, 0, 0))
    except Exception as e:
        eprint('[Wrapper Error]',e)
        status = "CRASHED"
        runtime = 99999
        quality = 1.0E9
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, 0, 0))



