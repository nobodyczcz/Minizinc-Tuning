# -*- coding: utf-8 -*-
"""
Created on Wed Jan  9 11:28:44 2019

@author: czcz2
"""
import json


class pcsConverter():
    """
    The pcsConverter handles the convertion between json parameter configuration space file and SMAC's pcs file
    """
    
    def pcsToJson(self,pcsFile,outputFile=None):
        """
        Convert SMAC's pcs file to JSON file
        """
        pcsDic={}
        with open(pcsFile) as file:
            lines = [line.rstrip('\n') for line in file]
            
            # Remove any blank lines from  file
            lines = [x for x in lines if x != '']
            
            for line in lines:
                splitLine = line.split(" ")
                
                paramName = splitLine[0]
                paramType = splitLine[1]
                paramRange = splitLine[2][1:-1].split(",")
                default=splitLine[3][1:-1]
                
                if paramType == "integer" :
                    #convert str to int
                    paramRange = [int(x) for x in paramRange]
                    default = int(default)
                elif paramType == "real" :
                    #convert str to float
                    paramRange = [float(x) for x in paramRange]
                    default = float(default)
                
                pcsDic[paramName]={"type":paramType,"range":paramRange,"default":default}
                print(paramName,": ",pcsDic[paramName])
                
        if outputFile == None:
            outputFile = pcsFile.split('.')[0] + ".json"
        pcsDic = {"name":pcsFile.split('.')[0],"description":"","parameters":pcsDic}
        
        with open(outputFile, 'w') as f:
            f.write(json.dumps(pcsDic, indent=4))
        print(pcsDic)
    
    def jsonToPcs(self,pcsFile,outputFile=None,threads=None):
        """
        Convert Json parameter file to SMAC's pcs file
        """
        with open(pcsFile) as file:
            jsonData = json.load(file)
        
        if outputFile == None:
            outputFile = pcsFile.split('.')[0] + ".pcs"
        
        with open(outputFile, 'w') as f:
            if threads is not None:
                line = 'MinizincThreads integer [1,'+str(threads)+'] ['+str(threads)+']\n'
                f.write(line)
            parameters = jsonData["parameters"]
            for param in parameters.keys():
                paramName = param
                paramType = parameters[param]["type"]
                if paramType == "integer" or paramType == "real":
                    if (parameters[param]["range"][1] - parameters[param]["range"][0]) > 1000:
                        paramType = 'ordinal'
                        newRange = []
                        maxi = int(parameters[param]["range"][1])
                        mini = int(parameters[param]["range"][0])
                        while mini < maxi:
                            newRange.append(mini)
                            if mini <= 0:
                                mini = 1
                            else:
                                mini = 10 * mini
                        paramRange = str(newRange).replace("'", "")[1:-1]
                        paramRange = "{" + paramRange + "}"
                    else:
                        paramRange = str(parameters[param]["range"]).replace("'","")

                else:
                    paramRange = str(parameters[param]["range"]).replace("'","")[1:-1]
                    paramRange = "{"+paramRange+"}"
                default = "["+str(parameters[param]["default"])+"]"
                line = paramName+" "+paramType+" "+paramRange+" "+default+"\n"
                f.write(line)
        return outputFile




        