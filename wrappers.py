import sys, os, re, multiprocessing, subprocess, psutil, time
from subprocess import Popen, PIPE

def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def get_current_timestamp(self):
    '''
    Get current timestamp
    '''
    return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))    

def eprint(*args, **kwargs):
    """
    A help funtion that print to stderr
    """
    print(*args, file=sys.stderr, **kwargs)

def cplex_wrapper(n, n_thread, cplex_dll):

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

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit ' + str(cutoff * 1000) + ' --solver cplex ' + instance     + ' --readParam tmpParamRead_' + str(n)     + ' --cplex-dll ' + cplex_dll


    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    #io.wait()

    #eprint("stdout:", stdout_.decode('utf-8'), "\nstderr:", stderr_.decode('utf-8'))


    status = "CRASHED"
    runtime = 99999

    if re.search(b'time elapsed:', stdout_):
        runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
        status = "SUCCESS"
    elif re.search(b'=====UNKNOWN=====', stdout_):
        runtime = cutoff
        status = "TIMEOUT"

    print('Result of this algorithm run: {}, {}, {}, 0, {}, {}'.format(status, runtime, runlength, seed, specifics))


def cbc_wrapper(n_thread):

    instance = sys.argv[1]
    specifics = sys.argv[2]
    cutoff = int(float(sys.argv[3]) + 1) # runsolver only rounds down to integer
    runlength = int(sys.argv[4])
    seed = int(sys.argv[5])
    params = sys.argv[6:]

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit ' \
    + str(cutoff * 1000) + ' --solver osicbc ' + instance + ' --cbcArgs "'

    for name, value in zip(params[::2], params[1::2]):
        cmd += ' ' + name + ' ' + value
    cmd += '"'

    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    
    status = "CRASHED"
    runtime = 99999
    
    
    try:
        (stdout_, stderr_) = io.communicate(timeout=cutoff)

        eprint("stdout:", stdout_.decode('utf-8'), "\nstderr:", stderr_.decode('utf-8'))
        
        if re.search(b'time elapsed:', stdout_):
            runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
            status = "SUCCESS"
        elif re.search(b'=====UNKNOWN=====', stdout_):
            runtime = cutoff
            status = "TIMEOUT"        
        
    except subprocess.TimeoutExpired:
        print("timeoutttttttttttttttttt")
        kill(io.pid)
        runtime = cutoff
        status = "TIMEOUT"

    print('Result of this algorithm run: {}, {}, {}, 0, {}, {}'.format(status, runtime, runlength, seed, specifics))
