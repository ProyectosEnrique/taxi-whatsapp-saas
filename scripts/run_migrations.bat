@echo off
echo ========================================
echo EJECUTANDO MIGRACIONES DE BASE DE DATOS
echo ========================================
echo.

cd /d "%~dp0\.."

python scripts\run_migrations.py

pause
