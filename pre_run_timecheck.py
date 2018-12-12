import sys, os, re
from subprocess import Popen, PIPE

def default_param_config(param_config_space, flag):
    lines = [line.rstrip('\n') for line in open(param_config_space)]
    paramList = []
    for line in lines:
        if re.search('(\[)([a-zA-Z0-9]+)(\])', line):
            default_val = re.search('(\[)([a-zA-Z0-9]+)(\])', line).group(2)
            if flag == 0:
                paramList.append('-' + line.split()[0] + ' ' + str(default_val))
            else:
                paramList.append(line.split()[0] + '\t' + str(default_val))
    if flag == 0:
        return ' '.join(paramList)
    else:
        paramList.insert(0, 'CPLEX Parameter File Version 12.6')
        with open('pre_run_time_check', 'w') as f:
            f.write('\n'.join(paramList))
            

def run_solver(n_thread, param_config_space, instance, flag, cplex_dll):
    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --solver '
    args = default_param_config(param_config_space, flag)
    
    if flag == 0:        
        cmd += 'osicbc ' + instance + ' --cbcArgs "' + args + '"'
    else:
        cmd += 'cplex ' + instance + ' --readParam pre_run_time_check' + \
        ' --cplex-dll ' + str(cplex_dll)
    print('cmd:', cmd)
    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    
    print(stdout_.decode('utf-8'), end=' ')
    print(stderr_.decode('utf-8'), end=' ')
    if re.search(b'time elapsed:', stdout_):
        runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
        return runtime
    
    
    
def instance_runtime(instanceList, n_thread, param_config_space, flag, cplex_dll):
    runtime = -1
    for instance in instanceList:
        print(instance)
        tmp = run_solver(n_thread, param_config_space, instance, flag, cplex_dll)
        print(tmp)
        if tmp > runtime:
            runtime = tmp
    return runtime