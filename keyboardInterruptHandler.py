from subprocess import Popen, PIPE

def remove_tmp_files(instanceList):
    cmd = 'rm cplex_wrapper_?.py scenario* pre_run_time_check tmpParamRead* ' + ' '.join(instanceList)
    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)