def pSMAC_wrapper_generator(n_SMAC, n_MINIZINC):
    from cplex_wrapper_template import cplex_wrapper
    for i in range(n_SMAC):
        writeToFile = []
        writeToFile.append('from cplex_wrapper import cplex_wrapper')
        writeToFile.append('cplex_wrapper({}, {})'.format(i, n_MINIZINC))
        with open('cplex_wrapper_' + str(i) + '.py', 'w') as f:
            f.write('\n'.join(writeToFile))
            
def pSMAC_scenario_generator(n_SMAC, param_config_space, cutoff_time, wallclock_limit):
    for i in range(n_SMAC):
        writeToFile = []
        writeToFile.append('algo = python -u ./cplex_wrapper_{}.py'.format(i))
        writeToFile.append('paramfile = ./{}'.format(param_config_space))
        writeToFile.append('execdir = .')
        writeToFile.append('deterministic = 0')
        writeToFile.append('run_obj = runtime')
        writeToFile.append('overall_obj = PAR10')
        writeToFile.append('cutoff_time = {}'.format(cutoff_time))
        writeToFile.append('wallclock-limit = {}'.format(wallclock_limit))
        writeToFile.append('instance_file = instances.txt')
        with open('scenario_' + str(i) + '.txt', 'w') as f:
            f.write('\n'.join(writeToFile))