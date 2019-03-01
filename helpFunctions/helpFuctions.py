import sys
import time


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs,flush=True)


def pprint(*args, **kwargs):
    print(*args, **kwargs, flush=True)


def get_current_timestamp():
    '''
    Get current timestamp
    '''
    return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))


def printPorgress(timeLimit):
    t = time.time()
    while (time.time() - t) < timeLimit:
        pprint("%%%mzn-progress", str(round((time.time() - t) / timeLimit, 2)))
        time.sleep(5)