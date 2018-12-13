import sys, os, re
from subprocess import Popen, PIPE
import pandas as pd

def runCmd(cmd):
    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    if len(stdout_) == 0:
        raise Exception(stderr_.decode('utf-8'))
    else:
        return stdout_
    
def runMinizinc(batch, instance, flag, n_Minizinc, runmode, arglist, cplex_param, cplex_dll):
    avgtime = 0
    for j in range(batch):
        print('running batch', j + 1)
        if flag == 0:
            
            if runmode == 0:
                cmd = 'minizinc -p' + str(n_Minizinc) + ' -s --solver osicbc ' + instance
            else:
                cmd = 'minizinc -p' + str(n_Minizinc) + ' -s --solver osicbc ' + instance + ' --cbcArgs ' + '"' + arglist + '"'
        else:
            
            if runmode == 0:
                cmd = 'minizinc -p' + str(n_Minizinc) + ' -s --solver cplex ' + instance + ' --cplex-dll ' + cplex_dll
            else:
                cmd = 'minizinc -p' + str(n_Minizinc) + ' -s --solver cplex ' + instance + ' --readParam ' \
                + cplex_param + ' ' + ' --cplex-dll ' + cplex_dll
        #print(cmd)
        
        avgtime += float(re.search(b'(?:time=)(\d+\.\d+)', runCmd(cmd)).group(1))
    avgtime /= batch
    print('Average Time:', avgtime)
    return avgtime


def runBenchmark(batch, instance, stdout_, flag, n_Minizinc, cplex_dll):
    benchmark = {}
    for i in stdout_.split(b'\n'):
        print(i)
        if len(i) != 0:
            df = pd.read_csv(i.decode('utf-8'))
            df.reset_index(inplace=True)
            print(df.iloc[-1][5:].values)
            if flag == 0:
                arglist = ''
            else:
                param = 'CPLEX Parameter File Version 12.6\n'
                
            for i in df.iloc[-1][5:].values:
                tmp = re.findall("[a-zA-Z\_\.\+\-0-9]+", i)
                if flag ==0:
                    arglist += '-' + tmp[0] + ' ' + tmp[1] + ' '
                else:
                    param += tmp[0] + '\t' + tmp[1] + '\n'
            if flag != 0:
                with open('benchmark_cplex_param_cfg', 'w') as f:
                    f.write(param)
            
            
            if flag == 0:
                print(arglist)
                avgtime = runMinizinc(batch, instance, flag, n_Minizinc, 1, arglist, '', cplex_dll)
                benchmark[arglist] = avgtime

            else:
                print(param)
                avgtime = runMinizinc(batch, instance, flag, n_Minizinc, 1, '', 'benchmark_cplex_param_cfg', cplex_dll)
                benchmark[param] = avgtime

    if flag == 0:
        avgtime = runMinizinc(batch, instance, flag, n_Minizinc, 0, '', '', cplex_dll)
        benchmark['base'] = avgtime
    else:
        avgtime = runMinizinc(batch, instance, flag, n_Minizinc, 0, '', '', cplex_dll)
        benchmark['base'] = avgtime        
    print(benchmark)            
    best_args = min(benchmark, key=benchmark.get)
    print('Recommended:\n', best_args)
    print('runtime: {}'.format(benchmark[best_args]))

def benchmark_main(instanceList, flag, n_Minizinc, cplex_dll, batch=5):
    for instance in instanceList:
        cmd = 'find . -name traj_old.csv'
        stdout_ = runCmd(cmd)
        runBenchmark(batch, instance, stdout_, flag, n_Minizinc, cplex_dll)