@echo off
cd /d "%~dp0"
py -3 start_pixora.py %*
if errorlevel 1 pause
