from subprocess import Popen, PIPE
from random import randint

def psmac_args(n_SMAC, flag, verbose):
    
    cmd = []
    io = Popen('which smac', shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    if len(stdout_) == 0:
        raise Exception("SMAC path not found in environment.")
    else:
        smac_path = stdout_.decode('utf-8').strip('\n')
        
    for i in range(n_SMAC):
        tmp = ''
        if flag == 0:
            tmp += '(python ' + smac_path + ' --scenario scenario.txt --seed ' + str(randint(1, 999999)) +\
            ' --shared_model True ' + '--output_dir runs ' + '--input_psmac_dirs runs/run*'
            if verbose:
                tmp += ' --verbose DEBUG)'
            else:
                tmp += ')'
            cmd.append(tmp)
        else:
            tmp += '(python ' + smac_path + ' --scenario scenario_' + str(i) + '.txt --seed ' + str(randint(1, 999999)) +\
            ' --shared_model True ' + '--output_dir runs ' + '--input_psmac_dirs runs/run*' 
            if verbose:
                tmp += ' --verbose DEBUG)'
            else:
                tmp += ')'
            cmd.append(tmp)
    return ' & '.join(cmd)


def psamc_exe(n_SMAC, flag, verbose):
    
    cmd = psmac_args(n_SMAC, flag, verbose)
    
    print('cmd:', cmd)
    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    #print("Process ID of subprocess %s" % io.pid)
    #(stdout_, stderr_) = io.communicate()
    if verbose:
        while io.poll() is None:
            line = io.stdout.readline()
            print(line.decode('utf-8'), end =" ")       
    #return io.pid