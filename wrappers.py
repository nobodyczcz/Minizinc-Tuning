import sys, os, re, psutil, time, shlex
from subprocess import Popen, PIPE, TimeoutExpired
from random import randint

'''
This file store the wrapper of solvers which will be directly called by SMAC.
'''

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
    '''
    Handle the instance input from argument
    '''
    temp = instance.split('|')
    instance = ''
    for i in temp:
        i = '"'+i+'" '
        instance = instance + i
    return instance

def runMinizinc(cmd,cutoff):
    t = time.time()
    io = Popen(cmd, stdout=PIPE, stderr=PIPE)

    status = "CRASHED"
    quality = 99999
    try:
        (stdout_, stderr_) = io.communicate(timeout=cutoff)

        print('[MiniZinc out] ', stdout_)
        runtime = time.time() - t

        if re.search(b'time elapsed:', stdout_):
            status = "SUCCESS"
            if re.search(b'This is a minimization problem.', stdout_):
                quality = float(re.search(b'(?:mzn-stat objective=)(\d+\.\d+)', stdout_).group(1))
            elif re.search(b'This is a maximization problem.', stdout_):
                quality = -float(re.search(b'(?:mzn-stat objective=)(\d+\.\d+)', stdout_).group(1))
        elif re.search(b'=====UNKNOWN=====', stdout_):
            eprint('[MiniZinc error] ', stderr_)
            status = "CRASHED"
    except TimeoutExpired:
        io.kill()
        status = "TIMEOUT"
        runtime = cutoff
        quality = 99999
        
    return status, runtime, quality
    

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
        
        # Prepare temp parameter file
        paramfile = 'CPLEX Parameter File Version 12.6\n'
        for name, value in zip(params[::2], params[1::2]):
            paramfile += name.strip('-') + '\t' + value + '\n'
        tempParam = get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam , 'w') as f:
            f.write(paramfile)

        cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --solver cplex ' + instance + ' --readParam '\
              + tempParam + ' --cplex-dll ' + cplex_dll
        cmd = shlex.split(cmd)

        status, runtime, quality = runMinizinc(cmd,cutoff)
        
        try:
            os.remove(tempParam)
        except:
            eprint('[Wrapper Warn] remove temp param file failed')
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, runlength, quality, seed, specifics))
    except Exception as e:
        eprint('[Wrapper Exception] ', e)
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

        cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time' \
        + ' --solver osicbc ' + instance + ' --cbcArgs "'

        for name, value in zip(params[::2], params[1::2]):
            cmd += ' ' + name + ' ' + value
        cmd += '"'
        cmd = shlex.split(cmd)
        
        status, runtime, quality = runMinizinc(cmd, cutoff)

        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, quality, runlength, seed, specifics))
    except Exception as e:
        eprint('[Wrapper Exception] ', e)
        status = "CRASHED"
        runtime = 99999
        quality = 99999
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, 0, 0))


def gurobi(n_thread, cplex_dll):
    try:
        instance = sys.argv[1]
        specifics = sys.argv[2]
        cutoff = int(float(sys.argv[3]) + 1)  # runsolver only rounds down to integer
        runlength = int(sys.argv[4])
        seed = int(sys.argv[5])
        params = sys.argv[6:]

        print("#########", instance)
        instance = seperateInstance(instance)

        paramfile = '# Parameter Setting for Gruobi\n'
        for name, value in zip(params[::2], params[1::2]):
            paramfile += name.strip('-') + '\t' + value + '\n'
        tempParam = get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam, 'w') as f:
            f.write(paramfile)

        cmd = 'minizinc -p' + str(
            n_thread) + ' -s --output-time --solver gurobi ' + instance + ' --readParam ' + tempParam
        cmd = shlex.split(cmd)
        status, runtime, quality = runMinizinc(cmd, cutoff)
        
        try:
            os.remove(tempParam)
        except:
            eprint('[Wrapper warn] remove temp param file failed')
            
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, runlength, quality, seed, specifics))
    except Exception as e:
        eprint('[Wrapper Exception] ', e)
        status = "CRASHED"
        runtime = 99999
        quality = 99999
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, 0, 0))