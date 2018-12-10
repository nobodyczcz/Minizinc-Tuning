from subprocess import Popen, PIPE

def remove_tmp_files(args):
    cmd = 'rm cplex_wrapper_? scenario* pre_run_time_check tmpParamRead*'
    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)