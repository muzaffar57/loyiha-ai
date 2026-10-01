@echo off
cd /d "%~dp0"
python desktop.py && goto :ok
py -3 desktop.py && goto :ok
echo.
echo Python topilmadi. python.org dan Python 3 o'rnating (tkinter bilan keladi).
pause
exit /b 1
:ok
