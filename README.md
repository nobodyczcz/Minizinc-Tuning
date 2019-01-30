# Minizinc-Tuning

This is a Automatic parameter tunning program for Minizinc solvers. 

Currently support cplex, gurobi and osicbc and able to perform parameter tunning on multiple instances. The program use [SMAC v2.10.03](http://www.cs.ubc.ca/labs/beta/Projects/SMAC/) to perform parameter tunning.


## Requirement

1. Java (Tested on 8, not sure does it working on 9 or 10)

   SMAC2 is written in java.
   
2. Python 3.x

   This program is written in python. (At first we use SMAC3 in python, which require some dependencies only working on linux, but based on the consideration of cross-platform we move to SMAC2 in Java)

3. Minizinc
   
4. Working on linux, mac and windows

## Basic Usage
1. On default, the program will try to minimize the time cost ot obtain optimal solution. 

2. Go to the directory of your model files and data files

3. Use a command in following format to start tunning:

```
python Path/to/Minizinc-Tunning.py --solver [1.solver] -p [2.No.of threads] -t [3.time limit] -pcsJson [4.pcsfile path] [5.model and data] 
```
\[1]: Solver you want to use: cplex / gurobi / osicbc

\[2]: How many threads that minizinc use to solve the problem. 

Attention the prameter configration for certain amount processors may not work when using another processors setting. This means if you use -p 2 for parameter tunning, the tunning result may not improve the model solving speed if you run minizinc with -p 1. (-p is not necessary. If remove -p, it will use default value 1) You also can tune No. of threads, see details in Advanced part.

\[3]: Total time limit for tunning the program, unit is seconds.

The time limit should be enough for runing the model for at leat 80 times. If your models needs 300 seconds to solve the problem, it is suggested to tuning for more than 6 hours (21600 seconds). If you only tunning for 3 hours, it will also give you a improved parameter configuration, but may not as good as 6 hour result. It is suggested to make it run as long as possible. 

\[4]: The path to json parameter configuration space file. We provide two (osicbc.json, cplex.json) in our program folder.

\[5]: models and datas: "Model1.mzn data1.dzn data2.dzn" "Model2.mzn data21.dzn" "Model3.mzn data31.dzn data32.dzn data33.dzn ..." ....

If you are using cplex on linux， or minizinc don't known where is cplex, add --cplex-dll \[6.dll file path] to the end of command. \[6.dll file path] is the path of cplex dll/so file. Remove it if you are using osicbc or gurobi


### For example:

#### For the mapping.mzn model in example directory
```
python Path/to/your/tuning program/Minizinc-Tunning.py --solver cplex -p 2 -t 3600 -pcsJson path/to/cplex.json "mapping.mzn mesh3x3_mp3_2.dzn ring_mp3.dzn"  --cplex-dll path/to/libcplexXXXX.so
```
## Advanced

### Optimize objective within limited time

**--obj-mode**

If your model is hard to achieve a optimal solution in reasonable time. You can use this argument to optimize the objective of solution within limited time. *Remember to use -c \[cut off time] to set time limit*

On default it try to minimize objective

For maximization problem, use

**--maximize** 

to indeticate that this is a maximization problem

### Parallel Tuning

**-psmac \[No. of smac]**

SMAC support parallel search and tunning. SMACs will share their data to biuld model. If your computer have enough CPU resource, use this to achieve better solution. For cpu with 8 threads, if you run minizinc with -p 1, you can use -psmac 6. If minizinc use -p 2 , you can try -psmac 3. Do not use all aviable threads, as cpus are not only used by minizinc and smac. 

### Tuning threads

**--tune-threads**

With this argument, the program will treat threads as one of parameter for tunning. -p \[No. of threads] will be treat as maximum threats available and default threats setting.

## Other option

**-c**

Set cut off time for each minizinc run manualy
