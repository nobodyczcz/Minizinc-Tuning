from run_minizinc.runtool import *
from helpFunctions.helpFuctions import *
'''
This file store the wrapper of solvers which will be directly called by SMAC.
'''

if __name__=="__main__":
    try:
        '''
        Try to read wrapper setting file.
        '''
        with open('wrapperSetting.json','r') as file:
            jsonData = json.load(file)

        solver = jsonData['solver']
        threads = jsonData['threads']
        dll = jsonData['dll']
        maximize = jsonData['maximize']
        obj_mode = jsonData['obj_mode']
        obj_bound = jsonData['obj_bond']
        verbose = jsonData['verbose']
        envdic = jsonData['envdic']
        minizinc_exe = jsonData['minizinc_exe']

        osenv = envdic['osenv']

        instance = sys.argv[1]
        specifics = sys.argv[2]
        cutoff = int(float(sys.argv[3]) + 1)  # runsolver only rounds down to integer
        runlength = int(sys.argv[4])
        seed = None if int(sys.argv[5]) == -1 else int(sys.argv[5])
        params = sys.argv[6:]


        '''
        Create wrapper, generate parameters and generate commands.
        '''
        if solver == 'cplex':
            wrapper = CplexWrapper(solver, threads,verbose,minizinc_exe,cutoff)
        elif solver == 'osicbc':
            wrapper = OsicbcWrapper(solver, threads,verbose,minizinc_exe,cutoff)
        elif solver == 'gurobi':
            wrapper = GurobiWrapper(solver, threads,verbose,minizinc_exe,cutoff)
        else:
            raise Exception('[Wrapper Error] Solver do not exist')
        wrapper.vprint('[Wrapper Debug] Read Wrapper setting',jsonData)
        tempParam = wrapper.process_param(params,randomSeed=seed)
        instancelist = wrapper.seperateInstance(instance)
        cmd = wrapper.generate_cmd(tempParam,solver,instancelist,dll)

        '''
        Run minizinc in suitable mode.
        '''
        if obj_mode:
            wrapper.vprint('Run in obj mode')
            status, runtime, quality = wrapper.runMinizinc_obj_mode(cmd, maximize, env = osenv)
        elif obj_bound is not None:
            wrapper.vprint('Run in obj cut mode')
            status, runtime, quality = wrapper.runMinizinc_obj_cut(cmd, maximize, obj_bound, env = osenv)
        else:
            wrapper.vprint('Run in time mode')
            status, runtime, quality = wrapper.runMinizinc_time(cmd, env = osenv)

        '''
        Clean temp parameter file and output results.
        '''
        try:
            os.remove(tempParam)
        except:
            pass
        wrapper.vprint('[Wrapper Debug] Run Finish ',status,' ', runtime,' ', quality)
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, runlength, quality, int(sys.argv[5]),
                                                                            specifics))

    except FileNotFoundError as e:
        eprint('[Wrapper Error] Failed when loading wrapperSetting', e)
        status = "CRASHED"
        runtime = 99999
        quality = ""
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, sys.argv[5], 0))
    except Exception as e:
        eprint('[Wrapper Error]',e)
        status = "CRASHED"
        runtime = 99999
        quality = ""
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, sys.argv[5], 0))
    except KeyboardInterrupt:
        eprint('KeyboardInterrupt caught')



