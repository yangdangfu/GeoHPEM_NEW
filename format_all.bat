@echo off
setlocal enabledelayedexpansion

REM Get the current directory
set ROOT_DIR=%cd%

REM Set the target directory to the 'src' directory in the current directory
set TARGET_DIR=%ROOT_DIR%\src

REM Check if the 'src' directory exists
if not exist "%TARGET_DIR%" (
    echo The "src" directory does not exist.
    exit /b
)

REM Run isort to sort imports for all Python files in the 'src' directory and its subdirectories
echo Running isort on all Python files in "%TARGET_DIR%" and its subdirectories...
for /r "%TARGET_DIR%" %%f in (*.py) do (
    echo Sorting imports in: %%f
    isort "%%f"
)

REM Run black to format all Python files in the 'src' directory and its subdirectories
echo Running black on all Python files in "%TARGET_DIR%" and its subdirectories...
for /r "%TARGET_DIR%" %%f in (*.py) do (
    echo Formatting with black: %%f
    black "%%f"
)

echo Formatting complete!
pause
