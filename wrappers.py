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
        self.basicCmd = ['minizinc', '--output-mode', 'json', '--output-objective', '--solver', solver] + self.instance
        self.verbose = verbose

    def vprint(self,*args, **kwargs):
        if self.verbose:
            print('[Wrapper Debug]',*args, file=sys.stderr, **kwargs)

    def extract_json_objects(self,text, decoder=json.JSONDecoder()):
        """Find JSON objects in text, and yield the decoded JSON data

        Does not attempt to look for JSON arrays, text, or other JSON types outside
        of a parent JSON object.

        """
        pos = 0
        while True:
            match = text.find('{', pos)
            if match == -1:
                break
            try:
                result, index = decoder.raw_decode(text[match:])
                if len(result) >= 1:
                    yield result
                pos = match + index
            except ValueError:
                pos = match + 1

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
        delims = {'----------\n'}
        term = {"=====UNSATISFIABLE=====\n", "=====UNSATorUNBOUNDED=====\n", "=====UNBOUNDED=====\n", \
                "=====UNKNOWN=====\n", "=====ERROR=====\n", "==========\n"}
        tmp=''
        try:
            for ch in iter(lambda: io.stdout.readline().decode('utf-8'), ""):
                if ch in delims:
                    for result in self.extract_json_objects(tmp):
                        try:
                            quality = result['_objective']
                            runtime = time.time()-t
                            self.vprint('[Minizinc Out] Find objective=', str(quality))
                            self.vprint('[Minizinc Out] full output', str(result))
                        except:
                            pass
                    tmp = ""
                elif ch in term:
                    self.vprint('[Minizinc Out] Complete: ', ch)
                    break
                else:
                    tmp += ch

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

            # while io.poll() is None:
            #     line = io.stdout.readline().decode('utf-8')
            #     try:
            #         quality = float(re.search('(?:%%mzn-stat objective=)((\d+\.\d+)|(\d+))', line).group(1))
            #         self.vprint('[Minizinc Out] Find mzn-stat objective=', str(quality))
            #         self.vprint('[Minizinc Out] the line', str(line))
            #
            #         runtime = time.time() - t
            #     except:
            #         pass
            #     if obj_bound is not None:
            #         if maximize and quality is not None:
            #             if quality >= obj_bound:
            #                 status = 'SUCCESS'
            #                 self.vprint('[Wrapper] Reach Obj bound:', str(quality))
            #                 break
            #         elif quality is not None:
            #             if quality <= obj_bound:
            #                 status = 'SUCCESS'
            #                 self.vprint('[Wrapper] Reach Obj bound:', str(quality))
            #                 break
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
            output = stdout_.decode('utf-8')
            self.vprint('[MiniZinc out] ', output)
            runtime = time.time() - t



            if re.search('==========', output):
                status = "SUCCESS"
                for result in self.extract_json_objects(output):
                    try:
                        quality = result['_objective']
                        self.vprint('[Minizinc Out] Find objective=', str(quality))
                        self.vprint('[Minizinc Out] full output', str(result))
                    except:
                        pass

                if maximize:
                    quality = -quality

            else:
                self.vprint('[MiniZinc Warn][Not Satisfy][stderr]', stderr_.decode('utf-8'))
                self.vprint('[MiniZinc Warn][Not Satisfy][stdout]', output)
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
            (stdout_, stderr_) = io.communicate(timeout=self.cutoff*1.5)
            output = stdout_.decode('utf-8')
            self.vprint('[MiniZinc out] ', output)


            for result in self.extract_json_objects(output):
                try:
                    quality = result['_objective']
                    self.vprint('[Minizinc Out] Find objective=', str(quality))
                    self.vprint('[Minizinc Out] full output', str(result))
                except:
                    pass


            if quality is not None:
                status = "SUCCESS"
                if maximize:
                    quality = -quality
            else:
                self.vprint('[MiniZinc Warn][Not Satisfy][stderr]', stderr_.decode('utf-8'))
                self.vprint('[MiniZinc Warn][Not Satisfy][stdout]', output)
                status = "CRASHED"
                quality = 1.0E9
                runtime = self.cutoff

        except TimeoutExpired as e:
            (stdout_, stderr_) = io.communicate()

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
    def __init__(self, solver, threads,verbose):
        Wrapper.__init__(self, solver, threads,verbose)

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
    def __init__(self, solver, threads,verbose):
        Wrapper.__init__(self, solver, threads,verbose)

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
    def __init__(self, solver, threads,verbose):
        Wrapper.__init__(self, solver, threads,verbose)

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
            wrapper.vprint('Run in obj mode')
            status, runtime, quality = wrapper.runMinizinc_obj_mode(cmd, maximize)
        elif obj_bound is not None:
            wrapper.vprint('Run in obj cut mode')
            status, runtime, quality = wrapper.runMinizinc_obj_cut(cmd, maximize, obj_bound)
        else:
            wrapper.vprint('Run in time mode')
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



