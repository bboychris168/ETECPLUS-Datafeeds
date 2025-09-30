"""
File handling utilities for ETEC+ Datafeeds application.
Handles reading, writing, and processing of various file formats.
"""

import pandas as pd
import requests
import os
from datetime import datetime
from typing import Optional, List, Tuple, Any, Dict
import streamlit as st
from io import BytesIO


def read_file(file: Any) -> Optional[pd.DataFrame]:
    """Read CSV or Excel file."""
    try:
        file.seek(0)
        if file.name.endswith('.csv'):
            # Try different delimiters
            for delimiter in [',', ';', '\t']:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, delimiter=delimiter, low_memory=False)
                    if len(df.columns) > 1:
                        return df
                except:
                    continue
        else:
            return pd.read_excel(file)
        return None
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None


def extract_shopify_columns(file: Any) -> Optional[List[str]]:
    """Extract column headers from uploaded Shopify CSV template."""
    try:
        file.seek(0)
        if file.name.endswith('.csv'):
            # Try different delimiters
            for delimiter in [',', ';', '\t']:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, delimiter=delimiter, nrows=0, low_memory=False)  # Just get headers
                    if len(df.columns) > 5:  # Reasonable number of columns for Shopify
                        return list(df.columns)
                except:
                    continue
        else:
            df = pd.read_excel(file, nrows=0)  # Just get headers
            return list(df.columns)
        return None
    except Exception as e:
        st.error(f"Error reading Shopify template: {str(e)}")
        return None


def detect_supplier(filename: str) -> Optional[str]:
    """Detect supplier from filename."""
    filename = filename.lower()
    
    # Common patterns
    patterns = {
        'auscomp': ['auscomp'],
        'compuworld': ['compuworld'],
        'leader_systems': ['leader', 'leadersystem'],
        'dicker': ['dicker'],
        'synnex': ['synnex'],
        'ingram': ['ingram'],
        'techdata': ['techdata']
    }
    
    for supplier, keywords in patterns.items():
        for keyword in keywords:
            if keyword in filename:
                return supplier
    return None


def download_supplier_file(url: str, filename: str, output_dir: str = "suppliers") -> Tuple[bool, str]:
    """Download a single supplier file."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    
    try:
        # Add user agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save to file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        return True, f"Downloaded to {file_path}"
        
    except requests.exceptions.RequestException as e:
        return False, f"Download failed - {str(e)}"
    except Exception as e:
        return False, f"Error - {str(e)}"


def load_files_from_suppliers_folder(folder_path: str = "suppliers") -> List[Tuple[str, str]]:
    """Load available files from suppliers folder."""
    if not os.path.exists(folder_path):
        return []
    
    files = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            file_path = os.path.join(folder_path, filename)
            # Get file modification time for display
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            display_name = f"{filename} (Updated: {mod_time.strftime('%Y-%m-%d %H:%M')})"
            files.append((file_path, display_name))
    
    return files


def create_file_from_path(file_path: str) -> Optional[BytesIO]:
    """Create a file-like object from a file path."""
    try:
        with open(file_path, 'rb') as f:
            file_content = BytesIO(f.read())
            file_content.name = os.path.basename(file_path)
            return file_content
    except Exception:
        return None