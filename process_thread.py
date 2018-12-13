import multiprocessing

def process_thread(n_thread=1):
    
    '''
    Compute number of smac that can run in parallel given the user input
    '''
    
    n_cores = multiprocessing.cpu_count() # Get number of threads available in the system
    
    if n_thread == 1: # Each SMAC occupies one thread
        return (n_cores, 1) # Return #SMAC and #thread for Minizinc
    elif n_thread < n_cores and n_cores % n_thread == 0: # Each SMAC occupies n_thread specified by user
        return (n_cores / n_thread, n_thread) # Return #SMAC and #thread for Minizinc
    else:
        raise Exception("{} threads found in the system. However {} threads specified by user.".format(n_cores, n_thread))