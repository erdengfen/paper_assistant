@echo off
chcp 65001 >nul
echo [INFO] Startup script: Auto-configure virtual environment and run gradio_app.py

cd /d %~dp0
echo [INFO] Current directory: %cd%

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not detected. Please install Python and add it to PATH!
    pause
    exit /b
)

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating...
    python -m venv .venv

    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Please check your Python installation.
        pause
        exit /b
    )

    echo [INFO] Virtual environment created. Activating and installing dependencies...
    call .venv\Scripts\activate

    if exist requirements.txt (
        echo [INFO] requirements.txt found. Installing dependencies...
        pip install --upgrade pip
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [ERROR] Failed to install dependencies. Please check requirements.txt.
            pause
            exit /b
        )
    ) else (
        echo [WARNING] requirements.txt not found. Skipping dependency installation.
    )
) else (
    echo [INFO] Virtual environment found. Activating...
    call .venv\Scripts\activate
)

echo [INFO] Running gradio_app.py...
python gradio_app.py

echo [INFO] Program finished.
pause
