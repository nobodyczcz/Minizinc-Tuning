import sys
import time
import os, shutil, argparse


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs,flush=True)


def pprint(*args, **kwargs):
    print(*args, **kwargs, flush=True)


def get_current_timestamp():
    '''
    Get current timestamp
    '''
    return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))


def printPorgress(timeLimit):
    t = time.time()
    while (time.time() - t) < timeLimit:
        pprint("%%%mzn-progress", str(round((time.time() - t) / timeLimit, 2)))
        time.sleep(5)

def environmentCheck(args):
    envdic = {}
    osenv = os.environ
    if shutil.which('minizinc') is None:
        raise Exception("Must Add Minizinc to Path Enviroment")
    else:
        envdic['minizinc'] = shutil.which('minizinc')

    if shutil.which('java') is None:
        raise Exception("Must install java and add it pt your PATH")
    else:
        envdic['java'] = shutil.which('java')

    if getattr(sys, 'frozen', False):
        # we are running in a bundle
        pass
    else:
        # we are running in a normal Python environment
        if sys.version_info[0] < 3:
            raise Exception("Must be using Python 3")
        else:
            envdic['python'] = sys.executable

    if args.solver == 'gurobi':
        try:
            envdic['GUROBI_HOME'] = osenv['GUROBI_HOME']
        except:
            raise Exception('Gurobi must be installed and add to PATH environment')

    elif args.solver == 'cplex':
        if 'cplex' not in os.environ['PATH']:
            raise Exception('You must install cplex.')
    envdic['osenv'] = osenv.copy()
    return envdic


def argparser():
    '''
    Initialize the parser and define the description information that will be displayed in help.
    :return: parser.parse_args()
    '''

    parser = argparse.ArgumentParser(prog='Parameter tunning tool', \
                                     formatter_class=argparse.RawTextHelpFormatter, \
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

    # Define arguments and their help information
    parser.add_argument('--solver', '--tuning-solver', choices=['osicbc', 'cplex', 'gurobi'], required=True,
                        metavar='osicbc/cplex', \
                        help='''\
    You can choose osicbc or cplex as solver. 
    If you choose cplex you need to specify the dll file of 
    cplex after --cplex-dll argument.
                        ''')

    parser.add_argument('instances', nargs='*', type=str, default=None, \
                        metavar='"model-name.mzn data1.dzn data2.dzn"', \
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

    parser.add_argument('-i', '--instances-file', default=None, metavar='your-instances-list-file-name', \
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

    parser.add_argument('--pcs-json', '--pcs-json-file', default=None, metavar='your-pcsJson-file-name', \
                        help='''\
    Specify the path of parameter configuratoin json file.
                        ''')

    parser.add_argument('-p', type=int, default=1, metavar='number-of-threads', \
                        help='''\
    Specify the number of threads when minizinc solve the model.

    It is suggested to use less threads, so that you can use Psmac 
    for parallel search. 
    Parallel search can significantly improve the efficiency for 
    finding a good parameter configuration.
                        ''')

    parser.add_argument('--psmac', type=int, default=1, metavar='number-of-threads', \
                        help='''\
    Enable parallel search and specify how many smac runing at same time.
    Warning: total threads use (number of threads for minizinc x number of smac)
    should be smaller than total aviable threads of your cpu.
                        ''')

    parser.add_argument('-c', '--cut', type=float, default=0, metavar='cut-off-time-by-seconds', \
                        help='''\
    Specify a cut off time for minizinc solve the problem. It is suggested 
    to use a time that can make most runs pass it. If you don't specify a
    cut off time, the program will test these instances and choose a suitable
    time.
                        ''')

    parser.add_argument('-t', '--time-limit', '--tuning-time', type=int, default=None, metavar='time-limit-by-seconds', \
                        help='''\
    You must specify a time limit for tunning. You can read the help for
    -pcs to see our suggestion for time limit.
                        ''')
    parser.add_argument('--tuning-runs', type=int, default=None, metavar='amount of runs', \
                        help='''\
    You can specify how many runs you want smac to perform, instead of tuning time limit.
                            ''')

    parser.add_argument('--dll', '--cplex-dll', default=None, type=str, metavar='/opt/ibm/....', \
                        help='''\
    You need to give the path of cplex  dll file if you want to use cplex
    as solve.
                        ''')

    parser.add_argument('-v', default=False, action='store_true', \
                        help='''\
    Display more information for debugging.
                        ''')
    parser.add_argument('--bench-mode', type=str, metavar='5:-1', \
                        default=None, help='''\
    Benchmark mode. Specify for every configuration, how many times it will be runed
    for average time. Default is 5 times. Also specify for every output file, how many
    last configuration will be test. Default is last 1. Format 'times:last'. last must 
    smaller than 0.
                        ''')
    parser.add_argument('--skip-bench', default=False, action='store_true' \
                        , help='''\
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
    With this argument, the program will try to optimize objective within limited time. You must specify
    a cut off time when using this mode. 
                            ''')
    parser.add_argument('--maximize', default=False, action='store_true' \
                        , help=''''\
    Let the program know that these model are maximize problems.
                                ''')

    parser.add_argument('--obj-cut', type=int, default=None \
                        , help=''''\
    Terminate minizinc when reach a certain bound.
                                ''')

    parser.add_argument('--minizinc', action='store_true', default=False \
                        , help=''''\
    Let program known that program is called by minizinc.
                                    ''')

    parser.add_argument('--minizinc-exe', type=str, default='minizinc' \
                        , help=''''\
    Let program known where is minizinc -executable.
                                        ''')

    parser.add_argument('--more-runs', default=False, action='store_true' \
                        , help=''''\
    To reduce the influence of random effect. SMAC will run every configuration for
    multiple times to evaluate performance.
                                            ''')

    parser.add_argument('--user-gurobi-tune-tool', default=False, action='store_true' \
                        , help=''''\
    Use gurobi's own parameter tuning tool. Currently, do not support multiple instance 
    tuning.
                                                ''')
    parser.add_argument('--tuning-tool', choices=['smac', 'grbtune'], default='smac',
                        metavar='smac/grbtune', \
                        help='''\
    specify using smac or using gurobi tuning tool to perform tuning. grbtune only support gurobi solver. 
                            ''')
    parser.add_argument('--restore', default=None,
                        metavar='path/to/history/run', \
                        help='''\
    Restore previous run. You can stop tuning, and continue tuning later with this command.
                                                        ''')
    parser.add_argument('--no-clean', default=False,
                        action='store_true', \
                        help='''\
    Do not clean cache folder.
                                                            ''')
    parser.add_argument('--output-dir', default=None,
                        type=str, \
                        help='''\
    specify the output directory.
                                                                ''')
    parser.add_argument('--output-file', default=None,
                        type=str, \
                        help='''\
    specify the output file and path.
                                                                    ''')
    parser.add_argument('--no-stop-first-crash', default=False,
                        action='store_true',\
                        help='''\
        do not stop tuning on first run crash
                                                                        ''')

    # args = parser.parse_args() #parse arguments
    args, unknownargs = parser.parse_known_args()
    # print(args)
    return args, unknownargs


def printStartMessage(args):
    print("*" * 50)
    print("Minizinc Executable: ", args.minizinc_exe)
    eprint("Solver: ", args.solver)
    eprint("threads: ", args.p)
    eprint("Tune threads: ", args.tune_threads)
    eprint("PSMAC mode: ", args.psmac)
    eprint("Optimize objective mode: ", args.obj_mode)
    if args.obj_mode:
        eprint("Maximization problem: ", args.maximize)
    eprint("Cuts time: ", args.cut)
    eprint("Tuning time limit: ", args.time_limit)
    eprint("Parameter space file: ", args.pcs_json)
    eprint("cplex dll: ", args.dll)
    eprint("Verbose: ", args.v)
    eprint("Skip Benchmark", args.skip_bench)
    eprint("*" * 50)