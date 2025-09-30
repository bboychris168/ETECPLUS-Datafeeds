#!/usr/bin/env python3
"""
Test script for the refactored ETEC+ Datafeeds application.
This verifies that all modules can be imported and key functions work.
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported successfully."""
    print("🧪 Testing module imports...")
    
    try:
        # Test core modules
        from src.core.data_processing import extract_quantity, convert_weight_to_grams, truncate_title
        from src.core.file_handler import detect_supplier
        from src.core.processor import DataProcessor
        
        # Test utils
        from src.utils.config import ConfigManager
        from src.utils.logger import AppLogger
        
        # Test data managers
        from src.data.manager import SupplierManager, QuotingManager
        
        # Test UI components
        from src.ui.styling import configure_page, apply_custom_css
        from src.ui.components import ShopifyTemplateTab, UploadTab, MappingTab
        
        # Test main app
        from main import ETECDatafeedsApp
        
        print("✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_core_functions():
    """Test core data processing functions."""
    print("\n🧪 Testing core functions...")
    
    from src.core.data_processing import extract_quantity, convert_weight_to_grams, truncate_title
    from src.core.file_handler import detect_supplier
    
    # Test quantity extraction
    assert extract_quantity("5") == 5
    assert extract_quantity("IN STOCK") == 999
    assert extract_quantity("OUT OF STOCK") == 0
    print("✅ Quantity extraction working")
    
    # Test weight conversion
    assert convert_weight_to_grams("1.5") == 1500
    assert convert_weight_to_grams("0.5") == 500
    assert convert_weight_to_grams("") == 0
    print("✅ Weight conversion working")
    
    # Test title truncation
    long_title = "A" * 300
    truncated = truncate_title(long_title, 255)
    assert len(truncated) <= 255
    assert truncated.endswith("...")
    print("✅ Title truncation working")
    
    # Test supplier detection
    assert detect_supplier("auscomp_datafeed.csv") == "auscomp"
    assert detect_supplier("compuworld_products.xlsx") == "compuworld"
    assert detect_supplier("unknown_file.csv") is None
    print("✅ Supplier detection working")

def test_config_manager():
    """Test configuration management."""
    print("\n🧪 Testing configuration manager...")
    
    from src.utils.config import ConfigManager
    
    config_mgr = ConfigManager()
    
    # Test basic functionality (doesn't require files to exist)
    shopify_template = config_mgr.load_shopify_template()
    assert isinstance(shopify_template, list)
    
    mappings = config_mgr.load_mappings()
    assert isinstance(mappings, dict)
    
    supplier_config = config_mgr.load_supplier_config()
    assert isinstance(supplier_config, dict)
    
    print("✅ Configuration manager working")

def test_logger():
    """Test logging functionality."""
    print("\n🧪 Testing logger...")
    
    from src.utils.logger import AppLogger
    
    logger = AppLogger()
    
    # Test logging methods
    message = logger.info("Test info message")
    assert message == "Test info message"
    
    warning = logger.warning("Test warning")
    assert warning == "Test warning"
    
    # Test log file creation
    log_file = logger.get_log_file_path()
    assert log_file is not None
    assert log_file.endswith(".log")
    
    print("✅ Logger working")

def test_application_class():
    """Test the main application class."""
    print("\n🧪 Testing application class...")
    
    # Note: This will produce Streamlit warnings when run outside streamlit run
    # but should still work for testing the class structure
    import warnings
    warnings.filterwarnings("ignore")
    
    from main import ETECDatafeedsApp
    
    app = ETECDatafeedsApp()
    
    # Verify key components exist
    assert hasattr(app, 'config_manager')
    assert hasattr(app, 'logger')
    assert hasattr(app, 'data_processor')
    assert hasattr(app, 'supplier_manager')
    assert hasattr(app, 'quoting_manager')
    
    print("✅ Application class structure working")

def main():
    """Run all tests."""
    print("🚀 Starting ETEC+ Datafeeds Refactored Tests\n")
    
    tests = [
        test_imports,
        test_core_functions,
        test_config_manager,
        test_logger,
        test_application_class,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The refactored application is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)