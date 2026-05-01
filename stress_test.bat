@echo off
cd /d "%~dp0"
%USERPROFILE%\anaconda3\python.exe -m pip install requests -q
%USERPROFILE%\anaconda3\python.exe stress_test.py
pause
