import sys, os, re, multiprocessing, subprocess, psutil, time, shlex
from subprocess import Popen, PIPE
from random import randint

def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def get_current_timestamp():
    '''
    Get current timestamp
    '''
    return time.strftime('[%Y%m%d%H%M%S]', time.localtime(time.time()))    

def eprint(*args, **kwargs):
    """
    A help funtion that print to stderr
    """
    print(*args, file=sys.stderr, **kwargs)

def seperateInstance(instance):
    temp = instance.split('|')
    instance = ''
    for i in temp:
        i = '"'+i+'" '
        instance = instance + i
    return instance

def cplex(n_thread, cplex_dll):

    instance = sys.argv[1]
    specifics = sys.argv[2]
    cutoff = int(float(sys.argv[3]) + 1) # runsolver only rounds down to integer
    runlength = int(sys.argv[4])
    seed = int(sys.argv[5])
    params = sys.argv[6:]
    print("#########",instance)
    instance = seperateInstance(instance)

    paramfile = 'CPLEX Parameter File Version 12.6\n'

    for name, value in zip(params[::2], params[1::2]):
        paramfile += name.strip('-') + '\t' + value + '\n'
    
    tempParam = get_current_timestamp() + str(randint(1, 999999))
    with open(tempParam , 'w') as f:
        f.write(paramfile)

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit ' + str(cutoff * 1000) + ' --solver cplex ' + instance     + ' --readParam ' + tempParam     + ' --cplex-dll ' + cplex_dll
    cmd = shlex.split(cmd)
    io = Popen(cmd, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    print('out: ', stdout_)
    print('error: ', stderr_)
    #io.wait()

    #eprint("stdout:", stdout_.decode('utf-8'), "\nstderr:", stderr_.decode('utf-8'))


    status = "CRASHED"
    runtime = 99999
    os.remove(tempParam)

    if re.search(b'time elapsed:', stdout_):
        runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
        status = "SUCCESS"
    elif re.search(b'=====UNKNOWN=====', stdout_):
        runtime = cutoff
        status = "TIMEOUT"

    print('Result of this algorithm run: {}, {}, {}, 0, {}, {}'.format(status, runtime, runlength, seed, specifics))


def osicbc(n_thread,empty):

    instance = sys.argv[1]
    specifics = sys.argv[2]
    cutoff = int(float(sys.argv[3]) + 1) # runsolver only rounds down to integer
    runlength = int(sys.argv[4])
    seed = int(sys.argv[5])
    params = sys.argv[6:]

    instance = seperateInstance(instance)

    cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --time-limit ' \
    + str(cutoff * 1000) + ' --solver osicbc ' + instance + ' --cbcArgs "'

    for name, value in zip(params[::2], params[1::2]):
        cmd += ' ' + name + ' ' + value
    cmd += '"'
    cmd = shlex.split(cmd)
    io = Popen(cmd, stdout=PIPE, stderr=PIPE)
    
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
