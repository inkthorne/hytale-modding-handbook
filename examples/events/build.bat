@echo off
echo Building example-entity-count plugin...
call ./gradlew.bat build
if %ERRORLEVEL% EQU 0 (
    echo Build successful! JAR located at: build\libs\example-entity-count.jar
) else (
    echo Build failed!
)
