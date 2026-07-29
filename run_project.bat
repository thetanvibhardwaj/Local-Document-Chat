@echo off
title Cognify Docs Launcher
echo ============================================================
echo           COGNIFY DOCS - RUNNER & INSTALLATION
echo ============================================================
echo.

:: 1. Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on your system PATH.
    echo Please download and install Python (3.9 - 3.11 recommended) and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Setup Virtual Environment
if not exist "venv" (
    echo [INFO] Python virtual environment (venv) not found. Creating it...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
    echo.
)

:: 3. Activate venv & Install dependencies
echo [INFO] Activating virtual environment...
call venv\Scripts\activate

echo [INFO] Installing required python libraries from requirements.txt...
echo This may take a minute or two on first run. Please wait...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies. Check your network connection.
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed successfully.
echo.

:: 4. Verify .env configuration
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env file from template...
        copy .env.example .env >nul
    ) else (
        echo [WARNING] .env.example template not found.
    )
)

:: Check if GEMINI_API_KEY is configured
findstr /C:"GEMINI_API_KEY=" .env >nul
if %errorlevel% eq 0 (
    :: Read key value
    for /f "tokens=2 delims==" %%A in ('findstr /C:"GEMINI_API_KEY=" .env') do set KEY_VAL=%%A
    if "%KEY_VAL%"=="" (
        echo [IMPORTANT] Google Gemini API Key is missing in your .env file!
        echo Please open the '.env' file in this folder and add your key:
        echo GEMINI_API_KEY=AIzaSy...
        echo.
        echo RAG question-answering will return error warnings until the key is added.
        echo.
    )
)

:: 5. Launch Backend in a new window
echo [INFO] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start cmd /k "title Cognify Docs API Server && call venv\Scripts\activate && python backend/main.py"

:: 6. Launch Frontend
echo [INFO] Launching Streamlit Frontend...
streamlit run frontend/app.py

echo.
echo ============================================================
echo Processes started. If browser doesn't open automatically, visit:
echo API Server:  http://127.0.0.1:8000/docs
echo Web Client:  http://localhost:8501
echo ============================================================
echo.
pause
