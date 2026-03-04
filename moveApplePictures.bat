:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Brief:	Move apple pictures from folder "%SRCDIR%" to "%DESTDIR%" but
::			each picture only once (extended or orginal[4:3])
::			Note:	This script must only be called once because next turn
::					would move original pictures since extended were moved
::					in first run!
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
::echo Note: Inverse Selection activated.

IF NOT EXIST "%DESTDIR%" (
	echo Convert all file names to lower case
	%PYTHON_HOME%\python.exe "%MAKELIST%" -a -v --os="utils.covertCaseOfFile( filePath, 0, 0 )"
	echo.
	echo Call specific script to move "original" Apple pics to folder: %DESTDIR%
	%PYTHON_HOME%\python.exe "%MAKELIST%" -a -d=%SRCDIR% --is="import toolsPictures;tp=toolsPictures.ApplePictureTools(makeList)" --filterSnippet="tp.checkIPhonePicture(curDir,filePath,inverseSelection=True)" --os="utils.moveFile(filePath,os.path.join(r'%DESTDIR%', os.path.basename(filePath)),overwrite=False)" --ip -v --noSubDirs --fmtAllSubEntries=""
) ELSE (
	echo ERROR! Destination directory "%DESTDIR%" already exists. Script already executed?
)

pause
