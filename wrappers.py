import sys, os, re, time, shlex
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

def runMinizinc(cmd,cutoff,maximize,obj_mode,obj_bound=None):
    """
    The function will execute the command line and return running result.
    :param cmd: the command line will be executed
    :param cutoff: cut off time of each run
    :return: status, runtime, quality
    """
    t = time.time()
    print('[Wraper out]', cmd)
    if obj_bound is not None:
        cmd.append('-a')
    io = Popen(cmd, stdout=PIPE, stderr=PIPE)
    pidFile = "pid"+str(io.pid)
    with open(pidFile, 'w') as f:
        f.write(str(io.pid))
    try:
        tempOut = open('temp.txt','w')
    except:
        pass
    status = "CRASHED"
    quality = 9999999
    runtime = cutoff
    try:
        if obj_bound is not None:
            while io.poll() is None and time.time()-t<=cutoff:
                line = io.stdout.readline().decode('utf-8')
                try:
                    tempOut.append(line)
                except:
                    pass

                try:
                    quality = float(re.search('(?:mzn-stat objective=)((\d+\.\d+)|(\d+))', line).group(1))
                    if maximize:
                        quality = -quality
                    runtime = time.time() - t
                    status = 'SUCCESS'
                except:
                    pass
                if maximize:
                    if quality >= obj_bound:
                        break
                else:
                    if quality <= obj_bound:
                        break
            io.terminate()
            if quality == 9999999:
                status = 'TIMEOUT'
        else:
            (stdout_, stderr_) = io.communicate(timeout=cutoff)

            eprint('[MiniZinc out] ', stdout_.decode('utf-8'))
            tempOut.append(stdout_.decode('utf-8'))
            runtime = time.time() - t

            if re.search(b'time elapsed:', stdout_):
                status = "SUCCESS"
                quality = float(re.search(b'(?:mzn-stat objective=)((\d+\.\d+)|(\d+))', stdout_).group(1))
                if maximize:
                    quality = -quality
                if obj_mode:
                    runtime = cutoff/3
            elif re.search(b'=====UNKNOWN=====', stdout_):
                eprint('[MiniZinc Warn][UNKNOWN] ', stderr_.decode('utf-8'))
                if obj_mode:
                    try:
                        quality = float(re.search(b'(?:mzn-stat objective=)((\d+\.\d+)|(\d+))', stdout_).group(1))
                    except:
                        pass
                    runtime = cutoff/3
                status = "CRASHED"
            else:
                eprint('[MiniZinc error] ', stderr_.decode('utf-8'))

    except TimeoutExpired:
        io.terminate()
        status = "TIMEOUT"
        runtime = cutoff
        quality = 9999999
    finally:
        try:
            os.remove(pidFile)
        except:
            pass
    return status, runtime, quality
    
def preProcess(obj_mode):
    instance = sys.argv[1]
    specifics = sys.argv[2]
    cutoff = int(float(sys.argv[3]) + 1) # runsolver only rounds down to integer
    runlength = int(sys.argv[4])
    seed = int(sys.argv[5])
    params = sys.argv[6:]
    time_limit = 0
    if obj_mode:
        time_limit = cutoff*1000
        cutoff = 3*cutoff
    return instance, specifics,cutoff,runlength,seed,params,time_limit

def cplex(n_thread, cplex_dll,maximize,obj_mode=False, obj_bound=None):
    """
    The wrapper for cplex. generate command and print run result.
    :param n_thread: how many threads minizinc use
    :param cplex_dll: the dll file of minizinc if need to use
    :return: none. print to stdout
    """
    try:
        instance, specifics,cutoff,runlength,seed,params,time_limit = preProcess(obj_mode)

        instance = seperateInstance(instance)
        
        # Prepare temp parameter file
        paramfile = 'CPLEX Parameter File Version 12.6\n'
        for name, value in zip(params[::2], params[1::2]):
            if name == '-MinizincThreads':
                n_thread = value
            else:
                paramfile += name.strip('-') + '\t' + value + '\n'
        tempParam = get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam , 'w') as f:
            f.write(paramfile)

        cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time --solver cplex ' + instance
        if obj_mode:
            cmd += ' --solver-time-limit ' + str(time_limit)
        cmd += ' --readParam ' + tempParam
        if cplex_dll != 'None':
            eprint(cplex_dll)
            cmd = cmd + ' --cplex-dll ' + cplex_dll
        if obj_bound:
            cmd += ' -a'
        cmd = shlex.split(cmd)

        status, runtime, quality = runMinizinc(cmd,cutoff,maximize,obj_mode,obj_bound)
        
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


def osicbc(n_thread,empty,maximize,obj_mode=False, obj_bound=None):
    """
    The wrapper for osicbc. generate command and print run result.
    :param n_thread: how many threads minizinc use
    :param cplex_dll: the dll file of minizinc if need to use
    :return: none. print to stdout
    """
    try:
        instance, specifics,cutoff,runlength,seed,params,time_limit = preProcess(obj_mode)
        instance = seperateInstance(instance)

        args = ''
        for name, value in zip(params[::2], params[1::2]):
            if name == '-MinizincThreads':
                n_thread = value
            else:
                args += ' ' + name + ' ' + value

        cmd = 'minizinc -p' + str(n_thread) + ' -s --output-time' \
              + ' --solver osicbc ' + instance
        if obj_mode:
            cmd += ' --solver-time-limit ' + str(time_limit)
        cmd += ' --cbcArgs "' + args + '"'

        if obj_bound:
            cmd += ' -a'
        cmd = shlex.split(cmd)
        
        status, runtime, quality = runMinizinc(cmd, cutoff,maximize,obj_mode,obj_bound)

        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, quality, runlength, seed, specifics))
    except Exception as e:
        eprint('[Wrapper Exception] ', e)
        status = "CRASHED"
        runtime = 99999
        quality = 99999
        print('Result of this algorithm run: {}, {}, {}, {}, {}, {}'.format(status, runtime, 0, quality, 0, 0))


def gurobi(n_thread, dll,maximize,obj_mode=False, obj_bound=None):
    """
    The wrapper for gurobi. generate command and print run result.
    :param n_thread: how many threads minizinc use
    :param cplex_dll: the dll file of minizinc if need to use
    :return: none. print to stdout
    """
    try:
        instance, specifics,cutoff,runlength,seed,params,time_limit = preProcess(obj_mode)
        instance = seperateInstance(instance)

        paramfile = '# Parameter Setting for Gruobi\n'
        for name, value in zip(params[::2], params[1::2]):
            if name == '-MinizincThreads':
                n_thread = value
            else:
                paramfile += name.strip('-') + '\t' + value + '\n'
        tempParam = get_current_timestamp() + str(randint(1, 999999))
        with open(tempParam, 'w') as f:
            f.write(paramfile)

        cmd = 'minizinc -p' + str(
            n_thread) + ' -s --output-time --solver gurobi ' + instance + ' --readParam ' + tempParam
        if obj_mode:
            cmd += ' --solver-time-limit ' + str(time_limit)
        if dll != 'None':
            cmd = cmd + ' --gurobi-dll ' + dll
        if obj_bound:
            cmd += ' -a'
        cmd = shlex.split(cmd)
        status, runtime, quality = runMinizinc(cmd, cutoff,maximize,obj_mode,obj_bound)
        
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

# def main():
#     solver = sys.argv[1]
#     if solver == 'cplex':
#
#     elif solver == 'osicbc':
#
#     elif solver == 'gurobi':