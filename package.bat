c:\Users\czcz2\Anaconda3\Scripts\pyinstaller.exe Minizinc-Tuning.py
c:\Users\czcz2\Anaconda3\Scripts\pyinstaller.exe wrappers.py
echo pyinstaller done

move .\dist\wrappers .\dist\Minizinc-Tuning\
echo move wrappers done

MKDIR .\dist\Minizinc-Tuning\example\
xcopy /s example .\dist\Minizinc-Tuning\example\
echo move example done

MKDIR .\dist\Minizinc-Tuning\pcsFiles\
xcopy /s pcsFiles .\dist\Minizinc-Tuning\pcsFiles\
echo move pcsFiles done

MKDIR .\dist\Minizinc-Tuning\smac-v2\
xcopy /s smac-v2 .\dist\Minizinc-Tuning\smac-v2\
echo move smac-v2 done

MKDIR .\dist\Minizinc-Tuning\cache
echo create cache

set /p delBuild=press any key to exit?: 
