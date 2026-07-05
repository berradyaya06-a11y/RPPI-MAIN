#!/bin/bash
# setup_mac.sh — One-click Mac setup for RPPI Maroc project
# Run: chmod +x setup_mac.sh && ./setup_mac.sh

echo "╔══════════════════════════════════════════╗"
echo "║   RPPI Maroc — Mac Setup                 ║"
echo "╚══════════════════════════════════════════╝"

# 1. Create virtual environment
echo "\n1. Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
echo "\n2. Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Install Playwright browser
echo "\n3. Installing Playwright browser (optional)..."
python -m playwright install chromium

# 4. Create .env
echo "\n4. Creating .env file..."
cp .env.example .env

# 5. Create __init__.py files
echo "\n5. Creating package init files..."
touch ingestion/__init__.py
touch ingestion/scrapers/__init__.py
touch processing/__init__.py
touch database/__init__.py
touch analytics/__init__.py
touch analytics/eda/__init__.py
touch analytics/hedonic/__init__.py
touch analytics/index/__init__.py
touch analytics/spatial/__init__.py
touch analytics/validation/__init__.py
touch analytics/bias/__init__.py
touch dashboard/__init__.py
touch utils/__init__.py
touch config/__init__.py
touch ml/__init__.py
touch tests/__init__.py

# 6. Initialize database
echo "\n6. Initializing database..."
python -c "from database.models import init_db; init_db()"

echo "\n╔══════════════════════════════════════════╗"
echo "║   ✅ Setup complete!                      ║"
echo "║                                           ║"
echo "║   Next steps:                             ║"
echo "║   source venv/bin/activate                ║"
echo "║   python main.py --ingest                 ║"
echo "║   python main.py --clean                  ║"
echo "║   python main.py --eda                    ║"
echo "║   python main.py --hedonic                ║"
echo "║   python main.py --dashboard              ║"
echo "╚══════════════════════════════════════════╝"
