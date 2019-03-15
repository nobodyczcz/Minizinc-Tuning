#!/bin/bash

pyinstaller ./wrappers.py
echo wrappers done

pyinstaller Minizinc-Tuning.py
echo tuning done

pyinstaller -F setup.py
echo setup done

mv ./dist/wrappers ./dist/Minizinc-Tuning/
echo move wrappers done

mv ./dist/setup ./dist/Minizinc-Tuning/
echo move setup done

cp -R example ./dist/Minizinc-Tuning/
echo move example done
cp -R pcsFiles ./dist/Minizinc-Tuning/
echo move pcsFiles done
cp -R smac-v2 ./dist/Minizinc-Tuning/
echo move smac-v2 done
mkdir ./dist/Minizinc-Tuning/cache
echo create cache

cp ./tuningConfiguration.json ./dist/Minizinc-Tuning/
cp ./minizinc-tuning.msc ./dist/Minizinc-Tuning/
echo move setup and configuration dome

chmod u+x ./dist/Minizinc-Tuning/Minizinc-Tuning
chmod u+x ./dist/Minizinc-Tuning/wrappers/wrappers
chmod u+x ./dist/Minizinc-Tuning/smac-v2/smac

echo set executable done
echo setup finish

