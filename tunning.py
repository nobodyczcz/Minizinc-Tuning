# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 16:05:40 2018

@author: czcz2
"""

import argparse
import sys

def eprint(*args, **kwargs):
    """
    A help funtion that print to stderr
    """
    print(*args, file=sys.stderr, **kwargs)

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
    
    parser.add_argument('-p',type=int,default=1,metavar='number-of-threads',\
                        help='''\
    Specify the number of threads when minizinc solve the model.
    This program will perform parallel search based on the the
    hardware of your computer and the number of threads for minizinc.
    For example:
        If your computer have a 8 threads CPU, and you specify 1 
        threads for minzinc, the program will run 8 SMAC to perform 
        parallel search.
        If your computer have a 8 threads CPU, and you specify 2 
        threads for minzinc, the program will run 4 SMAC to perform 
        parallel search.
        If your computer have a 8 threads CPU, and you specify 4 
        threads for minzinc, the program will run 2 SMAC to perform 
        parallel search.
    
    It is suggested to specify less threads, so that the program can
    use more SMAC for parallel search. More threads may or may not improve 
    running time, but more SMAC will definitly improve the efficiency for
    finding a good parameter configuration.
                        ''')
        
    parser.add_argument('-pcs',choices=['s','m','l'],required=True,metavar='s/m/l',\
                        help='''\
    Specify how many parameters will be used for tunning.
        s stands for 1/3 parameters.
        m stands for 1/2 parameters.
        l stands for all parameters.
    If you want to obtain a useful parameter configuration in short time,
    it is suggest to select a small parameter space.
        Eg: If the average time for solve the model (default parameters) with 
        single threads needs less than 100 seconds, you can choose s for 
        -pcs and tunning for 2 hours. It is possible to obtain 3x or more boost.
        Hint: It is also possible to discover a better configuration when 
        tunning longer than 2 hours, for example 4 hours, using s for -pcs. 
    If you want to improve performance extremely, you can use all parameters
    and tunning for more than 12 hours.
    
    Hint: The efficiency of tunning performs different on kind of problems.
    On some problems it is possible to obtain a 10x boost within one hour when
    you select l for -pcs. But sometimes you obtain a 10x boost until 10 hours.
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
    
    print(args)
    return args
    
def main():
    """
    This is then main framework for tunning program. The main defines arguments format, 
    validates the arguments format given, and control the whole process of the tunning program.  
    """
    
    '''
    Parse arguments
    '''
    args = argparser()

    '''
    Convert solver name to solver flag
    '''
    solverFlag=None
    if args.solver == "osicbc":
        solverFlag=0
    elif args.solver == "cplex":
        solverFlag=1
        if args.cplex_dll == None:
            raise Exception('You must specify the path of cplex dll file when using cplex.')
    
    '''
    Parameter file
    '''
    pcsFile = args.solver+args.pcs+".pcs"
        
    '''
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
        args.p
                        int, number of threads for minizinc
        args.pcs
                        string, size of parameter spaces
        args.t
                        int, tunning time limit by seconds
        args.v
                        boolean, -v True or False
        solverFlag
                        0: osicbc, 1:cplex
        pcsFile
                        string, file name of pcs file
    '''
    
    '''
    Process instances
    '''
    if args.instances_file != None:
        print("Read instances list file: ",args.instances_file)
        #call instances-process(instanceFile=args.instances_list)
    else:
        if args.instances == []:
            raise Exception('You need either specify a instances list file or give instances by commandline arguments. Use -h for help')
        print("Instances from arguments: ",args.instances)
        #call instances-process(instancesList=args.instances)
    
    '''
    Threads and parellel SMAC
    '''
    print("threads:", args.p)
    #result = decide-PSMAC(args.p)
    
    '''
    Start tunning
    '''
    print("solverFlag: ",solverFlag)
    print("PSMAC mode: ","result from last step")
    print("Cuts time: ", args.cut)
    print("Tuning time limit: ", args.t)
    print("Parameter space file: ", pcsFile)
    print("cplex dll: ", args.cplex_dll)
    print("verbose: ", args.v)
    #result=call tunning function
    
    '''
    Handle tunning result and output
    '''
    #call handle function
    
if __name__=="__main__":
    main()

