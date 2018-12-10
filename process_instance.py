from subprocess import Popen, PIPE
import re

def process_instance(ins_list='', ins_path=''):
    '''
    Process instance list or path to combine the model file with instance file(s) and write to a txt file with standard format for SMAC.
    
    '''
    
    if ins_list != '': # If list of instance is provided
        instance = ins_list
    elif ins_path != '': # If instance input file is provided
        try:
            instance = [line.rstrip('\n') for line in open(ins_path)]
        except FileNotFoundError:
            raise Exception("FileNotFoundError: No such file or directory")
    else:
        raise Exception('No path or list of instance is passed.')
        
    instanceList = []
    for i in instance:

        if len(re.findall('[^\.\s]+\.mzn', i)) > 1: # Require one model file in each line
            raise Exception('More than one model file found in the same line.')
        elif len(re.findall('^[^\.\s]+\.mzn', i)) == 0: # Require model file at first of each line
            raise Exception('Model file must come first in each line.')

        for j in i.split()[1:]:
            newName = i.split()[0].split('.')[0] + '_' + j.split('.')[0] + '.mzn' # Get name of combined model file
            #print("cat " + i.split()[0] + " " + j + " > " + newName)
            cmd = "cat " + i.split()[0] + " " + j + " > " + newName # Prepare the shell script for concat
            io = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE) # Excecute concat
            (stdout_, stderr_) = io.communicate()
            #print(stdout_)
            instanceList.append(newName)
            
    with open('instances.txt', 'w') as f:
        f.write('\n'.join(instanceList)) # Write the formated instance file to text for smac read in. 
        
    return instanceList # Return the combined file list for removal after smac optimization
        
if __name__ == "__main__":
    process_instance(ins_path='instance_input_example.txt')