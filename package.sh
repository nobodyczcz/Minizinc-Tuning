#!/bin/bash
minizincPath=`which minizinc`
minizincPath=${minizincPath//"bin/minizinc"/}
if [ -z $minizincPath ]
then
echo "Can't find Minizinc folder in path enviroment."
echo "Please input the path to Minizinc folder"
read minizincPath
else
echo find minizinc path : $minizincPath
fi

pyinstaller ./wrappers.py
echo wrappers done

pyinstaller Minizinc-Tuning.py
echo tuning done
mv ./dist/wrappers ./dist/Minizinc-Tuning/
echo move wrappers done
cp -r --copy-contents example ./dist/Minizinc-Tuning/
echo move example done
cp -r --copy-contents pcsFiles ./dist/Minizinc-Tuning/
echo move pcsFiles done
cp -r --copy-contents smac-v2 ./dist/Minizinc-Tuning/
echo move smac-v2 done
mkdir ./dist/Minizinc-Tuning/cache
echo create cache

cp -r --copy-contents ./dist/Minizinc-Tuning $minizincPath/share/minizinc/solvers/
cp ./minizinc-tuning.msc $minizincPath/share/minizinc/solvers/
echo move to $minizincPath/share/minizinc/solvers/ done

chmod u+x $minizincPath/share/minizinc/solvers/Minizinc-Tuning/Minizinc-Tuning
chmod u+x $minizincPath/share/minizinc/solvers/Minizinc-Tuning/MinizincTuning/wrappers/wrappers
chmod u+x $minizincPath/share/minizinc/solvers/Minizinc-Tuning/smac-v2/smac

echo set executable done
echo setup finish


