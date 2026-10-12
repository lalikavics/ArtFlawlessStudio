@echo off
rem Builds Output\ArtFlawlessStudio-Setup-<VERSION>.exe
rem Needs: Python 3 (https://www.python.org) and Inno Setup 6.3+ (https://jrsoftware.org/isdl.php)
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
%PY% make_studio_files.py || goto :fail
%PY% make_families.py || goto :fail
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run build.bat again.
  goto :fail
)
"%ISCC%" ArtFlawlessStudio.iss || goto :fail
echo.
echo Done: see the Output folder.
pause
exit /b 0
:fail
echo.
echo The build failed - see the messages above.
pause
exit /b 1
