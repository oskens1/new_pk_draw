@echo off
cd /d "%~dp0"
%USERPROFILE%\anaconda3\python.exe -m pip install pypdf -q
%USERPROFILE%\anaconda3\python.exe split_pdf.py
pause
