@echo off
echo ============================================
echo   RPPI Maroc - Windows Setup
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo [OK] Python found
python --version

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)
echo [OK] Virtual environment created

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install requirements
echo.
echo Installing dependencies (this takes 2-3 minutes)...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Install Playwright browser
echo.
echo Installing Playwright browser...
python -m playwright install chromium
echo [OK] Browser installed

REM Create .env file
echo.
if not exist .env (
    copy .env.example .env >nul
    echo [OK] .env file created
) else (
    echo [OK] .env file already exists
)

REM Create __init__.py files
echo.
echo Creating package files...
type nul > ingestion\__init__.py
type nul > ingestion\scrapers\__init__.py
type nul > processing\__init__.py
type nul > database\__init__.py
type nul > analytics\__init__.py
type nul > analytics\eda\__init__.py
type nul > analytics\hedonic\__init__.py
type nul > analytics\index\__init__.py
type nul > analytics\spatial\__init__.py
type nul > analytics\validation\__init__.py
type nul > analytics\bias\__init__.py
type nul > dashboard\__init__.py
type nul > utils\__init__.py
type nul > config\__init__.py
type nul > ml\__init__.py
type nul > tests\__init__.py
echo [OK] Package files created

REM Initialize database
echo.
echo Initializing database...
python -c "from database.models import init_db; init_db()"
if %errorlevel% neq 0 (
    echo [ERROR] Database init failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo Next steps - run these commands one by one:
echo.
echo   venv\Scripts\activate
echo   python main.py --ingest
echo   python main.py --clean
echo   python main.py --eda
echo   python main.py --hedonic
echo   python main.py --dashboard
echo.
echo Then open: http://localhost:8501
echo.
pause

