from initializer import *
import argparse,inspect

parser = argparse.ArgumentParser(prog='Output and benchmark tool',\
                                     formatter_class=argparse.RawTextHelpFormatter,\
                                     description='')

parser.add_argument('--solver',choices=['osicbc','cplex','gurobi'],required=True,metavar='osicbc/cplex',\
                        help='''\
                        ''')

parser.add_argument('--outputDir',type=str,required=True,\
                        help='''\
                        ''')
parser.add_argument('-c','--cutOff',type=float,\
                        help='''\
                        ''')

parser.add_argument('instance', nargs='*', type=str, default= None,\
                        metavar='"model-name.mzn data1.dzn data2.dzn"',\
                        help='')

parser.add_argument('-p',type=int,default = 1,\
                        help='''\
                        ''')
parser.add_argument('--cplex-dll',type=str,\
                        help='''\
                        ''')
parser.add_argument('-skip',default = False, action='store_true',\
                        help='''\
                        ''')
parser.add_argument('-a',default = False,action='store_true',\
                        help='''\
                        ''')
parser.add_argument('-row',default = -1, type=int,\
                        help='''\
                        ''')
args = parser.parse_args() 

solver = args.solver
outputDir = args.outputDir
cutOffTime = args.cutOff
instance = args.instance
p = args.p
cplex_dll = args.cplex_dll
initialCwd = os.getcwd()
filename = inspect.getframeinfo(inspect.currentframe()).filename
programPath = os.path.dirname(os.path.abspath(filename))

initializer = Initializer(solver, cutOffTime, False, None, p,instance, cplex_dll,programPath,None,True,False)

initializer.process_instance(instance,programPath)
os.chdir(sys.path[0]+"/cache")
initializer.initialCwd = initialCwd
initializer.outputdir = initialCwd + '/smac-output/'
initializer.rungroup =outputDir


if args.skip:
    initializer.noBnechOutput(-2,args.a)
else:
    initializer.benchmark_main(1,-1)


