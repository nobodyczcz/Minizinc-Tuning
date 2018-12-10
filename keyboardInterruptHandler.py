import signal
from subprocess import Popen, PIPE

def keyboardInterruptHandler(signal, instanceList):
    print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(signal))
    remove_tmp_files(instanceList)
    exit(0)
    
def remove_tmp_files(args):
    cmd = 'rm cplex_wrapper_? scenario* pre_run_time_check tmpParamRead*'
    io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    
signal.signal(signal.SIGINT, keyboardInterruptHandler(signal, 'test'))

while True:
    pass