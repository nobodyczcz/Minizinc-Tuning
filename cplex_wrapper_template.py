import sys, os, re
from subprocess import Popen, PIPE

def cplex_wrapper(n, n_thread):
    
    instance = sys.argv[1]
    specifics = sys.argv[2]
    cutoff = int(float(sys.argv[3]) + 1) # runsolver only rounds down to integer
    runlength = int(sys.argv[4])
    seed = int(sys.argv[5])
    params = sys.argv[6:]


    paramfile = 'CPLEX Parameter File Version 12.6\n'

    for name, value in zip(params[::2], params[1::2]):
        paramfile += name.strip('-') + '\t' + value + '\n'

    with open('tmpParamRead_' + str(n) , 'w') as f:
        f.write(paramfile)

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit ' \
    + str(cutoff * 1000) + ' --solver cplex ' + instance \
    + ' --readParam tmpParamRead' \
    + ' --cplex-dll /opt/ibm/ILOG/CPLEX_Studio128/cplex/bin/x86-64_linux/libcplex1280.so'

    #print(cmd)

    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()

    print(stdout_)
    print(stderr_)
    status = "CRASHED"
    runtime = 99999

    if re.search(b'time elapsed:', stdout_):
        runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
        status = "SUCCESS"
    elif re.search(b'=====UNKNOWN=====', stdout_):
        runtime = cutoff
        status = "TIMEOUT"

    print('Result for SMAC: {}, {}, {}, 0, {}, {}'.format(status, runtime, runlength, seed, specifics))