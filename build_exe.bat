@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --name ListenerAssistant main.py

echo.
echo Build complete. Check dist\ListenerAssistant.exe
pause
