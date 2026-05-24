@echo off
cd /d "%~dp0"
if not exist "input" mkdir input
if not exist "output" mkdir output

set AUDIO=
for %%f in (input\*.mp3 input\*.wav input\*.m4a) do (
    if "!AUDIO!"=="" set "AUDIO=%%f"
)

if "%AUDIO%"=="" (
    echo No audio file found in input folder.
    pause
    exit /b 1
)

py -3.12 main.py "%AUDIO%" %*

pause
