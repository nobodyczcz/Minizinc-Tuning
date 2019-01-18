import sys, os, re, psutil, time, shlex
from subprocess import Popen, PIPE, TimeoutExpired
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
    try:
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

        try:
            os.remove(tempParam)
        except:
            print('[warn] remove temp param file failed')
        
        quality = 99999
        if re.search(b'time elapsed:', stdout_):
            runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
            status = "SUCCESS"
            if re.search(b'This is a minimization problem.',stdout_):
                quality = float(re.search(b'(?:mzn-stat objective=)(\d+\.\d+)', stdout_).group(1))
            elif re.search(b'This is a maximization problem.',stdout_):
                quality = -float(re.search(b'(?:mzn-stat objective=)(\d+\.\d+)', stdout_).group(1))
        elif re.search(b'=====UNKNOWN=====', stdout_):
            runtime = cutoff
            status = "TIMEOUT"

        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, runlength, quality, seed, specifics))
    except:
        status = "CRASHED"
        runtime = 99999
        quality = 99999
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, 0, 0))


def osicbc(n_thread,empty):
    try:
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
        quality = 99999
        
        try:
            (stdout_, stderr_) = io.communicate(timeout=cutoff)

            eprint("stdout:", stdout_.decode('utf-8'), "\nstderr:", stderr_.decode('utf-8'))
            
            if re.search(b'time elapsed:', stdout_):
                runtime = float(re.search(b'(?:mzn-stat time=)(\d+\.\d+)', stdout_).group(1))
                status = "SUCCESS"
                if re.search(b'This is a minimization problem.',stdout_):
                    quality = float(re.search(b'(?:mzn-stat objective=)(\d+\.\d+)', stdout_).group(1))
                elif re.search(b'This is a maximization problem.',stdout_):
                    quality = -float(re.search(b'(?:mzn-stat objective=)(\d+\.\d+)', stdout_).group(1))
            elif re.search(b'=====UNKNOWN=====', stdout_):
                runtime = cutoff
                status = "TIMEOUT"        
        except TimeoutExpired:
            print("timeoutttttttttttttttttt")
            kill(io.pid)
            runtime = cutoff
            status = "TIMEOUT"

        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, quality, runlength, seed, specifics))
    except:
        status = "CRASHED"
        runtime = 99999
        quality = 99999
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, 0, 0))
