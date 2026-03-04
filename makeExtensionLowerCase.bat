:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Brief:	Make extensions of all files in folder lower case.
:: Author:	Jan Blumenthal (eagleeis@gmx.de)
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
@echo off

:: Check PYTHON_HOME and define, if necessary
if not defined PYTHON_HOME (
	set "PYTHON_HOME=c:\Tools\Python\3.13.1"
)

set "MAKELIST=%~dp0\makeList.py"

:: Change drive and current directory
cd /d %1

:: Remove quotation marks and trailing backslash
set "SRCDIR=%~1"
set "SRCDIR=%SRCDIR:~0,-1%"
set "DESTDIR=%SRCDIR%\excluded"

echo Path to makeList.py   : %MAKELIST%
echo Scanning directory    : %SRCDIR%
echo Destination directory : %DESTDIR%
echo.

echo Convert all extensions of files in folder "%SRCDIR%" to lower case.
%PYTHON_HOME%\python.exe "%MAKELIST%" -a -v --os="utils.covertCaseOfFile( filePath, None, 0 )"

pause
