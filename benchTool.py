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
parser.add_argument('-a', type=int,default = None,\
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

if solver == 'osicbc':
    initializer = CbcInitial(cutOffTime, 0, False, None, p, None, instance, cplex_dll,programPath,1,None)
elif solver == 'cplex':
    initializer = CplexInitial(cutOffTime, 0, False, None, p, None, instance, cplex_dll,programPath,1,None)
elif solver == 'gurobi':
    initializer = GurobiInitial(cutOffTime, 0, False, None, p, None, instance, cplex_dll,programPath,1,None)
initializer.process_instance()
os.chdir(sys.path[0]+"/cache")
initializer.initialCwd = initialCwd
initializer.outputdir = outputDir

if args.a is not None:
    stdout_ = glob.glob('./smac-output/' + initializer.outputdir + '/traj-run*.txt')
    print("Output found: ", stdout_)

    count=1
    for i in stdout_:
        if len(i) != 0:
            print("Configuration file: ", i)
            res = [line.rstrip('\n') for line in open(i)]
            for setting in res[args.a:]:
                print('Out put: ', setting)
                fileName = time.strftime('[%Y%m%d%H%M%S]', time.localtime(time.time()))+count
                print('to :',fileName)
                finalParam = initializer.param_generate(setting, initializer.initialCwd + '/' + fileName)
                count+=1
elif args.skip:
    initializer.noBnechOutput(-2,args.a)
else:
    initializer.benchmark_main(1,-1)


