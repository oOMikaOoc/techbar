@echo off

REM === Configuration ===
set TECHBAR_DIR=%~dp0
set ZEBAR_TARGET=C:\Users\%USERNAME%\.glzr\zebar\techbar\techbar\jzone.json

echo.
echo [Techbar] Generation en cours...

cd /d %TECHBAR_DIR%

python generate_jzone.py
if %errorlevel% neq 0 (
    echo [ERREUR] Echec de la generation
    pause
    exit /b
)

echo [Techbar] Copie vers Zebar...
copy /y "%TECHBAR_DIR%jzone.json" "%ZEBAR_TARGET%"

echo [Techbar] Termine !
pause