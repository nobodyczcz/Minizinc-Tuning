import os
import sys
import json
import stat
from subprocess import run, PIPE


def main():
    cmd = ['minizinc','--solvers']

    output = None
    try:
        output = run(cmd,stdout=PIPE,stderr=PIPE)
    except FileNotFoundError:
        print("[Error] Can't find Minizinc. Please ensure Minizinc is intalled")
        return

    if output is not None:
        result = output.stdout.decode("utf-8")
    else:
        print("[Error] No solver folder found")
        return

    store = False
    result = result.splitlines()
    index = result.index("Search path for solver configurations:")
    paths = result[index+1:]

    done = False

    if getattr(sys, 'frozen', False):
        # we are running in a bundle
        programPath = sys.executable
        programPath = os.path.dirname(programPath)
    else:
        # we are running in a normal Python environment
        programPath = os.path.dirname(os.path.abspath(__file__))

    if os.name == 'nt':
        exeName = "Minizinc-Tuning.exe"
    else:
        exeName = "Minizinc-Tuning"

    for i in paths:
        i=i.strip()
        if not os.path.exists(i):
            print(i," not exist, try to create")
            try:
                os.mkdir(i)
            except:
                print("can't mkdir, try next one")
                continue
        if os.access(i,os.W_OK):
            with open("minizinc-tuning.msc","r") as f:
                data = json.load(f)


            data["executable"] = os.path.join(programPath,exeName)
            print("Writing minizinc-tuning.msc to :", i)
            with open(os.path.join(i,"minizinc-tuning.msc"),"w") as f:
                f.write(json.dumps(data,indent=4))
            done = True
            break
        else:
            print("can't access ", i)

    if not done:
        print("[Error] Can not access: \n","\n".join(paths))
        print("Please copy minizinc-tuning.msc to any of these folder manually")
    else:
        print("Moving and Editing minizinc-tuning.msc successful")

    if os.name != 'nt' and programPath is not None:
        if getattr(sys, 'frozen', False):
            exePath = os.path.join(programPath,'Minizinc-Tuning')
        else:
            exePath = os.path.join(programPath, 'Minizinc-Tuning.py')
        st = os.stat(exePath)
        os.chmod(exePath, st.st_mode | stat.S_IEXEC)

        if getattr(sys, 'frozen', False):
            wrapperPath = os.path.join(programPath,'wrappers')
            wrapperPath = os.path.join(wrapperPath,'wrappers')
        else:
            wrapperPath = os.path.join(programPath, 'wrappers.py')
        st = os.stat(wrapperPath)
        os.chmod(wrapperPath, st.st_mode | stat.S_IEXEC)

        smacPath = os.path.join(programPath,'smac-v2')
        smacPath = os.path.join(smacPath, 'smac')
        st = os.stat(smacPath)
        os.chmod(smacPath, st.st_mode | stat.S_IEXEC)
        print("Chmod successful")
    print("Setup done, Minizinc should be able to find tuning-program now")
    input("Enter anything to exit:")

if __name__=="__main__":
    main()
