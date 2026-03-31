@echo off
setlocal

call npm install
call npm run build

echo.
echo Build complete. Check the release folder.
pause
