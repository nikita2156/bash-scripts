@echo off
chcp 65001 >nul
echo ============================================
echo SSH Tunnel Creator - Сборка для Windows
echo ============================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден в системе!
    echo Установите Python с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Установка зависимостей...
pip install -r requirements.txt pyinstaller

echo [2/3] Создание исполняемого файла...
pyinstaller --onefile --windowed --name "SSH_Tunnel_Creator" ^
    --add-data "requirements.txt;." ^
    ssh_tunnel_app.py

echo [3/3] Копирование файлов...
if exist "dist\SSH_Tunnel_Creator.exe" (
    echo.
    echo ============================================
    echo Сборка завершена успешно!
    echo Исполняемый файл: dist\SSH_Tunnel_Creator.exe
    echo ============================================
) else (
    echo ОШИБКА: Не удалось создать исполняемый файл
)

pause
