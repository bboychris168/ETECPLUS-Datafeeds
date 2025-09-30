#!/usr/bin/env python3
"""
Quick deployment script for the refactored ETEC+ Datafeeds application.
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required packages are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = ['streamlit', 'pandas', 'openpyxl', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
        print("✅ Dependencies installed!")
    else:
        print("✅ All dependencies satisfied!")
    
    return True

def run_tests():
    """Run the test suite."""
    print("\n🧪 Running tests...")
    result = subprocess.run([sys.executable, 'test_refactored.py'], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ Tests failed:\n{result.stdout}\n{result.stderr}")
        return False

def start_application():
    """Start the Streamlit application."""
    print("\n🚀 Starting ETEC+ Datafeeds (Refactored)...")
    print("📱 The application will open in your browser automatically.")
    print("🔗 If it doesn't open, visit: http://localhost:8501")
    print("\n💡 To stop the application, press Ctrl+C in this terminal")
    print("=" * 60)
    
    try:
        subprocess.run(['streamlit', 'run', 'main.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Streamlit: {e}")
        print("💡 Try running manually: streamlit run main.py")
        return False
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        return True

def main():
    """Main deployment function."""
    print("🏢 ETEC+ Datafeeds - Refactored Deployment")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('main.py'):
        print("❌ main.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    try:
        # Step 1: Check dependencies
        check_dependencies()
        
        # Step 2: Run tests
        if not run_tests():
            print("⚠️  Tests failed, but you can still run the application.")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("👋 Deployment cancelled")
                sys.exit(1)
        
        # Step 3: Start application
        start_application()
        
    except KeyboardInterrupt:
        print("\n👋 Deployment cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()