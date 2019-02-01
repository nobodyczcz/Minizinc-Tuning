#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 16:05:40 2018

@author: czcz2
"""

import argparse,signal, inspect, shutil
from pcsConverter import *
from initializer import *
from tunning import *

def argparser():
    '''
    Initialize the parser and define the description information that will be displayed in help.
    :return: parser.parse_args()
    '''

    parser = argparse.ArgumentParser(prog='Parameter tunning tool',\
                                     formatter_class=argparse.RawTextHelpFormatter,\
                                     description='''\
    This program performs automactic parameter tunning with SMAC3.
    To use this program you need to provide:
     1. Model and data files, you can provide several model, each with 
        several data.
        You can provide them by a instances list text file, or write them
        directly in the aguments.
        Please follow the format described in help for -instances-file.
     2. Solver name. Currently support cplex and osicbc.
     3. Time limit for tunning. Please read the help for -t to choose a 
        suitable time limit. You also can specify a cut off time for minizinc
        solve the model. If you don't specify cut off time, the program will 
        decide it.
     4. The parameter configuration file in json format. We provide several 
        parameter configuration file uder pcsFile/ directory. You can choose
        one. You also edit them by yourself.
     5. Number of threads for minizinc solve the model. 
     6. The dll file for cplex, if you choose cplex as solver.
     7. If you want to tune faster and your conputer have enough cpus. You can
        use -psmac for parallel search (smacs will share their results in this 
        mode.) 
                                 ''')

    
    #Define arguments and their help information
    parser.add_argument('--solver',choices=['osicbc','cplex','gurobi'],required=True,metavar='osicbc/cplex',\
                        help='''\
    You can choose osicbc or cplex as solver. 
    If you choose cplex you need to specify the dll file of 
    cplex after --cplex-dll argument.
                        ''')
    
    parser.add_argument('instances', nargs='*', type=str, default= None,\
                        metavar='"model-name.mzn data1.dzn data2.dzn"',\
                        help='''\
    ***Be aware of the quote in example!
    You can provide instaces by arguments in following format:
        
    "Model1.mzn data1.dzn data2.dzn" "Model2.mzn data21.dzn"
    "Model3.mzn data31.dzn data32.dzn data33.dzn ..." .... 
    
    Or you can provide them by given an instances list file 
    after --instances-file, if you specify one list file,
    the program will ignore the models and datas listed by 
    arguments.
    
    Hint: It is suggested to use one model with different 
    data file for multiple instances tunning. 
    It is not suggested to use multiple models, especially 
    models with big differences. Because different models may 
    require different configuration, it is hard to find one 
    good solution for all different models.
                        ''')
    
    parser.add_argument('-i','--instances-file',default= None ,metavar='your-instances-list-file-name',\
                        help='''\
    Specify the instances list file, the file shold be written 
    like this:
        
        Model1.mzn data1.dzn data2.dzn
        Model2.mzn data21.dzn
        Model3.mzn data31.dzn data32.dzn data33.dzn
        ......
    If you specify this file, the program will ignore the instances
    given by command-line arguments. 
                        ''')
    
    parser.add_argument('-pcsJson','--pcsJson-file',required=True, default= None ,metavar='your-pcsJson-file-name',\
                        help='''\
    Specify the path of parameter configuratoin json file.
                        ''')
    
    parser.add_argument('-p',type=int,default=1,metavar='number-of-threads',\
                        help='''\
    Specify the number of threads when minizinc solve the model.

    It is suggested to use less threads, so that you can use Psmac 
    for parallel search. 
    Parallel search can significantly improve the efficiency for 
    finding a good parameter configuration.
                        ''')

    parser.add_argument('-psmac',type=int,default=1,metavar='number-of-threads',\
                        help='''\
    Enable parallel search and specify how many smac runing at same time.
    Warning: total threads use (number of threads for minizinc x number of smac)
    should be smaller than total aviable threads of your cpu.
                        ''')
    
    parser.add_argument('-c','--cut',type=int,default=0,metavar='cut-off-time-by-seconds',\
                        help='''\
    Specify a cut off time for minizinc solve the problem. It is suggested 
    to use a time that can make most runs pass it. If you don't specify a
    cut off time, the program will test these instances and choose a suitable
    time.
                        ''')
    
    parser.add_argument('-t','-time-limit',type=int,required=True,metavar='time-limit-by-seconds',\
                        help='''\
    You must specify a time limit for tunning. You can read the help for
    -pcs to see our suggestion for time limit.
                        ''')
    
    parser.add_argument('--cplex-dll',default=None,type=str,metavar='/opt/ibm/....',\
                        help='''\
    You need to give the path of cplex  dll file if you want to use cplex
    as solve.
                        ''')
    
    parser.add_argument('-v',default=False,action='store_true',\
                        help='''\
    Display more information for debugging.
                        ''')
    parser.add_argument('--bench-mode',type=str, metavar='5:-1',\
                        default=None,help='''\
    Benchmark mode. Specify for every configuration, how many times it will be runed
    for average time. Default is 5 times. Also specify for every output file, how many
    last configuration will be test. Default is last 1. Format 'times:last'. last must 
    smaller than 0.
                        ''')
    parser.add_argument('--skip-bench',default = False, action='store_true'\
                        ,help='''\
    Some times bench mark may take a very long time. If you don't want spend time on it,
    just skip it. System will output the best configuration reported by SMAC. No value needed,
    skip bench when this option exist.
                        ''')

    parser.add_argument('--tune-threads', default=False, action='store_true' \
                        , help=''''\
    With this argument, the program will treat threads as a parameter for tuning. -p will be treat
    as the maximum available threads for minizinc.  
                            ''')
    parser.add_argument('--obj-mode', default=False, action='store_true' \
                    , help=''''\
    With this argument, the program will try to optimize objective within limited time. 
                            ''')
    parser.add_argument('--maximize', default=False, action='store_true' \
                        , help=''''\
        define the model is a maximize problem.
                                ''')

    parser.add_argument('--obj-cut', type=int, default=None \
                        , help=''''\
        Terminate minizinc when reach a certain bound.
                                ''')

    args = parser.parse_args() #parse arguments
    
    #print(args)
    return args
    
def main():
    """
    This is then main framework for tunning program. The main defines arguments format,
    validates the arguments format given, and control the whole process of the tunning program.

    Args and value explaination:
        args.solver
                        string, the name of solver
        args.cplex_dll
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
    args = argparser()

    #check does user provide cplex-dll when using cplex
    # if args.solver == "cplex":
    #     if args.cplex_dll == None:
    #         raise Exception('You must specify the path of cplex dll file when using cplex.')
    
    '''
    Parameter file pre check.
    Convert json pcs file to Smac pcs file format
    '''
    converter = pcsConverter()
    initialCwd = os.getcwd()
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    programPath = os.path.dirname(os.path.abspath(filename))
    if args.tune_threads:
        pcsFile = converter.jsonToPcs(args.pcsJson_file, sys.path[0] + "/cache/temppcs.pcs", args.p)
    else:
        pcsFile = converter.jsonToPcs(args.pcsJson_file, sys.path[0] + "/cache/temppcs.pcs")

    
    '''
    Instances pre check
    '''
    if args.instances_file is not None:
        print("Read instances list file: ",args.instances_file)
    else:
        if args.instances is None:
            raise Exception('You need either specify a instances list file or give instances by commandline arguments. Use -h for help')
        else:
            print("Instances from arguments: " ,' '.join(args.instances))
    
    '''
    Benchmark mode setting check
    '''
    if args.obj_cut is not None:
        args.skip_bench = True
    if args.bench_mode is not None:
        try:
            benchMode = args.bench_mode.split(':')
            times = int(benchMode[0])
            last = int(benchMode[1])
            if last >= 0:
                raise Exception('[Benchmark Mode Error] last must smaller than 0')
        except Exception as e:
            raise Exception('[Benchmark Mode Error] please read -h for help')


    print("=" * 50)
    print("threads: ", args.p)
    print("Tune threads: ", args.tune_threads)
    print("solver: ",args.solver)
    print("PSMAC mode: ","result from last step")
    print("Cuts time: ", args.cut)
    print("Tuning time limit: ", args.t)
    print("Parameter space file: ", pcsFile)
    print("cplex dll: ", args.cplex_dll)
    print("verbose: ", args.v)
    print("=" * 50)

    '''
    Tunning initialization
    In this step the program will generate related temperary files
    '''
    if args.solver == "osicbc":
        initializer = CbcInitial(args.cut, args.t, args.v, pcsFile, args.p, args.instances_file, args.instances,
                                 args.cplex_dll, programPath, args.psmac, initialCwd, args.obj_mode)
    elif args.solver == "cplex":
        initializer = CplexInitial(args.cut, args.t, args.v, pcsFile, args.p, args.instances_file, args.instances,
                                   args.cplex_dll, programPath, args.psmac, initialCwd, args.obj_mode)
    elif args.solver == "gurobi":
        initializer = GurobiInitial(args.cut, args.t, args.v, pcsFile, args.p, args.instances_file, args.instances,
                                    args.cplex_dll, programPath, args.psmac, initialCwd, args.obj_mode)
    else:
        raise Exception("Do not support solver: ", args.solver)

    try:
        # combine instances fils and generate relating temp files
        initializer.process_instance()

        # check threads settings
        initializer.process_thread()

        # change working directory to /cache
        os.chdir(sys.path[0]+"/cache") 
        
        # Calculate cut off time if use didn't specify
        initializer.cut_off_time_calculation(args.obj_cut,args.maximize)

        # generate wrapper and smac scenario
        initializer.pSMAC_wrapper_generator(args.solver,args.maximize,args.obj_cut)
        initializer.pSMAC_scenario_generator(args.solver)
        tempOut = open('temp.txt','w')
        tempOut.write('')
        tempOut.close()

        '''
        Start Tunning
        '''
        if os.name == 'nt':
            smacPath = os.path.abspath("../smac-v2/smac.bat")
        else:
            smacPath = os.path.abspath("../smac-v2/smac")
        print("smac path: ",smacPath)
        tunning = Tunning(args.v,args.psmac,initializer.outputdir,smacPath)

        tunning.runSmac()

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt has been caught.")

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
                            print('[Exception] ', e)
            except:
                pass
        '''
        Benchmark and output result to file
        '''
        try:
            if args.skip_bench or args.obj_mode:
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
                    print('[Benchmark Mode Error] ', e)
        except KeyboardInterrupt:
            pass
        print("\nCleaning up...")
        initializer.remove_tmp_files()

def enviromentCheck():
    minizinc = shutil.which('minizinc')
    python3 = shutil.which('python3')

if __name__=="__main__":
    main()


