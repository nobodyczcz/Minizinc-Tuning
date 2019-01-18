from initializer import *

solver = sys.argv[1]
outputDir = sys.argv[2]
cutOffTime = int(sys.argv[3])
instance = sys.argv[4]
p = int(sys.argv[5])
cplex_dll = sys.argv[6]
initialCwd = os.getcwd()

if solver == 'osicbc':
    initializer = CbcInitial(cutOffTime, 0, False, None, p, None, None, cplex_dll,None,1,None)
elif solver == 'cplex':
    initializer = CplexInitial(cutOffTime, 0, False, None, p, None, None, cplex_dll,None,1,None)
os.chdir(sys.path[0]+"/cache") 
initializer.instanceList = [instance]
initializer.initialCwd = initialCwd
initializer.outputdir = outputDir
print(cutOffTime)

initializer.benchmark_main(5)


