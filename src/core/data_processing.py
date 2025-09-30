"""
Data processing utilities for ETEC+ Datafeeds application.
Handles data transformation, validation, and formatting.
"""

import pandas as pd
import re
from typing import Any, Union, List


def extract_quantity(qty_str: Any) -> int:
    """Extract quantity from string representation."""
    if pd.isna(qty_str) or qty_str == '':
        return 0
    
    qty_str = str(qty_str).strip().upper()
    
    if qty_str in ['IN STOCK', 'AVAILABLE', 'YES']:
        return 999
    if qty_str in ['OUT OF STOCK', 'NO', 'DISCONTINUED']:
        return 0
    
    match = re.search(r'(\d+)', qty_str)
    return int(match.group(1)) if match else 0


def convert_weight_to_grams(weight_str: Any) -> int:
    """Convert weight string to grams - simple x1000 conversion for kg to grams."""
    if pd.isna(weight_str) or weight_str == '':
        return 0
    
    weight_str = str(weight_str).strip()
    
    # Extract just the numeric value
    try:
        # Remove any non-numeric characters except decimal point
        clean_weight = re.sub(r'[^\d.]', '', weight_str)
        if clean_weight:
            weight_value = float(clean_weight)
            # Simple conversion: multiply by 1000 to convert kg to grams
            return int(round(weight_value * 1000))
        else:
            return 0
    except (ValueError, TypeError):
        return 0


def truncate_title(title_str: Any, max_length: int = 255) -> str:
    """Truncate title to maximum character length for Shopify compatibility - STRICT 255 limit."""
    if pd.isna(title_str) or title_str == '':
        return ''
    
    title_str = str(title_str).strip()
    
    # If already within limit, return as-is
    if len(title_str) <= max_length:
        return title_str
    
    # Strict truncation: cut to max_length-3, add '...', then double-check
    if max_length >= 3:
        truncated = title_str[:max_length-3] + '...'
    else:
        # If max_length is less than 3, just truncate to max_length
        truncated = title_str[:max_length]
    
    # Final safety check - absolutely ensure we don't exceed max_length
    if len(truncated) > max_length:
        truncated = truncated[:max_length]
    
    return truncated


def normalize_dataframe_types(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame column types to prevent concatenation errors."""
    df_normalized = df.copy()
    
    # Define columns that should remain numeric
    numeric_columns = ['Variant Inventory Qty', 'Variant Price', 'Cost per item', 'Variant Grams']
    
    for col in df_normalized.columns:
        if col in numeric_columns:
            # Keep numeric columns as numeric, convert to float to handle mixed int/float
            # Remove commas before converting to numeric
            df_normalized[col] = df_normalized[col].astype(str).str.replace(',', '')
            df_normalized[col] = pd.to_numeric(df_normalized[col], errors='coerce').fillna(0)
        else:
            # Convert all other columns to string and handle None/NaN values aggressively
            try:
                # Convert to string, handling None and NaN values
                df_normalized[col] = df_normalized[col].fillna('').astype(str)
                # Replace common problematic values
                df_normalized[col] = df_normalized[col].replace({
                    'nan': '',
                    'None': '',
                    'NaN': '',
                    '<NA>': ''
                })
            except Exception as e:
                # If conversion fails, force everything to empty string
                df_normalized[col] = ''
    
    return df_normalized


def generate_shopify_tags(df: pd.DataFrame, item_code_column: str, tag_columns: List[str]) -> List[str]:
    """Generate Shopify tags by combining data from multiple columns."""
    tags_list = []
    
    for _, row in df.iterrows():
        tags = []
        
        # Process each selected tag column
        for col in tag_columns:
            if col in df.columns and pd.notna(row[col]) and str(row[col]).strip():
                value = str(row[col]).strip()
                
                # Split only on major separators (preserve - and _ as connectors)
                parts = re.split(r'[\s/\\|,;:]+', value)
                
                # Clean each part
                for part in parts:
                    # Remove unwanted special characters but keep - and _
                    clean_part = re.sub(r'[^\w\s\-_]', '', part).strip()
                    
                    # Convert to lowercase and add if not empty
                    if clean_part and len(clean_part) > 1:  # Ignore single character tags
                        tags.append(clean_part.lower())
        
        # Remove duplicates while preserving order
        unique_tags = []
        seen = set()
        for tag in tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        
        # Join tags with commas
        final_tags = ', '.join(unique_tags) if unique_tags else ''
        tags_list.append(final_tags)
    
    return tags_list