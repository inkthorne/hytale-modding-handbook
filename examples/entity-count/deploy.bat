@echo off
call "%~dp0..\hytale-paths.bat"
set "MODS_DIR=%HYTALE_MODS_DIR%"
set "JAR_FILE=build\libs\example-entity-count.jar"

if not exist "%JAR_FILE%" (
    echo JAR not found. Building first...
    call gradlew.bat build
    if %ERRORLEVEL% NEQ 0 (
        echo Build failed!
                exit /b 1
    )
)

if not exist "%MODS_DIR%" (
    echo Creating mods directory...
    mkdir "%MODS_DIR%"
)

echo Deploying to %MODS_DIR%...
copy /Y "%JAR_FILE%" "%MODS_DIR%\"

if %ERRORLEVEL% EQU 0 (
    echo Deployed successfully!
) else (
    echo Deploy failed!
)
