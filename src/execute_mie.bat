echo start execution...please don't close this window before finish   

:: @echo off
:: get current path which should be path to dropbox
SET cur_path="%~dp0"

SET my_path="C:\Users\Christina Zavou\Desktop"
SET alternative_path="C:\Users\ChristinaZ\Desktop"

if not exist %my_path% (
	cd %alternative_path%
) else (
	cd %my_path%
)

RD /S /Q "Medical_Information_Extraction" 
git clone https://github.com/christinazavou/Medical_Information_Extraction.git

SET destination_folder="results_test"
SET destination_file="exec_out.txt"
call :joinpath %cur_path% %destination_folder%
SET destination_path=%Result%
if not exist %destination_path% mkdir %destination_path%

call :joinpath %destination_path% %destination_file%
SET outputfile=%Result%

python Medical_Information_Extraction\src\execute_configurations.py %destination_path% 
::> %outputfile%

echo thanks for waiting. execution finished. you can close the window. 
pause
goto :EOF



:joinpath
set Path1=%~1
set Path2=%~2
if {%Path1:~-1,1%}=={\} (set Result=%Path1%%Path2%) else (set Result=%Path1%\%Path2%)
goto :eof