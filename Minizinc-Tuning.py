#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 16:05:40 2018

@author: czcz2
"""

import signal
from pcsConverter import *
from initializer import *
from tunning import *
from helpFunctions.helpFuctions import *





def main():
    """
    This is then main framework for tunning program. The main defines arguments format,
    validates the arguments format given, and control the whole process of the tunning program.

    Args and value explaination:
        args.solver
                        string, the name of solver
        args.dll
                        string, the path of
        args.cut
                        int, cut off time by seconds
        args.instances
                        list, list of instaces
        args.instances-file
                        string, name of instance list file
        args.pcsJson-file
                        string, path of pcsJson-file
        args.p
                        int, number of threads for minizinc
        args.psmac
                        int, number of smac running for paralell smac
        args.pcs
                        string, size of parameter spaces
        args.t
                        int, tunning time limit by seconds
        args.v
                        boolean, -v True or False
        pcsFile
                        string, file name of pcs fil
    :return: None
    """
    
    '''
    Parse arguments
    '''
    args, unknownargs = argparser()


    '''
    Enviroment pre check
    '''
    envdic = environmentCheck(args)
    
    if args.tuning_tool == 'grbtune':
        args.skip_bench = True
        args.psmac = 1
        args.tune_threads = False
        if args.solver != 'gurobi':
            raise Exception('Must use gurobi as solver when using gurobi tuning tool')

    if args.time_limit is None and args.tuning_runs is None:
        raise Exception('You must specify either --time-limit or --tuning-runs')

    '''
    Parameter file pre check.
    Convert json pcs file to Smac pcs file format
    '''
    converter = pcsConverter()
    initialCwd = os.getcwd()

    if getattr(sys, 'frozen', False):
        # we are running in a bundle
        programPath = sys._MEIPASS
    else:
        # we are running in a normal Python environment
        programPath = os.path.dirname(os.path.abspath(__file__))

    if args.pcs_json is None:
        try:
            args.pcs_json = os.path.abspath(programPath+'/pcsFiles/' + args.solver + '.json')
        except:
            eprint('[Minizinc-Tuning error]Cannot find parameter configuration json file for ' + args.solver +\
                            ' under Minizinc-Tuning/pcsFiles/ . Please specify one with -pcsJson argument')
            raise
    if not os.path.exists(programPath+'/cache'):
        os.mkdir(programPath+'/cache')
    pcsFile = converter.jsonToPcs(args.pcs_json, programPath + "/cache/temppcs.pcs", args.p if args.tune_threads else None)

    
    '''
    Instances pre check
    '''
    if len(unknownargs) > 0:
        args.instances += unknownargs
        eprint(args.instances)

    if args.instances_file is not None:
        eprint("Read instances list file: ",args.instances_file)
    else:
        if args.instances is None:
            raise Exception('You need either specify a instances list file or give instances by commandline arguments. Use -h for help')
        else:
            eprint("Instances from arguments: " ,' '.join(args.instances))
    
    '''
    Benchmark mode setting check
    '''

    if args.obj_mode:
        if args.cut == 0:
            raise Exception('[Setting error] You must specify a -c (cut off time) for objective optimizing mode')
    if args.bench_mode is not None:
        try:
            benchMode = args.bench_mode.split(':')
            times = int(benchMode[0])
            last = int(benchMode[1])
            if last >= 0:
                raise Exception('[Benchmark Mode Error] last must smaller than 0')
        except Exception as e:
            raise Exception('[Benchmark Mode Error] please read -h for help')

    '''
    Tunning initialization
    In this step the program will generate related temperary files
    '''
    printStartMessage(args)

    initializer = Initializer(args.solver,args.cut, args.v, pcsFile, args.p, args.instances_file,
                                 args.dll,initialCwd, args.minizinc_exe,args.maximize, args.obj_mode)
    stateFiles = None
    initializer.totalTuningTime=args.time_limit

    if args.restore is not None:
        restore =  os.path.abspath(args.restore)
        rungroups = os.path.basename(restore)
        outputDir = args.restore.replace(rungroups, "")
        stateFiles = glob.glob(outputDir+rungroups+"/state*")
        for i in stateFiles:
            i = os.path.normpath(i)
        eprint(get_current_timestamp(),"Find state folders: ", stateFiles)

    if args.output_file is not None:
        outputDir =  os.path.dirname(args.output_file)
        filename =os.path.basename(args.output_file)
        initializer.setOutputDir(os.path.abspath(outputDir))
        initializer.outputFile = filename

    elif args.output_dir is not None:
        initializer.setOutputDir(os.path.abspath(args.output_dir))


    # combine instances fils and generate relating temp files
    initializer.process_instance(args.instances,programPath,args.minizinc)

    # check threads settings
    initializer.thread_check(args.psmac)

    # change working directory to /cache
    os.chdir(programPath+"/cache")

    try:
        # Calculate cut off time if use didn't specify
        initializer.cut_off_time_calculation()
        if args.time_limit is None:
            if args.cut == 0:
                args.time_limit = int((initializer.cutOffTime * args.tuning_runs)//3)
            else:
                args.time_limit = int(initializer.cutOffTime * args.tuning_runs)

            if args.more_runs:
                args.time_limit = args.time_limit * 3
            eprint('{} Tuning Time Limit set as: {}. For {} runs'.format(get_current_timestamp(), args.time_limit,args.tuning_runs))

        if args.tuning_tool == 'grbtune':
            initializer.lp_model_generate(envdic['osenv'])
        else:
            # generate wrapper and smac scenario
            initializer.wrapper_setting_generator(args.solver,args.obj_cut,args.obj_mode,envdic)
            initializer.pSMAC_scenario_generator(args.obj_mode,args.time_limit,args.more_runs)

        '''
        Start Tunning
        '''

        if os.name == 'nt':
            smacPath = os.path.abspath("../smac-v2/smac.bat")
        else:
            smacPath = os.path.abspath("../smac-v2/smac")
        tunning = Tunning(args.v,args.psmac,initializer.outputdir,smacPath,initializer.rungroup,args.no_stop_first_crash)

        if args.tuning_tool == 'grbtune':
            cmd = tunning.grbtune_cmd(args.time_limit,initializer.cutOffTime,args.more_runs,args.obj_mode,initializer.lpList,args.p)
            tunning.runGrbtune(cmd, args.time_limit, env=envdic['osenv'])
        else:
            tunning.runSmac(args.time_limit, env = envdic['osenv'], restore = stateFiles)

    except KeyboardInterrupt:
        eprint("\nKeyboardInterrupt has been caught.")

    finally:
        #use following code to ensure all miniinc process are killed.
        files = glob.glob('pid*')
        for f in files:
            try:
                with open(f) as content:
                    pid = content.read()
                    if pid is None:
                        pass
                    else:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                        except Exception as e:
                            pass
            except:
                pass
        '''
        Benchmark and output result to file
        '''
        try:
            if args.skip_bench:
                if args.tuning_tool == 'grbtune':
                    initializer.grbTuneOutput()
                else:
                    initializer.noBnechOutput()

            elif args.bench_mode is None:
                if args.psmac > 1:
                    initializer.benchmark_main(5,-1) # run benchmark for last 1 configuration of each output file. Each run 5 times.
                else:
                    initializer.benchmark_main(5,-3) # run benchmark for last 3 configuration of the output file. Each run 5 times.
            else:
                try:
                    initializer.benchmark_main(times,last)
                except Exception as e:
                    eprint('[Benchmark Mode Error] ', e)
        except KeyboardInterrupt:
            pass

        if not args.no_clean:
            eprint("\nCleaning up...")
            initializer.remove_tmp_files()


if __name__=="__main__":
    eprint(get_current_timestamp()," Tunning program start.")
    main()


