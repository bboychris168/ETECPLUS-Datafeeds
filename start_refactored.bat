@echo off
echo 🏢 Starting ETEC+ Datafeeds (Refactored Version)
echo ================================================
echo.
echo 🔍 Checking if code loads correctly...
python -c "from main import ETECDatafeedsApp; print('✅ Code verified!')"
if %errorlevel% neq 0 (
    echo ❌ Code check failed!
    pause
    exit /b 1
)
echo.
echo 🚀 Starting Streamlit application...
echo 📱 Your browser should open automatically to: http://localhost:8501
echo 💡 To stop the application, press Ctrl+C
echo.
streamlit run main.py
pause