@echo off
cd /d "%~dp0"
start /min powershell -STA -ExecutionPolicy Bypass -File "%~dp0start.ps1"
