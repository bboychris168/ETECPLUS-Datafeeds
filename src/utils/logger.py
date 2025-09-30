"""
Logging utilities for ETEC+ Datafeeds application.
Provides structured logging with file output and UTF-8 encoding.
"""

import logging
import os
from datetime import datetime
from io import StringIO
from typing import Optional


class AppLogger:
    """Manages application logging with file output."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.log_folder = os.path.join(base_path, "logs")
        self.log_file: Optional[str] = None
        self.setup_logging()
    
    def setup_logging(self) -> str:
        """Setup logging to capture debug information to file."""
        os.makedirs(self.log_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_folder, f"datafeed_processing_{timestamp}.log")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(StringIO())  # Capture to string for download
            ]
        )
        
        return self.log_file
    
    def info(self, message: str) -> str:
        """Log info message."""
        logging.info(message)
        return message
    
    def warning(self, message: str) -> str:
        """Log warning message."""
        logging.warning(message)
        return message
    
    def error(self, message: str) -> str:
        """Log error message."""
        logging.error(message)
        return message
    
    def write(self, message: str) -> str:
        """Log message (equivalent to st.write but logged)."""
        logging.info(message)
        return message
    
    def get_log_file_path(self) -> Optional[str]:
        """Get the current log file path."""
        return self.log_file
    
    def get_log_file_size(self) -> int:
        """Get the size of the current log file in bytes."""
        if self.log_file and os.path.exists(self.log_file):
            return os.path.getsize(self.log_file)
        return 0
    
    def read_log_file(self) -> str:
        """Read the contents of the current log file."""
        if self.log_file and os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return f.read()
        return ""