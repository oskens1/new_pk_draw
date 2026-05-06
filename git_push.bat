@echo off
cd /d "%~dp0"
for /f "tokens=1-5 delims=/ " %%a in ("%date%") do set D=%%a/%%b/%%c
for /f "tokens=1-2 delims=:" %%a in ("%time%") do set T=%%a:%%b
git add .
git commit -m "Update %D% %T%"
git push origin main
pause
