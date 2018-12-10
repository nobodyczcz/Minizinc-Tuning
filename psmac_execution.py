from subprocess import Popen, PIPE
from random import randint

def psmac_args(n_SMAC, flag, verbose=False):
    
    cmd = []
    io = Popen('which smac', shell=True, stdout=PIPE, stderr=PIPE)
    
    if len(stdout_) == 0:
        raise Exception("SMAC path not found in enviroment.")
    else:
        smac_path = stdout_.decode('utf-8').strip('\n')
        
    for i in range(n_SMAC):
        tmp = ''
        if flag == 0:
            tmp += '(python ' + smac_path + '--scenario scenario.txt --seed ' + str(randint(1, 999999)) +\
            ' --shared_model True ' + '--output_dir runs ' + '--input_psmac_dirs runs/run*'
            if verbose:
                tmp += '--verbose True)'
            else:
                tmp += ')'
            cmd.append(tmp)
        else:
            tmp += '(python ' + smac_path + '--scenario scenario_' + str(i) + '.txt --seed ' + str(randint(1, 999999)) +\
            ' --shared_model True ' + '--output_dir runs ' + '--input_psmac_dirs runs/run*' 
            if verbose:
                tmp += '--verbose True)'
            else:
                tmp += ')'
            cmd.append(tmp)
    return ' & '.join(cmd)


def psamc_exe(cmd, n_SMAC, flag, verbose=False):
    
    cmd = psmac_args(n_SMAC, flag, verbose=False)
    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    (stdout_, stderr_) = io.communicate()
    if verbose:
        print(stdout_.decode('utf-8'))
        print(stderr_.decode('utf-8'))
        
        