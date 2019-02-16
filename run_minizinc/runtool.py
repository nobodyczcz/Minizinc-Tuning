import sys, os, re, time, json
from subprocess import Popen, PIPE, TimeoutExpired
from random import randint

'''
This file store the wrapper of solvers which will be directly called by SMAC.
'''

class Wrapper():
    '''
    This Wrapper is used for SMAC run minizinc. When SMAC create a configuration, it will try to run minizinc through
    this wrapper
    '''
    def __init__(self, solver, threads, verbose,minizinc_exe='minizinc',cutoff=None):
        self.cutoff = cutoff
        self.time_limit = 0
        self.solver = solver
        self.threads = threads
        self.minizinc_exe = minizinc_exe
        self.basicCmd = [minizinc_exe, '--output-mode', 'json', '--output-objective', '--solver', solver]
        self.verbose = verbose

    def vprint(self,*args, **kwargs):
        '''
        Print to stderr when -v (verbose mode) is on.
        :param args: anything
        :param kwargs: anything
        :return: None
        '''
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

    def runMinizinc_obj_cut(self,cmd,maximize,obj_bound=None,env = None):
        """
        The function will execute the command line, shut down the program when meet certain objective and return running result.
        :param cmd: the command line will be executed
        :param cutoff: cut off time of each run
        :return: status, runtime, quality
        """
        t = time.time()

        cmd += ['--time-limit', str(self.cutoff*1000), '-a']
        self.vprint('[Wraper out]', cmd)
        io = Popen(cmd, stdout=PIPE, stderr=PIPE, env = env)

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

    def runMinizinc_time(self,cmd,env = None):
        t = time.time()
        self.vprint('[Wraper out]', cmd)

        io = Popen(cmd, stdout=PIPE, stderr=PIPE, env = env)

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
            runtime = time.time() - t
            output = stdout_.decode('utf-8')
            # self.vprint('[MiniZinc out] ', output)
            self.vprint('[Wrapper out] Minizinc Finish')
            if re.search('==========', output):
                status = "SUCCESS"
                for result in self.extract_json_objects(output):
                    try:
                        quality = result['_objective']
                        self.vprint('[Minizinc Out] Find objective=', str(quality))
                    except:
                        pass

            else:
                self.vprint('[MiniZinc Warn][Not Satisfy][stdout]', output)
                self.vprint('[MiniZinc Warn][Not Satisfy][stderr]', stderr_.decode('utf-8'))

                if runtime < self.cutoff:
                    status = 'CRASHED'
                else:
                    status = "TIMEOUT"
                quality = 1.0E9
                runtime = self.cutoff

        except TimeoutExpired as e:
            self.vprint('[Wrapper Err] Timeout')
            io.terminate()
            status = 'TIMEOUT'
            runtime = self.cutoff
            quality = 1.0E9
        finally:
            try:
                os.remove(pidFile)
            except:
                pass
        return status, runtime, quality

    def runMinizinc_obj_mode(self,cmd,maximize=False, env = None):
        t = time.time()
        cmd += ['--time-limit', str(self.cutoff * 1000)]
        self.vprint('[Wraper out]', cmd)
        io = Popen(cmd, stdout=PIPE, stderr=PIPE,env = env)

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
            (stdout_, stderr_) = io.communicate(timeout=self.cutoff*2)
            runtime = time.time()-t
            output = stdout_.decode('utf-8')
            #self.vprint('[MiniZinc out] ', output)
            self.vprint('[Wrapper out] Minizinc Finish')


            for result in self.extract_json_objects(output):
                try:
                    quality = result['_objective']
                    self.vprint('[Minizinc Out] Find objective=', str(quality))
                except:
                    pass


            if quality is not None:
                status = "SUCCESS"
                if maximize:
                    quality = -quality
            else:
                self.vprint('[MiniZinc Warn][Not Satisfy][stdout]', output)
                self.vprint('[MiniZinc Warn][Not Satisfy][stderr]', stderr_.decode('utf-8'))
                if runtime < self.cutoff:
                    status = 'CRASHED'
                else:
                    status = "TIMEOUT"
                quality = 1.0E9
                runtime = self.cutoff

        except TimeoutExpired as e:
            io.terminate()
            self.vprint('[Wrapper Exception] ', 'Minizinc did not stop on timelimit, killed by wrapper')
            status = "Crashed"
            runtime = self.cutoff
            quality = 1.0E9

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

    def output_lp(self,cmd,timelimit,env=None):
        cmd += ['--solver-time-limit', str(timelimit * 1000)]
        io = Popen(cmd, stdout=PIPE, stderr=PIPE, env=env)
        io.communicate()




    def process_param(self,params,outputdir = None):
        raise Exception('Must override this method')

    def generate_cmd(self, tempParam,solver,instance,dll=None):
        cmd = self.basicCmd + ['-p', str(self.threads)] + instance

        if tempParam is not None:
            cmd += ['--readParam', tempParam]

        if dll is not None:
            cmd += ['--'+solver+'-dll', dll]
        return cmd

class CplexWrapper(Wrapper):
    def __init__(self, solver, threads,verbose,minizinc_exe='minizinc',cutoff=None):
        Wrapper.__init__(self, solver, threads,verbose,minizinc_exe,cutoff)

    def process_param(self,params,outputdir = None):
        # Prepare temp parameter file
        paramfile = 'CPLEX Parameter File Version 12.6\n'
        for name, value in zip(params[::2], params[1::2]):
            if name == '-MinizincThreads':
                self.threads = value
            else:
                paramfile += name.strip('-') + '\t' + value + '\n'
        if outputdir is not None:
            tempParam = outputdir+"cplex_cfg"
        else:
            tempParam = self.get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam, 'w') as f:
            f.write(paramfile)
        return tempParam

class OsicbcWrapper(Wrapper):
    def __init__(self, solver, threads,verbose,minizinc_exe='minizinc',cutoff=None):
        Wrapper.__init__(self, solver, threads,verbose,minizinc_exe,cutoff)

    def process_param(self,params,outputdir = None):
        # Prepare temp parameter file
        args = ''
        for name, value in zip(params[::2], params[1::2]):
            if name == '-MinizincThreads':
                self.threads = value
            else:
                args += ' ' + name + ' ' + value
        if outputdir is not None:
            with open(outputdir+'cbc_cfg','w') as f:
                f.write(args)
        return args

class GurobiWrapper(Wrapper):
    def __init__(self, solver, threads,verbose,minizinc_exe='minizinc',cutoff=None):
        Wrapper.__init__(self, solver, threads,verbose,minizinc_exe,cutoff)

    def process_param(self,params, outputdir = None):
        # Prepare temp parameter file
        paramfile = '# Parameter Setting for Gruobi\n'
        for name, value in zip(params[::2], params[1::2]):
            if name == '-MinizincThreads':
                self.threads = value
            else:
                paramfile += name.strip('-') + '\t' + value + '\n'
        if outputdir is not None:
            tempParam = outputdir+"gurobi_cfg"
        else:
            tempParam = self.get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam, 'w') as f:
            f.write(paramfile)
        return tempParam




