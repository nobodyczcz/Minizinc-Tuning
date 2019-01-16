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
        
        
        with open(outputFile, 'w') as f:
            f.write(json.dumps(pcsDic, indent=4))
        print(pcsDic)
    
    def jsonToPcs(self,pcsFile,outputFile=None):
        """
        Convert Json parameter file to SMAC's pcs file
        """
        with open(pcsFile) as file:
            jsonData = json.load(file)
        
        if outputFile == None:
            outputFile = pcsFile.split('.')[0] + ".pcs"
        
        with open(outputFile, 'w') as f:
            for param in jsonData.keys():
                paramName = param
                paramType = jsonData[param]["type"]
                if paramType == "integer" or paramType == "real":
                    paramRange = str(jsonData[param]["range"]).replace("'","")
                else:
                    paramRange = str(jsonData[param]["range"]).replace("'","")[1:-1]
                    paramRange = "{"+paramRange+"}"
                default = "["+str(jsonData[param]["default"])+"]"
                line = paramName+" "+paramType+" "+paramRange+" "+default+"\n"
                f.write(line)
        return outputFile




        