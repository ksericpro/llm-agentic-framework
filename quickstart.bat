@echo off
REM Quick Start Script for LangChain Agentic Pipeline
REM Windows Batch Script

echo ================================================================================
echo LangChain Agentic Pipeline - Quick Start
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Checking Python installation...
python --version
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    echo Virtual environment created!
) else (
    echo [2/5] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [4/5] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully!
echo.

REM Check if .env exists
if not exist ".env" (
    echo [5/5] Setting up environment variables...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env file and add your API keys:
    echo   - OPENAI_API_KEY
    echo   - TAVILY_API_KEY (optional, for web search)
    echo.
    echo Opening .env file in notepad...
    timeout /t 2 >nul
    notepad .env
) else (
    echo [5/5] .env file already exists
)
echo.

REM Run setup verification
echo ================================================================================
echo Running setup verification...
echo ================================================================================
echo.
python test_setup.py
if errorlevel 1 (
    echo.
    echo Setup verification failed. Please fix the issues above.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Setup Complete! You can now:
echo ================================================================================
echo.
echo 1. Start the API server:
echo    python api.py
echo.
echo 2. Or use uvicorn (recommended):
echo    uvicorn api:app --reload --port 8000
echo.
echo 3. Test with example client:
echo    python example_client.py
echo.
echo 4. View API docs:
echo    http://localhost:8000/docs
echo.
echo ================================================================================
echo.

REM Ask if user wants to start the server
set /p start_server="Do you want to start the API server now? (y/n): "
if /i "%start_server%"=="y" (
    echo.
    echo Starting API server...
    echo Press Ctrl+C to stop the server
    echo.
    python api.py
)

pause
