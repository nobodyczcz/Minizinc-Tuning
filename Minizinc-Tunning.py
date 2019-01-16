# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 16:05:40 2018

@author: czcz2
"""

import sys, re, os ,argparse
from pcsConverter import *
import psutil
from subprocess import Popen
from initializer import *
from tunning import *

def argparser():
        #Initialize the parser and define the description information that will be displayed in help.
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
     4. The size of parameter spaces you want to tunning. Please read help 
        for -p to choose a suitable pcs size. 
     5. Number of threads for minizinc solve the model. The number of 
        threads for minizinc also will decide how smac perform parallel search.
        See help for -p for details
     6. The dll file for cplex, if you choose cplex as solver.
                                 ''')

    
    #Define arguments and their help information
    parser.add_argument('--solver',choices=['osicbc','cplex'],required=True,metavar='osicbc/cplex',\
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
    
    parser.add_argument('--cplex-dll',type=str,metavar='/opt/ibm/....',\
                        help='''\
    You need to give the path of cplex  dll file if you want to use cplex
    as solve.
                        ''')
    
    parser.add_argument('-v',default=False,action='store_true',\
                        help='''\
    Display more information for debugging.
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
                        string, file name of pcs file
    """
    
    '''
    Parse arguments
    '''
    args = argparser()

    #solver check
    if args.solver == "cplex":
        if args.cplex_dll == None:
            raise Exception('You must specify the path of cplex dll file when using cplex.')
    
    '''
    Parameter file pre check
    '''
    converter = pcsConverter()
    initialCwd = os.getcwd()
    print(sys.path[0])
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    programPath = os.path.dirname(os.path.abspath(filename))
    pcsFile = converter.jsonToPcs(args.pcsJson_file,sys.path[0]+"/cache/temppcs.pcs")
    print(pcsFile)
    
    '''
    Instances pre check
    '''
    if args.instances_file != None:
        print("Read instances list file: ",args.instances_file)

    else:
        if args.instances == None:
            raise Exception('You need either specify a instances list file or give instances by commandline arguments. Use -h for help')
            
        else:
            print("Instances from arguments: ",' '.join(args.instances))

    print("=" * 50)
    print("threads: ", args.p)
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

    try:
        if args.solver == "osicbc" :
            initializer = cbcInitial(args.cut, args.t, args.v, pcsFile, args.p, args.instances_file, args.instances, args.cplex_dll,programPath,args.psmac,initialCwd)
        elif args.solver == "cplex":
            initializer = cplexInitial(args.cut, args.t, args.v, pcsFile, args.p, args.instances_file, args.instances, args.cplex_dll,programPath,args.psmac,initialCwd)
        else:
            raise Exception("Do not support solver: ",args.solver)
        
        #combine instances fils and generate relating temp files
        initializer.process_instance()

        #check threads settings
        initializer.process_thread()

        #change working directory to /cache
        os.chdir(sys.path[0]+"/cache") 
        
        #Calculate cut off time if use didn't specify
        initializer.cut_off_time_calculation()

        #generate wrapper and smac scenario
        initializer.pSMAC_wrapper_generator()
        initializer.pSMAC_scenario_generator()

        '''
        Start Tunning
        '''
        smacPath = "../smac-v2/smac"
        print("smac path: ",smacPath)
        if args.solver == "osicbc" :
            tunning = CbcTunning(args.v,args.psmac,initializer.outputdir,smacPath)
        elif args.solver == "cplex":
            tunning = CplexTunning(args.v,args.psmac,initializer.outputdir,smacPath)

        tunning.runSmac()

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt has been caught.")
        for process in psutil.process_iter():      
            if set(['java', '-Xmx1024m', '-cp']).issubset(set(process.cmdline())):
                print(' '.join(process.cmdline()))
                print('Process found. Terminating it.')
                process.terminate()
    finally:
        try:
            initializer.benchmark_main(10)
        except KeyboardInterrupt:
            pass
        print("\nCleaning up...")
        initializer.remove_tmp_files()


    # '''
    # Handle tunning result and output
    # '''
    #call handle function
    
if __name__=="__main__":
    main()


