# Minizinc-Tuning

This is a Automatic parameter tunning program for Minizinc solvers. Currently support cplex and osicbc and able to perform parameter tunning on multiple instanes. The program use [SMAC v2.10.03](http://www.cs.ubc.ca/labs/beta/Projects/SMAC/) to perform parameter tunning.


# Requirement

1. Java (Tested on 8, not sure does it working on 9 or 10)

   SMAC2 is written in java.
   
2. Python 3.x

   This program is written in python. (At first we use SMAC3 in python, which require some dependencies only working on linux, but based on the consideration of cross-platform we move to SMAC2 in Java)
 
3. psutil

   The program require psutil python module. Anaconda have this module on default. If you meet error "No module named 'psutil'", you can install it by:
   
   `pip install psutil`

4. Minizinc
   
5. Currently only working on Linux. But will soon working on Windows and Mac

# Usage

1. Go to the directory of your model files and data files

2. Use a command in following format to start tunning:

```
python Path/to/Minizinc-Tunning.py --solver [1] -p [2] -psmac [3] -t [4]  --cplex-dll[5] -pcsJson [6] [7]
```
\[1]: Solver you want to use: cplex / osicbc

\[2]: How many processors that minizinc use to solve the problem. Attention the prameter configration for certain amount processors may not work when using another processors setting. This means if you use -p 2 for parameter tunning, the tunning result may not improve the model solving speed if you run minizinc with -p 1. (-p is not necessary. If remove -p, it will use default value 1)

\[3] Number of smac running parallel. Can be removed if you do not need psmac

Parallel smac can improve the tunning efficiency a lot. If you have enough cpu to run psmac, it is suggested to use it. For cpu with 8 threads, if you run minizinc with -p 1, you can use -psmac 6. If minizinc use -p 2 , you can try -psmac 3. Do not use all aviable threads, as cpus are not only used by minizinc and smac. 

\[4]: Total time limit for tunning the program, unit is seconds. If your models that needs around 300 seconds to solve with -p 1, it is suggested to tuning for more than 6 hours (21600 seconds) with -psmac 6 to achieve a extreme boost. If you only tunning for 3 hours, it will also give you a improved parameter configuration, but not as good as 6 hour result. It is suggested to make it run as long as possible. Sleeping time is very suitable to perform tunning.

\[5]: The path of cplex dll/so file. Remove it if you are using osicbc

\[6]: The path to json parameter configuration space file. We provide two (osicbc.json, cplex.json) in our program folder.

\[7]: models and datas: "Model1.mzn data1.dzn data2.dzn" "Model2.mzn data21.dzn" "Model3.mzn data31.dzn data32.dzn data33.dzn ..." ....

It is suggested to use simiar model for tunning. Also suggested to use big instances together with small instances. For big instances, I mean need several hundred or even thoundrends seconds to solve. For small instances, I mean the instances can be solve within 60 seconds.

### For example:
```
python Path/to/your/tuning program/Minizinc-Tunning.py --solver cplex -p 2 -t 3600 -pcsJson path/to/cplex.json "mapping.mzn mesh3x3_mp3_2.dzn ring_mp3.dzn"  --cplex-dll path/to/libcplexXXXX.so
```
## Hint
