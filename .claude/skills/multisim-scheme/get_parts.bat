@echo off
rem Get missing parts (run on the PC with Multisim; close the Multisim window first).
rem Claude writes donors_request.txt (next to this file) -> Multisim replaces template placeholders with the requested
rem parts (scripts\donors.vbs, COM ReplaceComponent) -> scripts\harvest.py adds them to samples\ni (old parts are kept).
rem If the skill is inside a git repository: git pull before, git push after (the catalog goes to Claude).
cd /d "%~dp0"
rem Python 3: "python" or the launcher "py"; Multisim COM is 32-bit - the 32-bit script host is needed
set PY=python
python --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || (echo ERROR - Python 3 not found: install it from python.org ^(tick "Add to PATH"^) & goto fail)
set CS=C:\Windows\SysWOW64\cscript.exe
if not exist %CS% set CS=C:\Windows\System32\cscript.exe
set INGIT=0
git rev-parse --is-inside-work-tree >nul 2>&1 && set INGIT=1
if %INGIT%==1 git pull
if exist donors_new rmdir /s /q donors_new
echo Multisim: replacing placeholders (may take a few minutes)...
%CS% //nologo scripts\donors.vbs donors_request.txt donors_new > donors_log.txt 2>&1
type donors_log.txt
%PY% scripts\harvest.py donors_new --keep -o samples\ni
if errorlevel 1 goto fail
copy /y donors_log.txt samples\ni\donors_log.txt > nul
if %INGIT%==0 goto nogit
git add samples\ni
git commit -m "Donors: parts from donors_request.txt"
git push
if errorlevel 1 goto fail
echo.
echo DONE - tell Claude that the parts are pushed.
pause
exit /b 0
:nogit
echo.
echo DONE - send Claude the files from the donors_new folder and samples\ni\donors_log.txt
echo (or zip the skill folder again and upload it).
pause
exit /b 0
:fail
echo.
echo ERROR - send the text above to Claude.
pause
exit /b 1
