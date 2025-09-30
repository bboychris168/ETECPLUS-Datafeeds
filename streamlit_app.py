import streamlit as st
import pandas as pd
import json
import os
import re
import requests
import io
from datetime import datetime
import time
import logging
from io import StringIO


# Configure page
st.set_page_config(
    page_title="ETEC+ Supplier Datafeeds",
    page_icon="📊",
    layout="wide"
)

# Setup logging
def setup_logging():
    """Setup logging to capture debug information to file"""
    log_folder = "logs"
    os.makedirs(log_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_folder, f"datafeed_processing_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(StringIO())  # Capture to string for download
        ]
    )
    
    return log_file

# Initialize logging
if 'log_file' not in st.session_state:
    st.session_state.log_file = setup_logging()

def log_info(message):
    """Log info message and optionally show in streamlit"""
    logging.info(message)
    # Optionally show brief message in streamlit
    return message

def log_write(message):
    """Log message (equivalent to st.write but logged)"""
    logging.info(message)
    # Show in streamlit but also log
    st.write(message)
    return message

# Enhanced CSS with mapping highlights
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .step-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }

    .mapping-status {
        font-weight: bold;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.9em;
        margin-left: 10px;
    }
    .status-mapped {
        background: #28a745;
        color: white;
    }
    .status-custom {
        background: #17a2b8;
        color: white;
    }
    .status-missing {
        background: #dc3545;
        color: white;
    }
    .status-required {
        background: #ffc107;
        color: black;
    }
    
    /* Modern Upload Section Styling */
    .supplier-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border: 1px solid #e1e8ed;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .supplier-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }
    
    .upload-section {
        background: #ffffff;
        border: 2px dashed #d1d5db;
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .upload-section:hover {
        border-color: #667eea;
        background: #f8faff;
    }
    
    .file-list-item {
        background: #f8f9fa;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        margin: 0.3rem 0;
        border-left: 3px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'supplier_mappings' not in st.session_state:
    st.session_state.supplier_mappings = {}
if 'update_template' not in st.session_state:
    st.session_state.update_template = False

def load_shopify_template():
    """Load Shopify CSV template fields from config file"""
    if os.path.exists("mappings/shopify_template.json"):
        with open("mappings/shopify_template.json", 'r') as f:
            template_data = json.load(f)
            return template_data.get("columns", [])
    return []

def save_shopify_template(columns):
    """Save Shopify CSV template columns to config file"""
    os.makedirs("mappings", exist_ok=True)
    template_data = {
        "columns": columns,
        "uploaded_date": pd.Timestamp.now().isoformat()
    }
    with open("mappings/shopify_template.json", 'w') as f:
        json.dump(template_data, f, indent=2)

def extract_shopify_columns(file):
    """Extract column headers from uploaded Shopify CSV template"""
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

def load_mappings():
    """Load supplier mappings"""
    if os.path.exists("mappings/supplier_mappings.json"):
        with open("mappings/supplier_mappings.json", 'r') as f:
            return json.load(f)
    return {}

def save_mappings(mappings):
    """Save supplier mappings"""
    os.makedirs("mappings", exist_ok=True)
    with open("mappings/supplier_mappings.json", 'w') as f:
        json.dump(mappings, f, indent=2)

def load_supplier_config():
    """Load supplier download configuration"""
    if os.path.exists("supplier_config.json"):
        with open("supplier_config.json", 'r') as f:
            return json.load(f)
    return {}

def save_supplier_config(config):
    """Save supplier download configuration"""
    with open("supplier_config.json", 'w') as f:
        json.dump(config, f, indent=4)

def download_to_suppliers_folder(selected_suppliers, supplier_config):
    """Download files directly to suppliers folder"""
    # Create suppliers folder if it doesn't exist
    os.makedirs("suppliers", exist_ok=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, supplier_key in enumerate(selected_suppliers):
        config = supplier_config[supplier_key]
        status_text.text(f"Downloading {config['name']}...")
        
        try:
            url = config['url']
            filename = config['filename']
            file_path = os.path.join("suppliers", filename)
            
            # Add user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Save to file
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            st.success(f"✅ {config['name']}: Downloaded to {file_path}")
            
        except requests.exceptions.RequestException as e:
            st.error(f"❌ {config['name']}: Download failed - {str(e)}")
        except Exception as e:
            st.error(f"❌ {config['name']}: Error - {str(e)}")
        
        # Update progress
        progress_bar.progress((i + 1) / len(selected_suppliers))
    
    status_text.text("Download complete!")

def load_files_from_suppliers_folder():
    """Load available files from suppliers folder"""
    suppliers_folder = "suppliers"
    if not os.path.exists(suppliers_folder):
        return []
    
    files = []
    for filename in os.listdir(suppliers_folder):
        if filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            file_path = os.path.join(suppliers_folder, filename)
            # Get file modification time for display
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            display_name = f"{filename} (Updated: {mod_time.strftime('%Y-%m-%d %H:%M')})"
            files.append((file_path, display_name))
    
    return files



def extract_quantity(qty_str):
    """Extract quantity from string"""
    if pd.isna(qty_str) or qty_str == '':
        return 0
    
    qty_str = str(qty_str).strip().upper()
    
    if qty_str in ['IN STOCK', 'AVAILABLE', 'YES']:
        return 999
    if qty_str in ['OUT OF STOCK', 'NO', 'DISCONTINUED']:
        return 0
    
    match = re.search(r'(\d+)', qty_str)
    return int(match.group(1)) if match else 0

def convert_weight_to_grams(weight_str):
    """Convert weight string to grams - simple x1000 conversion for kg to grams"""
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

def truncate_title(title_str, max_length=255):
    """Truncate title to maximum character length for Shopify compatibility - STRICT 255 limit"""
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

def normalize_dataframe_types(df):
    """Normalize DataFrame column types to prevent concatenation errors"""
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

def generate_shopify_tags(df, item_code_column, tag_columns):
    """Generate Shopify tags by combining data from multiple columns"""
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

def save_tag_mapping(tag_config):
    """Save tag generation configuration"""
    os.makedirs("mappings", exist_ok=True)
    with open("mappings/tag_config.json", 'w') as f:
        json.dump(tag_config, f, indent=2)

def load_tag_mapping():
    """Load tag generation configuration"""
    if os.path.exists("mappings/tag_config.json"):
        with open("mappings/tag_config.json", 'r') as f:
            return json.load(f)
    return {}

def detect_supplier(filename):
    """Detect supplier from filename"""
    filename = filename.lower()
    mappings = load_mappings()
    
    # Check existing mappings first
    for supplier, config in mappings.items():
        if '_file_keyword' in config:
            if config['_file_keyword'].lower() in filename:
                return supplier
    
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

def read_file(file):
    """Read CSV or Excel file"""
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

def find_and_remove_duplicates(combined_df):
    """Find duplicates and remove them, keeping lowest cost. Returns final df and duplicates info."""
    log_write("🔍 **Duplicate Removal Debug:**")
    
    # Show initial vendor breakdown
    if 'Vendor' in combined_df.columns:
        initial_counts = combined_df['Vendor'].value_counts()
        log_write(f"📊 Before duplicate removal:")
        for vendor, count in initial_counts.items():
            log_info(f"   • {vendor}: {count} products")
    
    if 'Variant SKU' not in combined_df.columns or 'Cost per item' not in combined_df.columns:
        log_write("⚠️ Missing required columns for duplicate removal")
        return combined_df, []
    
    # Convert cost to numeric - remove commas first
    combined_df['Cost per item'] = combined_df['Cost per item'].astype(str).str.replace(',', '')
    combined_df['Cost per item'] = pd.to_numeric(combined_df['Cost per item'], errors='coerce')
    
    # Check for invalid costs by vendor
    invalid_costs = combined_df[combined_df['Cost per item'].isna()]
    if len(invalid_costs) > 0:
        log_write(f"⚠️ Found {len(invalid_costs)} rows with invalid costs:")
        if 'Vendor' in invalid_costs.columns:
            invalid_by_vendor = invalid_costs['Vendor'].value_counts()
            for vendor, count in invalid_by_vendor.items():
                log_info(f"   • {vendor}: {count} invalid costs")
    
    # Remove rows with invalid costs
    before_dropna = len(combined_df)
    combined_df = combined_df.dropna(subset=['Cost per item'])
    after_dropna = len(combined_df)
    
    if before_dropna != after_dropna:
        log_write(f"🗑️ Removed {before_dropna - after_dropna} rows with invalid costs")
        
        # Show vendor breakdown after removing invalid costs
        if 'Vendor' in combined_df.columns:
            after_invalid_removal = combined_df['Vendor'].value_counts()
            log_write(f"📊 After removing invalid costs:")
            for vendor, count in after_invalid_removal.items():
                log_info(f"   • {vendor}: {count} products")
    
    # Find duplicates and preserve image URLs before removal
    duplicates_info = []
    images_preserved = 0
    
    # Check what image fields are available
    available_image_fields = ['Image Src', 'Variant Image', 'Image', 'Product Image', 'Image URL']
    found_image_fields = [field for field in available_image_fields if field in combined_df.columns]
    
    if found_image_fields:
        log_write(f"📷 Checking for images in fields: {', '.join(found_image_fields)}")
    else:
        log_write("⚠️ No standard image fields found in data")
    
    if len(combined_df) > 0:
        # Group by Variant SKU to find duplicates
        grouped = combined_df.groupby('Variant SKU')
        
        for sku, group in grouped:
            if len(group) > 1:
                # Sort by cost to see which ones will be removed
                group_sorted = group.sort_values('Cost per item')
                kept_idx = group_sorted.index[0]  # Index of lowest cost (kept)
                removed_rows = group_sorted.iloc[1:]  # Higher cost (removed)
                
                # Check if we can preserve image URLs from duplicates
                image_fields = ['Image Src', 'Variant Image', 'Image', 'Product Image', 'Image URL']
                
                for image_field in image_fields:
                    if image_field in combined_df.columns:
                        # Get current image value for kept item
                        current_image = combined_df.loc[kept_idx, image_field]
                        
                        # If kept item has no image or empty image
                        if pd.isna(current_image) or str(current_image).strip() == '' or str(current_image).lower() in ['none', 'null', 'n/a']:
                            # Look for image in duplicates that will be removed
                            for _, removed_row in removed_rows.iterrows():
                                removed_image = removed_row.get(image_field, '')
                                
                                # If duplicate has a valid image URL, preserve it
                                if (pd.notna(removed_image) and 
                                    str(removed_image).strip() != '' and 
                                    str(removed_image).lower() not in ['none', 'null', 'n/a'] and
                                    (str(removed_image).startswith(('http', 'https', 'www.', 'ftp://')) or 
                                     '.' in str(removed_image))):  # Also accept relative URLs with extensions
                                    
                                    # Transfer image URL to kept item
                                    combined_df.loc[kept_idx, image_field] = removed_image
                                    images_preserved += 1
                                    
                                    log_info(f"🖼️ Preserved {image_field} for SKU {sku}: '{removed_image}' from {removed_row.get('Vendor', 'Unknown')} → {combined_df.loc[kept_idx, 'Vendor']}")
                                    break  # Only take the first valid image found
                        else:
                            # If kept item already has an image, still check if duplicates have better/different images
                            best_images = []
                            for _, removed_row in removed_rows.iterrows():
                                removed_image = removed_row.get(image_field, '')
                                if (pd.notna(removed_image) and 
                                    str(removed_image).strip() != '' and 
                                    str(removed_image).lower() not in ['none', 'null', 'n/a'] and
                                    str(removed_image) != str(current_image) and  # Different from current
                                    (str(removed_image).startswith(('http', 'https', 'www.', 'ftp://')) or 
                                     '.' in str(removed_image))):
                                    best_images.append(removed_image)
                            
                            # If we found alternative images, log them for reference
                            if best_images:
                                log_info(f"ℹ️ SKU {sku} has {len(best_images)} alternative images available from duplicates (keeping current: '{current_image}')")
                
                # Record duplicate info
                for _, removed_row in removed_rows.iterrows():
                    duplicates_info.append({
                        'Variant SKU': sku,
                        'Title': removed_row.get('Title', ''),
                        'Vendor (Removed)': removed_row.get('Vendor', ''),
                        'Cost (Removed)': removed_row.get('Cost per item', 0),
                        'Vendor (Kept)': combined_df.loc[kept_idx, 'Vendor'],
                        'Cost (Kept)': combined_df.loc[kept_idx, 'Cost per item'],
                        'Savings': removed_row.get('Cost per item', 0) - combined_df.loc[kept_idx, 'Cost per item']
                    })
    
    # Show image preservation summary
    if images_preserved > 0:
        st.success(f"🖼️ Successfully preserved {images_preserved} image URLs from duplicate items to ensure products have images")
        log_info("📋 Image preservation ensures that when duplicates are removed, any missing images are filled from the duplicate entries")
    else:
        log_info("📷 No image preservation needed - either no duplicates found or all kept items already had images")
    
    # Remove duplicates keeping lowest cost (with preserved images)
    final_df = combined_df.sort_values('Cost per item').drop_duplicates('Variant SKU', keep='first')
    
    # Show final vendor breakdown after duplicate removal
    if 'Vendor' in final_df.columns:
        final_counts = final_df['Vendor'].value_counts()
        log_write(f"📊 After duplicate removal:")
        for vendor, count in final_counts.items():
            log_info(f"   • {vendor}: {count} products")
        
        # Show what was removed by vendor
        if len(duplicates_info) > 0:
            removed_by_vendor = {}
            for dup in duplicates_info:
                vendor = dup['Vendor (Removed)']
                removed_by_vendor[vendor] = removed_by_vendor.get(vendor, 0) + 1
            
            log_write(f"🗑️ Duplicates removed by vendor:")
            for vendor, count in removed_by_vendor.items():
                log_info(f"   • {vendor}: {count} products removed")
    
    return final_df, duplicates_info

def process_files(uploaded_files, mappings):
    """Process all uploaded files and combine data"""
    all_data = []
    
    for file in uploaded_files:
        supplier = detect_supplier(file.name)
        log_info(f"🔍 Processing {file.name} - Detected supplier: {supplier}")  # Debug info
        
        if supplier and supplier in mappings:
            log_info(f"✅ Found mapping for {supplier}")  # Debug info
            
            df = read_file(file)
            if df is not None:
                log_info(f"📊 Read {len(df)} rows from {file.name}")  # Debug info
                log_info(f"📋 Available columns in {file.name}: {list(df.columns)}")  # Show actual columns
                
                mapping = mappings[supplier]
                log_info(f"🔗 Applying {len(mapping)} mappings for {supplier}")
                
                # Apply mapping
                mapped_data = {}
                successful_mappings = 0
                custom_mappings = 0
                missing_columns = []
                
                for shopify_field, supplier_field in mapping.items():
                    if shopify_field == "_file_keyword":
                        # Skip _file_keyword - it's not a Shopify field
                        continue
                    elif shopify_field.endswith('_custom'):
                        # Skip custom field keys, they're handled separately
                        continue
                    elif supplier_field and supplier_field in df.columns:
                        # Map from supplier column
                        mapped_data[shopify_field] = df[supplier_field]
                        successful_mappings += 1
                    elif shopify_field == "Tags" and supplier_field and ',' in supplier_field:
                        # Special handling for Tags field with multiple columns
                        tag_columns = [col.strip() for col in supplier_field.split(',') if col.strip()]
                        available_tag_cols = [col for col in tag_columns if col in df.columns]
                        
                        if available_tag_cols:
                            # Generate tags from multiple columns
                            item_code_col = 'Variant SKU'  # Use SKU as identifier
                            tags = generate_shopify_tags(df, item_code_col, available_tag_cols)
                            mapped_data[shopify_field] = tags
                            successful_mappings += 1
                            log_info(f"   🏷️ Generated tags from: {', '.join(available_tag_cols)}")
                        else:
                            # No valid tag columns found
                            mapped_data[shopify_field] = [""] * len(df)
                            log_info(f"   ⚠️ Tag columns not found: {', '.join(tag_columns)}")
                    elif f"{shopify_field}_custom" in mapping and mapping[f"{shopify_field}_custom"]:
                        # Use custom text value - FIX: Create list to match DataFrame rows
                        custom_value = mapping[f"{shopify_field}_custom"]
                        mapped_data[shopify_field] = [custom_value] * len(df)
                        custom_mappings += 1
                    else:
                        # Leave empty - FIX: Create list to match DataFrame rows
                        mapped_data[shopify_field] = [""] * len(df)
                        if supplier_field and supplier_field not in df.columns:
                            missing_columns.append(f"{shopify_field} → {supplier_field}")
                
                log_info(f"   ✅ Column mappings: {successful_mappings}")
                log_info(f"   📝 Custom values: {custom_mappings}")
                if missing_columns:
                    log_info(f"   ⚠️ Missing columns: {', '.join(missing_columns)}")
                
                # Create DataFrame
                if mapped_data:
                    result_df = pd.DataFrame(mapped_data)
                    log_info(f"📊 Created DataFrame: {len(result_df)} rows × {len(result_df.columns)} columns")
                    
                    # Process quantity if mapped
                    if 'Variant Inventory Qty' in result_df.columns:
                        result_df['Variant Inventory Qty'] = result_df['Variant Inventory Qty'].apply(extract_quantity)
                    
                    # Process weight conversion to grams if mapped
                    if 'Variant Grams' in result_df.columns:
                        result_df['Variant Grams'] = result_df['Variant Grams'].apply(convert_weight_to_grams)
                        log_info(f"   ⚖️ Converted weights to grams for {supplier}")
                    
                    # Process title length limitation if mapped
                    if 'Title' in result_df.columns:
                        original_titles = result_df['Title'].astype(str)
                        long_titles = original_titles[original_titles.str.len() > 255]
                        if len(long_titles) > 0:
                            result_df['Title'] = result_df['Title'].apply(truncate_title)
                            log_info(f"   ✂️ Truncated {len(long_titles)} long titles (>255 chars) for {supplier}")
                            
                            # Double-check: verify no titles exceed 255 characters after truncation
                            final_titles = result_df['Title'].astype(str)
                            still_long = final_titles[final_titles.str.len() > 255]
                            if len(still_long) > 0:
                                # Emergency truncation - force to exactly 255 chars
                                result_df.loc[final_titles.str.len() > 255, 'Title'] = final_titles[final_titles.str.len() > 255].str[:255]
                                log_info(f"   🚨 Emergency truncated {len(still_long)} titles that still exceeded 255 chars")
                            else:
                                log_info(f"   ✅ All titles verified to be ≤255 characters for {supplier}")
                    
                    # Add vendor
                    result_df['Vendor'] = supplier
                    
                    # Normalize data types to prevent concatenation errors
                    result_df = normalize_dataframe_types(result_df)
                    
                    # Add default values for required fields
                    result_df['Published'] = 'true'
                    result_df['Option1 Name'] = 'Title'
                    result_df['Option1 Value'] = 'Default Title'
                    result_df['Variant Inventory Tracker'] = 'shopify'
                    result_df['Variant Inventory Policy'] = 'deny'
                    result_df['Variant Fulfillment Service'] = 'manual'
                    result_df['Variant Requires Shipping'] = 'true'
                    result_df['Variant Taxable'] = 'true'
                    result_df['Gift Card'] = 'false'
                    result_df['Status'] = 'active'
                    

                    
                    # Show sample data for debugging (but log the info)
                    log_info(f"📋 Sample data from {supplier}:")
                    sample_cols = ['Title', 'Variant SKU', 'Vendor', 'Variant Price', 'Variant Grams']
                    available_cols = [col for col in sample_cols if col in result_df.columns]
                    if available_cols:
                        sample_data = result_df[available_cols].head(2)
                        for idx, row in sample_data.iterrows():
                            log_info(f"   Sample {idx+1}: {dict(row)}")
                    
                    all_data.append(result_df)
                    st.success(f"✅ {file.name}: {len(result_df)} products processed from {supplier}")
                    log_info(f"Successfully processed {len(result_df)} products from {supplier}")
                else:
                    st.error(f"❌ {file.name}: No valid mappings found for {supplier}")
                    log_info(f"No valid mappings found for {supplier}. Mapped data keys: {list(mapped_data.keys()) if mapped_data else 'None'}")
            else:
                st.error(f"❌ {file.name}: Could not read file")
        else:
            if supplier:
                st.warning(f"⚠️ {file.name}: Detected supplier '{supplier}' but no mapping found")
                log_info(f"Detected supplier '{supplier}' but no mapping found. Available mappings: {list(mappings.keys())}")
            else:
                st.warning(f"⚠️ {file.name}: Could not detect supplier from filename")
                log_info("Could not detect supplier from filename")
                log_info("Available suppliers with keywords:")
                for supp, map_data in mappings.items():
                    keyword = map_data.get('_file_keyword', 'No keyword')
                    log_info(f"• {supp}: '{keyword}'")
    
    return all_data

# Main App
st.markdown('<div class="main-header"><h1>🏢 ETEC+ Supplier Datafeeds</h1><p>Simple Shopify CSV Mapping</p></div>', unsafe_allow_html=True)

# Load data
shopify_fields = load_shopify_template()
st.session_state.supplier_mappings = load_mappings()

# Check if Shopify template is configured
shopify_configured = len(shopify_fields) > 0

# Show workflow steps
if not shopify_configured:
    st.info("📋 **Workflow:** 1️⃣ Upload Shopify Template → 2️⃣ Upload Supplier Files → 3️⃣ Map Columns → 4️⃣ Export")
else:
    st.success("📋 **Workflow:** ✅ Shopify Template → 2️⃣ Upload Supplier Files → 3️⃣ Map Columns → 4️⃣ Export")

if not shopify_configured:
    st.warning("⚠️ Please upload your Shopify CSV template first to configure the column headers.")

# Help Section
with st.expander("📖 How to Use This Application", expanded=False):
    st.markdown("""
### 🚀 **Quick Start Guide**

**Step 1: Setup Shopify Template** 🏪
- Upload your Shopify CSV template file
- This defines the columns for your final export

**Step 2: Get Supplier Data** 📁
- Download data automatically from configured suppliers, OR
- Upload supplier files manually

**Step 3: Map Your Data** 🔗
- Match supplier columns to Shopify fields
- Add custom text where needed
- Generate tags from multiple columns

**Step 4: Export Products** ⚡
- Review and export your mapped data
- Download the final Shopify-ready CSV

**Step 5: Quote Products** 💰
- Generate quote database from your mappings
- Search products by SKU
- Compare prices across all suppliers

---
💡 **Tips:**
- Complete steps in order for best results
- Use the supplier URL manager to add new suppliers
- The quoting system shows ALL supplier options (no duplicates removed)
    """)

# Tabs
if shopify_configured:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏪 Shopify Template", "📁 Upload", "🔗 Map", "⚡ Export", "💰 Quoting"])
else:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏪 Shopify Template", "📁 Upload (Disabled)", "🔗 Map (Disabled)", "⚡ Export (Disabled)", "💰 Quoting"])

# Shopify Template Tab
with tab1:
    st.header("🏪 Shopify CSV Template")
    
    if shopify_configured:
        st.success(f"✅ Shopify template configured with {len(shopify_fields)} columns")
        
        # Show current template
        with st.expander("📋 Current Shopify Columns", expanded=False):
            cols = st.columns(3)
            for i, field in enumerate(shopify_fields):
                with cols[i % 3]:
                    st.write(f"• {field}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Update Template", help="Upload a new Shopify CSV template"):
                st.session_state.update_template = True
        with col2:
            if st.button("🗑️ Clear Template", help="Remove current template configuration"):
                if os.path.exists("mappings/shopify_template.json"):
                    os.remove("mappings/shopify_template.json")
                st.success("Template cleared! Please refresh the page.")
                st.rerun()
    
    if not shopify_configured or st.session_state.get('update_template', False):
        st.info("📤 Upload your Shopify CSV template file to configure the column headers")
        
        shopify_template_file = st.file_uploader(
            "Choose your Shopify CSV template",
            type=['csv', 'xlsx', 'xls'],
            help="Upload a Shopify CSV file (can be empty) to extract the column headers",
            key="shopify_template"
        )
        
        if shopify_template_file:
            columns = extract_shopify_columns(shopify_template_file)
            if columns:
                st.success(f"✅ Found {len(columns)} columns in your Shopify template")
                
                # Preview columns
                with st.expander("📋 Preview Columns", expanded=True):
                    cols = st.columns(3)
                    for i, col in enumerate(columns):
                        with cols[i % 3]:
                            st.write(f"• {col}")
                
                if st.button("💾 Save Shopify Template", type="primary"):
                    save_shopify_template(columns)
                    st.success("🎉 Shopify template saved! Please refresh the page to continue.")
                    st.balloons()
                    if 'update_template' in st.session_state:
                        del st.session_state.update_template
                    st.rerun()
            else:
                st.error("❌ Could not read columns from the file. Please check the file format.")

# Upload Tab
with tab2:
    if not shopify_configured:
        st.header("📁 Upload Supplier Files (Disabled)")
        st.warning("⚠️ Please configure your Shopify template first in the 'Shopify Template' tab.")
    else:
        st.header("📁 Get Supplier Data")
        st.markdown("*Choose how to get your supplier data files for processing*")
        
        # Create modern card-style sections
        supplier_config = load_supplier_config()
        
        # Section 1: Auto-Download from APIs
        if supplier_config:
            st.markdown("### 🌐 Download from Supplier APIs")
            st.markdown("*Get the latest data directly from your suppliers*")
            
            col1, col2, col3 = st.columns(3)
            supplier_keys = list(supplier_config.keys())
            
            selected_suppliers = []
            for i, supplier_key in enumerate(supplier_keys):
                config = supplier_config[supplier_key]
                with [col1, col2, col3][i % 3]:
                    if st.checkbox(f"Select {config['name']}", key=f"download_{supplier_key}"):
                        selected_suppliers.append(supplier_key)
            
            if selected_suppliers and st.button("� Download to Suppliers Folder", type="primary"):
                download_to_suppliers_folder(selected_suppliers, supplier_config)
            
            st.divider()
        
        # Section 2: Load from Downloaded Files
        supplier_files = load_files_from_suppliers_folder()
        
        if supplier_files:
            st.markdown("### 📂 Load Downloaded Files")
            st.markdown("*Use previously downloaded files from the suppliers folder*")
            
            # Show available files in a nice format
            with st.expander(f"📋 View Available Files ({len(supplier_files)} files)", expanded=False):
                for file_path, display_name in supplier_files:
                    supplier_name = detect_supplier(os.path.basename(file_path))
                    col_file, col_supplier = st.columns([3, 1])
                    with col_file:
                        st.write(f"📄 {display_name}")
                    with col_supplier:
                        if supplier_name:
                            st.success(f"✅ {supplier_name}")
                        else:
                            st.warning("❓ Unknown")
            
            col_load, col_count = st.columns([1, 2])
            with col_load:
                if st.button("📋 Load All Files", type="secondary", use_container_width=True):
                    loaded_files = []
                    for file_path, display_name in supplier_files:
                        try:
                            with open(file_path, 'rb') as f:
                                file_content = io.BytesIO(f.read())
                                file_content.name = os.path.basename(file_path)
                                loaded_files.append(file_content)
                        except Exception as e:
                            st.error(f"Error loading {display_name}: {str(e)}")
                    
                    if loaded_files:
                        st.session_state.uploaded_files = loaded_files
                        st.success(f"🎉 Loaded {len(loaded_files)} files successfully!")
            with col_count:
                st.info(f"📊 {len(supplier_files)} file{'s' if len(supplier_files) != 1 else ''} available")
                
            st.divider()
        
        # Section 3: Manual Upload
        st.markdown("### � Manual File Upload")
        st.markdown("*Upload files directly from your computer as a fallback option*")
        
        uploaded_files = st.file_uploader(
            "📁 Select files to upload",
            accept_multiple_files=True,
            type=['csv', 'xlsx', 'xls'],
            help="Upload CSV or Excel files from your computer",
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            col_success, col_info = st.columns([2, 1])
            with col_success:
                st.success(f"🎉 {len(uploaded_files)} file(s) uploaded successfully!")
            with col_info:
                total_size = sum(getattr(f, 'size', 0) for f in uploaded_files)
                if total_size > 0:
                    size_mb = total_size / (1024 * 1024)
                    st.info(f"📊 Total: {size_mb:.1f}MB")
            
            # Show uploaded files with supplier detection
            with st.expander("📋 View Uploaded Files", expanded=True):
                for file in uploaded_files:
                    supplier = detect_supplier(file.name)
                    col_file, col_supplier = st.columns([3, 1])
                    with col_file:
                        st.write(f"📄 {file.name}")
                    with col_supplier:
                        if supplier:
                            st.success(f"✅ {supplier}")
                        else:
                            st.warning("❓ Unknown")
            
            st.session_state.uploaded_files = uploaded_files
        
        st.divider()
        
        # Section 4: Supplier URL Management
        st.markdown("### ⚙️ Manage Supplier URLs")
        st.markdown("*Add, edit, or remove supplier download URLs*")
        
        supplier_config = load_supplier_config()
        
        with st.expander("🔧 Supplier Configuration", expanded=False):
            # Add new supplier
            st.markdown("**Add New Supplier:**")
            col1, col2 = st.columns(2)
            with col1:
                new_supplier_key = st.text_input("Supplier Key (lowercase, no spaces)", help="e.g., 'new_supplier'")
                new_supplier_name = st.text_input("Supplier Display Name", help="e.g., 'New Supplier'")
            with col2:
                new_supplier_url = st.text_input("Download URL", help="Full URL to the supplier's datafeed")
                new_supplier_filename = st.text_input("Filename", help="e.g., 'new_supplier_datafeed.csv'")
            
            col_add, col_spacer = st.columns([1, 3])
            with col_add:
                if st.button("➕ Add Supplier", type="secondary"):
                    if new_supplier_key and new_supplier_name and new_supplier_url and new_supplier_filename:
                        supplier_config[new_supplier_key] = {
                            "name": new_supplier_name,
                            "url": new_supplier_url,
                            "filename": new_supplier_filename,
                            "file_type": "csv",
                            "description": f"{new_supplier_name} product datafeed"
                        }
                        save_supplier_config(supplier_config)
                        st.success(f"✅ Added {new_supplier_name} successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Please fill in all fields")
            
            # Edit existing suppliers
            if supplier_config:
                st.markdown("**Edit Existing Suppliers:**")
                for key, config in supplier_config.items():
                    with st.container():
                        st.markdown(f"**{config['name']}** (`{key}`)")
                        col_edit1, col_edit2, col_remove = st.columns([2, 2, 1])
                        
                        with col_edit1:
                            new_name = st.text_input(f"Name###{key}", value=config['name'], key=f"name_{key}")
                            new_url = st.text_input(f"URL###{key}", value=config['url'], key=f"url_{key}")
                        
                        with col_edit2:
                            new_filename = st.text_input(f"Filename###{key}", value=config['filename'], key=f"filename_{key}")
                            
                            col_update, col_delete = st.columns(2)
                            with col_update:
                                if st.button(f"💾 Update", key=f"update_{key}", type="secondary"):
                                    supplier_config[key].update({
                                        "name": new_name,
                                        "url": new_url,
                                        "filename": new_filename
                                    })
                                    save_supplier_config(supplier_config)
                                    st.success(f"✅ Updated {new_name}!")
                                    st.rerun()
                            
                            with col_delete:
                                if st.button(f"🗑️ Remove", key=f"delete_{key}", type="secondary"):
                                    del supplier_config[key]
                                    save_supplier_config(supplier_config)
                                    st.success(f"✅ Removed supplier!")
                                    st.rerun()
                        
                        st.divider()
        
        # Show current files status
        if 'uploaded_files' in st.session_state and st.session_state.uploaded_files:
            st.divider()
            st.write("**📋 Current Files Ready for Processing:**")
            for file in st.session_state.uploaded_files:
                supplier = detect_supplier(file.name)
                st.write(f"✅ {file.name} - {supplier or 'Unknown supplier'}")

# Mapping Tab
with tab3:
    if not shopify_configured:
        st.header("🔗 Map Columns (Disabled)")
        st.warning("⚠️ Please configure your Shopify template first.")
    elif 'uploaded_files' not in st.session_state:
        st.header("🔗 Map Columns")
        st.warning("⚠️ Please upload supplier files first.")
    else:
        st.header("🔗 Map Supplier Columns to Shopify")
        
        # Select file
        file_names = [f.name for f in st.session_state.uploaded_files]
        selected_file = st.selectbox("Select file:", file_names)
        
        if selected_file:
            try:
                file = next(f for f in st.session_state.uploaded_files if f.name == selected_file)
                supplier = st.text_input("Supplier name:", detect_supplier(selected_file) or "")
            except StopIteration:
                st.error(f"Could not find file {selected_file} in uploaded files")
                file = None
                supplier = None
            
            if supplier and file is not None:
                df = read_file(file)
                if df is not None:
                    supplier_columns = [""] + list(df.columns)
                    existing = st.session_state.supplier_mappings.get(supplier, {})
                    
                    st.subheader("Column Mappings")
                    
                    # Show mapping status summary
                    actual_shopify_fields = [field for field in shopify_fields if field != "_file_keyword"]
                    important_fields = ["Variant SKU", "Title", "Variant Price", "Cost per item", "Variant Inventory Qty"]
                    
                    mapped_count = 0
                    custom_count = 0
                    important_missing = []
                    
                    for field in actual_shopify_fields:
                        current_mapping = existing.get(field, "")
                        current_custom = existing.get(f"{field}_custom", "")
                        
                        if current_mapping:
                            mapped_count += 1
                        elif current_custom:
                            custom_count += 1
                        elif field in important_fields:
                            important_missing.append(field)
                    
                    # Status summary
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("📋 Column Mappings", mapped_count, f"of {len(actual_shopify_fields)} fields")
                    with col_b:
                        st.metric("📝 Custom Values", custom_count)
                    with col_c:
                        st.metric("⚠️ Missing Important", len(important_missing), delta=f"-{len(important_missing)}" if important_missing else None)
                    
                    if important_missing:
                        st.error(f"🚨 **Critical fields missing:** {', '.join(important_missing)}")
                    else:
                        st.success("✅ **All critical fields are mapped!**")
                    
                    st.info("💡 **Color Guide:** 🟢 Green = Mapped | 🟡 Yellow = Required | 🔴 Red = Missing")
                    
                    # File keyword for auto-detection
                    # Initialize mapping with existing data to preserve state
                    mapping = existing.copy() if existing else {}
                    mapping["_file_keyword"] = st.text_input(
                        "🔍 File keyword (for auto-detection):", 
                        value=existing.get("_file_keyword", supplier.lower()),
                        help="This keyword will be used to automatically detect files from this supplier"
                    )
                    
                    # Create columns for better layout
                    col1, col2 = st.columns(2)
                    
                    # Map all Shopify fields in two columns (excluding _file_keyword)
                    actual_shopify_fields = [field for field in shopify_fields if field != "_file_keyword"]
                    for i, field in enumerate(actual_shopify_fields):
                        with col1 if i % 2 == 0 else col2:
                            # Use current mapping values if available, otherwise use existing saved values
                            current_mapping = mapping.get(field, "") or existing.get(field, "")
                            current_custom = mapping.get(f"{field}_custom", "") or existing.get(f"{field}_custom", "")
                            
                            # Determine field status and styling
                            important_fields = ["Variant SKU", "Title", "Variant Price", "Cost per item", "Variant Inventory Qty"]
                            is_important = field in important_fields
                            has_mapping = bool(current_mapping)
                            has_custom = bool(current_custom)
                            
                            # Create status indicators
                            if has_mapping:
                                status = "✅ MAPPED"
                                status_class = "status-mapped"
                            elif has_custom:
                                status = "📝 CUSTOM"
                                status_class = "status-custom" 
                            elif is_important:
                                status = "⚠️ REQUIRED"
                                status_class = "status-required"
                            else:
                                status = "❌ MISSING"
                                status_class = "status-missing"
                            
                            # Field header with status
                            icon = "⭐" if is_important else "📋"
                            # Add special icon for Variant Grams
                            if field == "Variant Grams":
                                icon = "⚖️"
                            # Add special icon for Title
                            elif field == "Title":
                                icon = "📝"
                            header_html = f"""
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 1.1em; font-weight: bold;">{icon} {field}</span>
                                <span class="mapping-status {status_class}">{status}</span>
                            </div>
                            """
                            st.markdown(header_html, unsafe_allow_html=True)
                            
                            # Add helpful note for Variant Grams field
                            if field == "Variant Grams":
                                st.info("⚖️ **Auto-conversion:** All weights multiplied by 1000 (simple kg→g conversion)")
                                with st.expander("💡 Weight Conversion Examples", expanded=False):
                                    st.markdown("""
                                    **Simple weight conversion (×1000):**
                                    - `0.5` → `500` (grams)
                                    - `1.2` → `1200` (grams)  
                                    - `2.5` → `2500` (grams)
                                    - `0.75` → `750` (grams)
                                    - `3` → `3000` (grams)
                                    
                                    **Note:** All numeric values are multiplied by 1000 to convert kg to grams.
                                    Non-numeric values will be set to 0.
                                    """)
                            
                            # Add helpful note for Title field
                            elif field == "Title":
                                st.info("📝 **Auto-truncation:** Titles longer than 255 characters will be automatically truncated with '...'")
                                with st.expander("💡 Title Length Examples", expanded=False):
                                    st.markdown("""
                                    **Title character limit (255 max):**
                                    - Titles ≤ 255 chars → Keep as is
                                    - Titles > 255 chars → Truncate to 252 chars + "..."
                                    
                                    **Example:**
                                    - Original: `"Very long product title that exceeds 255 characters..."`
                                    - Result: `"Very long product title that exceeds 255 characte..."`
                                    
                                    **Note:** This prevents Shopify import errors due to title length limits.
                                    """)
                            
                            # Radio button to choose mapping type
                            mapping_type = st.radio(
                                f"How to set {field}:",
                                ["📋 Map from supplier column", "📝 Enter custom text", "❌ Leave empty"],
                                key=f"{field}_type",
                                horizontal=True,
                                index=0 if current_mapping and current_mapping in supplier_columns else (1 if current_custom else 2)
                            )
                            
                            if mapping_type == "📋 Map from supplier column":
                                # Special handling for Tags field - allow multiple columns
                                if field == "Tags":
                                    # For Tags, allow multiple column selection
                                    current_tag_columns = current_mapping.split(',') if current_mapping else []
                                    current_tag_columns = [col.strip() for col in current_tag_columns if col.strip() in supplier_columns]
                                    
                                    selected_columns = st.multiselect(
                                        f"Select columns for {field}:",
                                        supplier_columns[1:],  # Exclude empty option
                                        default=current_tag_columns,
                                        key=f"{field}_multiselect",
                                        help="Select multiple columns to combine for tags. They will be processed and cleaned automatically."
                                    )
                                    
                                    # Store as comma-separated string
                                    mapping[field] = ','.join(selected_columns) if selected_columns else ''
                                    
                                    if selected_columns:
                                        st.info(f"🏷️ Will generate tags from: {', '.join(selected_columns)}")
                                else:
                                    # Regular single column selection for other fields
                                    mapping[field] = st.selectbox(
                                        f"Select column for {field}:",
                                        supplier_columns,
                                        index=supplier_columns.index(current_mapping) if current_mapping in supplier_columns else 0,
                                        key=f"{field}_select",
                                        help=f"Map to your supplier column for {field}" + (" (⭐ Highly Recommended)" if is_important else "")
                                    )
                                
                                # Clear custom text if mapping from column
                                if f"{field}_custom" in mapping:
                                    del mapping[f"{field}_custom"]
                                    
                            elif mapping_type == "📝 Enter custom text":
                                mapping[f"{field}_custom"] = st.text_input(
                                    f"Custom text for {field}:",
                                    value=current_custom,
                                    key=f"{field}_custom_input",
                                    help=f"Enter static text that will be used for all products in {field}",
                                    placeholder=f"e.g., 'Electronics', 'true', 'active', etc."
                                )
                                # Clear column mapping if using custom text
                                mapping[field] = ""
                                
                            else:  # Leave empty
                                mapping[field] = ""
                                if f"{field}_custom" in mapping:
                                    del mapping[f"{field}_custom"]
                            
                            # Add separator line
                            st.markdown("---")
                    
                    if st.button("💾 Save Mapping"):
                        # Clean mapping - keep file keyword, non-empty values, and custom text
                        clean_mapping = {}
                        for k, v in mapping.items():
                            if k == "_file_keyword":
                                clean_mapping[k] = v
                            elif k.endswith('_custom') and v:
                                clean_mapping[k] = v
                            elif not k.endswith('_custom') and v:
                                clean_mapping[k] = v
                        
                        st.session_state.supplier_mappings[supplier] = clean_mapping
                        save_mappings(st.session_state.supplier_mappings)
                        st.success(f"✅ Saved mapping for {supplier}")
                        
                        # Show summary of what was saved
                        column_mappings = sum(1 for k, v in clean_mapping.items() if not k.endswith('_custom') and not k == '_file_keyword' and v)
                        custom_mappings = sum(1 for k, v in clean_mapping.items() if k.endswith('_custom') and v)
                        st.info(f"📊 Saved {column_mappings} column mappings and {custom_mappings} custom text fields")
                else:
                    st.error("❌ Could not read the selected file. Please check the file format or try re-downloading.")

# Export Tab
with tab4:
    if not shopify_configured:
        st.header("⚡ Process & Export (Disabled)")
        st.warning("⚠️ Please configure your Shopify template first.")
    elif 'uploaded_files' not in st.session_state:
        st.header("⚡ Process & Export")
        st.warning("⚠️ Please upload supplier files first.")
    elif not st.session_state.supplier_mappings:
        st.header("⚡ Process & Export")
        st.warning("⚠️ Please create column mappings first.")
    else:
        st.header("⚡ Process & Export")
        
        # Debug section - add this to help identify the issue
        with st.expander("🔍 Debug Info", expanded=False):
            st.write("**Uploaded Files:**")
            for file in st.session_state.uploaded_files:
                supplier = detect_supplier(file.name)
                has_mapping = supplier in st.session_state.supplier_mappings if supplier else False
                st.write(f"• {file.name} → {supplier or 'No supplier detected'} → {'✅ Has mapping' if has_mapping else '❌ No mapping'}")
            
            st.write("\n**Available Mappings:**")
            for supplier, mapping in st.session_state.supplier_mappings.items():
                keyword = mapping.get('_file_keyword', 'No keyword')
                mapped_fields = [k for k in mapping.keys() if not k.startswith('_') and not k.endswith('_custom')]
                custom_fields = [k.replace('_custom', '') for k in mapping.keys() if k.endswith('_custom')]
                st.write(f"• {supplier}: keyword='{keyword}'")
                st.write(f"  - Mapped fields: {len(mapped_fields)} ({', '.join(mapped_fields[:3])}{'...' if len(mapped_fields) > 3 else ''})")
                st.write(f"  - Custom fields: {len(custom_fields)} ({', '.join(custom_fields[:3])}{'...' if len(custom_fields) > 3 else ''})")
            
            # Show column differences that might cause conflicts
            st.write("\n**Potential Data Type Conflicts:**")
            st.write("Fields that some suppliers have but others don't:")
            all_fields = set()
            supplier_fields = {}
            for supplier, mapping in st.session_state.supplier_mappings.items():
                fields = set([k for k in mapping.keys() if not k.startswith('_') and not k.endswith('_custom')])
                supplier_fields[supplier] = fields
                all_fields.update(fields)
            
            for field in sorted(all_fields):
                suppliers_with_field = [s for s, fields in supplier_fields.items() if field in fields]
                suppliers_without_field = [s for s, fields in supplier_fields.items() if field not in fields]
                if len(suppliers_without_field) > 0:
                    st.write(f"• {field}: ✅ {', '.join(suppliers_with_field)} | ❌ {', '.join(suppliers_without_field)}")
        
        if st.button("🚀 Process Files"):
            all_data = process_files(st.session_state.uploaded_files, st.session_state.supplier_mappings)
            
            if all_data:
                st.write(f"📊 Processing {len(all_data)} supplier files...")
                
                # Show details of each supplier's data before combining
                for i, df in enumerate(all_data):
                    vendor = df['Vendor'].iloc[0] if 'Vendor' in df.columns and len(df) > 0 else f"Supplier {i+1}"
                    st.write(f"📋 Supplier {i+1} ({vendor}): {len(df)} rows, {len(df.columns)} columns")
                    if 'Title' in df.columns:
                        sample_titles = df['Title'].head(2).tolist()
                        st.write(f"   📝 Sample products: {', '.join([str(t)[:50] + '...' if len(str(t)) > 50 else str(t) for t in sample_titles])}")
                
                # More aggressive normalization before combining
                normalized_data = []
                for i, df in enumerate(all_data):
                    vendor = df['Vendor'].iloc[0] if 'Vendor' in df.columns and len(df) > 0 else f"Supplier {i+1}"
                    st.write(f"� Normalizing {vendor}: {len(df)} rows")
                    
                    # Apply our comprehensive normalization
                    df_normalized = normalize_dataframe_types(df)
                    normalized_data.append(df_normalized)
                
                # Combine data with robust error handling
                try:
                    st.write("🔗 Attempting to combine data...")
                    combined_df = pd.concat(normalized_data, ignore_index=True)
                    st.success(f"✅ Successfully combined {len(combined_df)} rows")
                    
                    # Show breakdown by vendor after successful combination
                    if 'Vendor' in combined_df.columns:
                        vendor_counts = combined_df['Vendor'].value_counts()
                        st.write("📊 **Final Combined Data by Vendor:**")
                        for vendor, count in vendor_counts.items():
                            st.write(f"   • {vendor}: {count} products")
                    else:
                        st.warning("⚠️ No Vendor column found in combined data")
                except Exception as e:
                    st.error(f"❌ Error combining data: {str(e)}")
                    st.info("🔧 Trying manual combination method...")
                    
                    # Manual combination with column alignment
                    combined_df = pd.DataFrame()
                    for i, df in enumerate(normalized_data):
                        st.write(f"🔄 Adding supplier {i+1}...")
                        
                        if combined_df.empty:
                            combined_df = df.copy()
                            st.write(f"   📝 Base: {len(combined_df)} rows, {len(combined_df.columns)} columns")
                        else:
                            # Get all unique columns
                            all_columns = list(set(combined_df.columns) | set(df.columns))
                            
                            # Add missing columns to both DataFrames
                            for col in all_columns:
                                if col not in combined_df.columns:
                                    combined_df[col] = ""
                                if col not in df.columns:
                                    df[col] = ""
                            
                            # Ensure same column order
                            combined_df = combined_df.reindex(columns=all_columns, fill_value="")
                            df = df.reindex(columns=all_columns, fill_value="")
                            
                            # Force all columns to string type for consistency
                            for col in all_columns:
                                if col not in ['Variant Inventory Qty', 'Variant Price', 'Cost per item', 'Variant Grams']:
                                    combined_df[col] = combined_df[col].astype(str)
                                    df[col] = df[col].astype(str)
                            
                            # Combine
                            try:
                                combined_df = pd.concat([combined_df, df], ignore_index=True)
                                st.write(f"   ✅ Added: {len(df)} rows. Total: {len(combined_df)} rows")
                            except Exception as inner_e:
                                st.error(f"   ❌ Failed to add supplier {i+1}: {str(inner_e)}")
                                st.write(f"   📊 Combined columns: {list(combined_df.columns)}")
                                st.write(f"   📊 Supplier columns: {list(df.columns)}")
                                continue
                
                # Show final combination results
                if 'Vendor' in combined_df.columns:
                    vendor_counts = combined_df['Vendor'].value_counts()
                    st.write("📊 **Manual Combination Results by Vendor:**")
                    for vendor, count in vendor_counts.items():
                        st.write(f"   • {vendor}: {count} products")
                else:
                    st.warning("⚠️ No Vendor column found in manually combined data")
                
                # Remove duplicates and get duplicate info
                final_df, duplicates_info = find_and_remove_duplicates(combined_df)
                
                # Ensure all required Shopify fields are present (excluding _file_keyword)
                actual_shopify_fields = [field for field in shopify_fields if field != "_file_keyword"]
                for field in actual_shopify_fields:
                    if field not in final_df.columns:
                        final_df[field] = ""
                
                # Remove _file_keyword if it somehow got into the DataFrame
                if "_file_keyword" in final_df.columns:
                    final_df = final_df.drop(columns=["_file_keyword"])
                
                # Generate Handle from Title if not mapped
                if 'Handle' not in final_df.columns or final_df['Handle'].isna().all():
                    final_df['Handle'] = final_df['Title'].str.lower().str.replace(' ', '-').str.replace('[^a-z0-9-]', '', regex=True)
                
                st.success(f"🎉 {len(final_df)} unique products ready!")
                
                # Show duplicate removal stats
                original_count = sum(len(df) for df in all_data)
                duplicates_removed = len(duplicates_info)
                if duplicates_removed > 0:
                    total_savings = sum(dup['Savings'] for dup in duplicates_info)
                    st.info(f"📊 Removed {duplicates_removed} duplicates, kept lowest cost prices. Total potential savings: ${total_savings:.2f}")
                    
                    # Show duplicates in expandable section
                    with st.expander(f"🔍 View {duplicates_removed} Removed Duplicates", expanded=False):
                        if duplicates_info:
                            duplicates_df = pd.DataFrame(duplicates_info)
                            
                            # Format the display
                            duplicates_df['Cost (Removed)'] = duplicates_df['Cost (Removed)'].apply(lambda x: f"${x:.2f}")
                            duplicates_df['Cost (Kept)'] = duplicates_df['Cost (Kept)'].apply(lambda x: f"${x:.2f}")
                            duplicates_df['Savings'] = duplicates_df['Savings'].apply(lambda x: f"${x:.2f}")
                            
                            # Normalize duplicates dataframe for display to prevent ArrowTypeError
                            display_duplicates_df = normalize_dataframe_types(duplicates_df)
                            st.dataframe(
                                display_duplicates_df,
                                use_container_width=True,
                                column_config={
                                    "Variant SKU": st.column_config.TextColumn("Product SKU", width="medium"),
                                    "Title": st.column_config.TextColumn("Product Title", width="large"),
                                    "Vendor (Removed)": st.column_config.TextColumn("Removed From", width="small"),
                                    "Cost (Removed)": st.column_config.TextColumn("Higher Cost", width="small"),
                                    "Vendor (Kept)": st.column_config.TextColumn("Kept From", width="small"),
                                    "Cost (Kept)": st.column_config.TextColumn("Lower Cost", width="small"),
                                    "Savings": st.column_config.TextColumn("Savings", width="small")
                                }
                            )
                            
                            # Summary by vendor
                            st.subheader("Duplicate Summary by Vendor")
                            removed_by_vendor = {}
                            kept_by_vendor = {}
                            
                            for dup in duplicates_info:
                                removed_vendor = dup['Vendor (Removed)']
                                kept_vendor = dup['Vendor (Kept)']
                                
                                removed_by_vendor[removed_vendor] = removed_by_vendor.get(removed_vendor, 0) + 1
                                kept_by_vendor[kept_vendor] = kept_by_vendor.get(kept_vendor, 0) + 1
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Products Removed (Higher Cost):**")
                                for vendor, count in removed_by_vendor.items():
                                    st.write(f"• {vendor}: {count} products")
                            
                            with col2:
                                st.write("**Products Kept (Lower Cost):**")
                                for vendor, count in kept_by_vendor.items():
                                    st.write(f"• {vendor}: {count} products")
                else:
                    st.info("📊 No duplicates found - all products have unique SKUs")
                
                # Preview
                st.subheader("Final Dataset Preview")
                # Normalize for display to prevent ArrowTypeError
                display_df = normalize_dataframe_types(final_df.head(10))
                st.dataframe(display_df)
                
                # Download options
                col_csv, col_log = st.columns(2)
                
                with col_csv:
                    # Create UTF-8 encoded CSV
                    csv_data = final_df.to_csv(index=False, encoding='utf-8')
                    st.download_button(
                        "💾 Download Shopify CSV (UTF-8)",
                        csv_data.encode('utf-8'),
                        "shopify_products.csv",
                        "text/csv; charset=utf-8",
                        type="primary"
                    )
                
                with col_log:
                    # Download log file
                    if os.path.exists(st.session_state.log_file):
                        with open(st.session_state.log_file, 'r', encoding='utf-8') as f:
                            log_data = f.read()
                        
                        st.download_button(
                            "📋 Download Processing Log",
                            log_data,
                            f"processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            "text/plain; charset=utf-8",
                            type="secondary"
                        )
                
                # Store in session for reference
                st.session_state.processed_data = final_df
                st.session_state.duplicates_info = duplicates_info

# Show current mappings in sidebar
st.sidebar.header("Current Mappings")

# Show log file info
if 'log_file' in st.session_state and os.path.exists(st.session_state.log_file):
    file_size = os.path.getsize(st.session_state.log_file)
    st.sidebar.info(f"📋 Processing log: {file_size} bytes")
    st.sidebar.caption("Log will be available for download after processing")

if st.session_state.supplier_mappings:
    for supplier, mapping in st.session_state.supplier_mappings.items():
        with st.sidebar.expander(f"📋 {supplier}"):
            for field, value in mapping.items():
                if field == "_file_keyword":
                    st.write(f"🔍 File keyword: {value}")
                elif field.endswith('_custom'):
                    # Show custom text fields
                    original_field = field.replace('_custom', '')
                    if value:
                        st.write(f"📝 {original_field} ← Custom: '{value}'")
                elif value and not mapping.get(f"{field}_custom"):
                    # Show column mappings only if no custom text
                    st.write(f"🔗 {field} ← {value}")
else:
    st.sidebar.info("No mappings created yet")

# Quoting Tab
with tab5:
    st.header("💰 Product Quoting")
    st.markdown("Search for products using variant SKUs and view product information with images.")
    
    # Initialize session state for quoting
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    
    # Search section
    st.markdown("### 🔍 Product Search")
    
    col_search, col_button = st.columns([3, 1])
    with col_search:
        search_input = st.text_input(
            "Enter SKU/Product Code",
            placeholder="e.g., ABC123, DEF456, GHI789",
            help="Enter one or multiple SKUs separated by commas"
        )
    
    with col_button:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
        search_button = st.button("🔍 Search Products", type="primary", use_container_width=True)
    
    # Bulk search option
    st.markdown("**Bulk Search:**")
    bulk_skus = st.text_area(
        "Enter multiple SKUs (one per line)",
        placeholder="ABC123\nDEF456\nGHI789",
        height=100
    )
    
    if st.button("🔍 Bulk Search", type="secondary"):
        if bulk_skus:
            search_input = bulk_skus.replace('\n', ',')
            search_button = True
    
    # Auto-generate export data for quoting
    st.markdown("### � Automatic Data Loading")
    
    # Check if we have mapped suppliers ready for export
    has_mapped_suppliers = bool(st.session_state.supplier_mappings)
    shopify_columns = load_shopify_template()
    
    if has_mapped_suppliers and shopify_columns:
        st.success("✅ Supplier mappings detected - automatically generating quote data")
        
        # Create quoting folder
        os.makedirs("quoting", exist_ok=True)
        quoting_file_path = "quoting/export_data_for_quoting.csv"
        
        # Auto-generate the export CSV for quoting
        col_generate, col_status = st.columns([1, 2])
        with col_generate:
            if st.button("🔄 Generate Quote Data", type="primary"):
                try:
                    # Create quote data with ALL supplier entries (no deduplication)
                    combined_data = []
                    
                    if 'uploaded_files' in st.session_state and st.session_state.uploaded_files:
                        for file in st.session_state.uploaded_files:
                            supplier = detect_supplier(file.name)
                            if supplier and supplier in st.session_state.supplier_mappings:
                                mapping = st.session_state.supplier_mappings[supplier]
                                
                                # Read supplier file
                                file.seek(0)
                                if file.name.endswith('.csv'):
                                    supplier_df = pd.read_csv(file, low_memory=False)
                                else:
                                    supplier_df = pd.read_excel(file)
                                
                                # Apply mappings to create Shopify format
                                export_data = pd.DataFrame()
                                for shopify_col in shopify_columns:
                                    if shopify_col in mapping:
                                        mapped_col = mapping[shopify_col]
                                        if mapped_col and mapped_col in supplier_df.columns:
                                            export_data[shopify_col] = supplier_df[mapped_col]
                                        elif f"{shopify_col}_custom" in mapping and mapping[f"{shopify_col}_custom"]:
                                            export_data[shopify_col] = mapping[f"{shopify_col}_custom"]
                                        else:
                                            export_data[shopify_col] = ""
                                    else:
                                        export_data[shopify_col] = ""
                                
                                # Add supplier identifier and include ALL entries
                                if not export_data.empty:
                                    export_data['_Supplier'] = supplier
                                    combined_data.append(export_data)
                    
                    if combined_data:
                        # Combine ALL supplier data (NO duplicate removal)
                        quote_df = pd.concat(combined_data, ignore_index=True)
                        
                        # Save to quoting folder
                        quote_df.to_csv(quoting_file_path, index=False)
                        st.session_state.quoting_data_generated = True
                        
                        # Count by supplier
                        supplier_counts = quote_df['_Supplier'].value_counts()
                        count_text = ", ".join([f"{supplier}: {count}" for supplier, count in supplier_counts.items()])
                        st.success(f"✅ Generated quote data with {len(quote_df)} products ({count_text})")
                        st.rerun()
                    else:
                        st.error("❌ No data to export. Please check your supplier files and mappings.")
                        
                except Exception as e:
                    st.error(f"❌ Error generating quote data: {str(e)}")
        
        with col_status:
            # Check if quoting data exists
            if os.path.exists(quoting_file_path):
                file_stats = os.stat(quoting_file_path)
                file_size = file_stats.st_size / 1024  # KB
                modified_time = pd.Timestamp.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                st.info(f"📄 Quote data available: {file_size:.1f}KB (Updated: {modified_time})")
                exported_csv = quoting_file_path  # Use the auto-generated file
                
                # Show auto-refresh option
                if st.button("🔄 Refresh Data", type="secondary", help="Regenerate quote data with latest mappings"):
                    st.session_state.quoting_data_generated = False  # Force regeneration
                    st.rerun()
            else:
                st.warning("⚠️ No quote data generated yet.")
                
                st.info("💡 Click 'Generate Quote Data' to create searchable product database")
                
                exported_csv = None
    else:
        st.warning("⚠️ No supplier mappings found")
        st.info("💡 Please go to the Upload and Map tabs to set up your supplier data first")
        
        # Show helpful workflow
        with st.expander("📋 Setup Workflow", expanded=True):
            st.markdown("""
            **To use the quoting system:**
            1. 🏪 **Shopify Template**: Upload your Shopify CSV template
            2. 📁 **Upload**: Upload supplier data files  
            3. 🔗 **Map**: Map supplier columns to Shopify fields
            4. 💰 **Quoting**: Return here to search products and find best prices
            """)
        
        exported_csv = None
    
    # Perform search
    if search_button and search_input and exported_csv is not None:
        search_terms = [term.strip().upper() for term in search_input.replace('\n', ',').split(',') if term.strip()]
        
        if search_terms:
            st.markdown("### 📊 Search Results")
            
            # Search through the exported CSV file
            all_results = []
            
            try:
                # Read the exported CSV file (either file path or uploaded file)
                if isinstance(exported_csv, str):
                    # It's a file path
                    df = pd.read_csv(exported_csv, low_memory=False)
                else:
                    # It's an uploaded file object
                    exported_csv.seek(0)
                    df = pd.read_csv(exported_csv, low_memory=False)
                
                st.write(f"📄 Loaded {len(df)} products from quote data")
                
                # Search for SKUs in the Variant SKU column primarily, but also other columns as fallback
                for search_term in search_terms:
                    # Create a mask to search across relevant columns
                    mask = pd.Series([False] * len(df))
                    
                    # Primary search in Variant SKU column
                    if 'Variant SKU' in df.columns:
                        mask |= df['Variant SKU'].astype(str).str.upper().str.contains(search_term, na=False)
                    
                    # Fallback search in other text columns
                    for col in df.columns:
                        if df[col].dtype == 'object' and col not in ['Image Src', 'Body (HTML)', 'SEO Description']:  # Skip large text fields
                            mask |= df[col].astype(str).str.upper().str.contains(search_term, na=False)
                    
                    # Get matching rows
                    matches = df[mask].copy()
                    
                    if not matches.empty:
                        matches['search_term'] = search_term
                        all_results.append(matches)
                
            except Exception as e:
                st.error(f"Error reading exported CSV: {str(e)}")
                all_results = []
            
            # Display results
            if all_results:
                combined_results = pd.concat(all_results, ignore_index=True)
                st.session_state.search_results = combined_results
                
                st.success(f"✅ Found {len(combined_results)} matching products")
                
                # Find and display lowest cost product
                # Look for Shopify cost columns first, then fallback to generic terms
                shopify_cost_fields = ['Cost per item', 'Variant Price']
                generic_cost_fields = ['cost', 'price', 'wholesale', 'buy', 'purchase', 'dealer', 'trade', 'net']
                
                lowest_cost_product = None
                lowest_cost_value = float('inf')
                
                # Show quick stats
                total_suppliers = len(combined_results['_Supplier'].unique()) if '_Supplier' in combined_results.columns else 1
                st.info(f"📊 Searching {len(combined_results)} products from {total_suppliers} supplier(s)")
                
                for idx, row in combined_results.iterrows():
                    # Prioritize Shopify cost columns first
                    for col in row.index:
                        if col in shopify_cost_fields or any(cost_field in col.lower() for cost_field in generic_cost_fields):
                            try:
                                # Clean and convert price value
                                raw_value = row[col]
                                if pd.isna(raw_value) or raw_value == '':
                                    continue
                                    
                                price_str = str(raw_value).replace('$', '').replace(',', '').replace(' ', '').replace('AUD', '').replace('USD', '').strip()
                                
                                if price_str and price_str.lower() not in ['nan', 'none', '', 'null', '0', '0.0', '0.00']:
                                    # Remove commas before converting to float
                                    price_value = float(price_str.replace(',', ''))
                                    if price_value > 0:
                                        # Prioritize "Cost per item" over other price fields
                                        if col == 'Cost per item':
                                            if price_value < lowest_cost_value:
                                                lowest_cost_value = price_value
                                                lowest_cost_product = row.copy()
                                                lowest_cost_product['_cost_field'] = col
                                                lowest_cost_product['_cost_value'] = price_value
                                        elif lowest_cost_product is None or lowest_cost_product.get('_cost_field') != 'Cost per item':
                                            # Only use other price fields if no "Cost per item" found
                                            if price_value < lowest_cost_value:
                                                lowest_cost_value = price_value
                                                lowest_cost_product = row.copy()
                                                lowest_cost_product['_cost_field'] = col
                                                lowest_cost_product['_cost_value'] = price_value
                            except (ValueError, TypeError):
                                continue
                
                # Display lowest cost product at the top
                if lowest_cost_product is not None:
                    # Enhanced green styling for entire best price section
                    st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                        color: white;
                        border-radius: 15px;
                        padding: 20px;
                        margin: 15px 0;
                        box-shadow: 0 4px 20px rgba(40, 167, 69, 0.3);
                        border: none;
                    ">
                    <h3 style="color: white; margin-top: 0;">🏆 Best Price Found</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.container():
                        
                        col_info, col_image = st.columns([2, 1])
                        
                        with col_info:
                            st.markdown(f"**🏷️ Best Price: ${lowest_cost_product['_cost_value']:.2f}** ({lowest_cost_product['_cost_field']})")
                            st.markdown(f"**📦 Supplier:** {lowest_cost_product.get('supplier', 'Unknown')}")
                            st.markdown(f"**🔍 Search Term:** {lowest_cost_product.get('search_term', 'N/A')}")
                            
                            # Display key Shopify product information
                            shopify_important_fields = ['Title', 'Vendor', 'Type', 'Variant SKU', 'Variant Price', 'Cost per item', 'Variant Compare At Price', 'Variant Inventory Qty']
                            
                            # Show key fields first
                            for field in shopify_important_fields:
                                if field in lowest_cost_product.index and pd.notna(lowest_cost_product[field]) and lowest_cost_product[field] != '':
                                    st.markdown(f"**{field}:** {lowest_cost_product[field]}")
                            
                            # Show other relevant fields
                            other_fields = ['Tags', 'Product Category', 'Variant Barcode', 'Handle']
                            for field in other_fields:
                                if field in lowest_cost_product.index and pd.notna(lowest_cost_product[field]) and lowest_cost_product[field] != '':
                                    st.write(f"{field}: {lowest_cost_product[field]}")
                        
                        with col_image:
                            # Smart image search - try best price product first, then all other suppliers
                            image_found = False
                            image_url_found = None
                            supplier_with_image = None
                            
                            # Define image field patterns to look for
                            def find_image_url(product_row):
                                """Find image URL in a product row"""
                                # Check Shopify image fields first
                                shopify_image_fields = ['Image Src', 'Variant Image']
                                for field in shopify_image_fields:
                                    if field in product_row.index and pd.notna(product_row[field]):
                                        url = str(product_row[field]).strip()
                                        if url.startswith(('http', 'https')):
                                            return url
                                
                                # Check generic image fields
                                for col in product_row.index:
                                    col_lower = str(col).lower()
                                    if any(keyword in col_lower for keyword in ['image', 'img', 'photo', 'picture']):
                                        if pd.notna(product_row[col]):
                                            url = str(product_row[col]).strip()
                                            if url.startswith(('http', 'https')):
                                                return url
                                return None
                            
                            # Step 1: Try to get image from the best price product
                            best_price_supplier = lowest_cost_product.get('_Supplier', 'Unknown')
                            image_url_found = find_image_url(lowest_cost_product)
                            
                            if image_url_found:
                                supplier_with_image = best_price_supplier
                                image_found = True
                            else:
                                # Step 2: Search ALL other suppliers for an image
                                st.write(f"🔍 Best price supplier ({best_price_supplier}) has no image, searching other suppliers...")
                                
                                # Get the search term to find all related products
                                search_term = lowest_cost_product.get('search_term', '')
                                if search_term:
                                    # Find all products with the same search term
                                    matching_products = combined_results[combined_results['search_term'] == search_term]
                                    st.write(f"📊 Found {len(matching_products)} total products for this SKU")
                                    
                                    # Try each supplier
                                    for idx, other_product in matching_products.iterrows():
                                        other_supplier = other_product.get('_Supplier', 'Unknown')
                                        
                                        # Skip the best price supplier (already tried)
                                        if other_supplier != best_price_supplier:
                                            st.write(f"🔍 Checking {other_supplier} for images...")
                                            temp_image_url = find_image_url(other_product)
                                            
                                            if temp_image_url:
                                                image_url_found = temp_image_url
                                                supplier_with_image = other_supplier
                                                image_found = True
                                                st.write(f"✅ Found image in {other_supplier}!")
                                                break
                                            else:
                                                st.write(f"❌ No image in {other_supplier}")
                            
                            # Display the image if found
                            if image_found and image_url_found:
                                try:
                                    if supplier_with_image == best_price_supplier:
                                        caption = "Product Image"
                                    else:
                                        caption = f"Product Image (from {supplier_with_image})"
                                    
                                    st.image(image_url_found, caption=caption, width=200)
                                except Exception as e:
                                    st.error(f"Failed to load image: {str(e)}")
                                    st.info("📷 Image URL found but failed to load")
                            else:
                                st.warning("📷 No images found in any supplier data")
                                
                                # Debug: Show what fields are available
                                st.write("🔍 Available fields in best price product:")
                                available_fields = [col for col in lowest_cost_product.index if pd.notna(lowest_cost_product[col]) and str(lowest_cost_product[col]).strip()]
                                st.write(available_fields[:10])  # Show first 10 fields
                        
                        # Show source info
                        supplier = lowest_cost_product.get('_Supplier', 'Unknown')
                        vendor = lowest_cost_product.get('Vendor', 'Unknown Vendor')
                        st.markdown(f"**Source:** {supplier} (Vendor: {vendor})")
                    
                    st.markdown("---")
                    st.markdown("### 📋 All Search Results")
                else:
                    st.warning("💰 No cost/price information found in the search results")
                    st.info("🔍 Looking for columns containing: cost, price, wholesale, buy, purchase, dealer, trade, net")
                
                # Group results by search term and show supplier comparison
                for search_term in search_terms:
                    term_results = combined_results[combined_results['search_term'] == search_term]
                    
                    if not term_results.empty:
                        st.markdown(f"#### 🔍 Results for: **{search_term}** ({len(term_results)} supplier options)")
                        
                        # Sort by cost for better comparison
                        if 'Cost per item' in term_results.columns:
                            # Convert cost column to numeric for proper sorting
                            term_results['_cost_numeric'] = pd.to_numeric(
                                term_results['Cost per item'].astype(str).str.replace('[$,]', '', regex=True), 
                                errors='coerce'
                            )
                            term_results = term_results.sort_values('_cost_numeric', na_position='last')
                        
                        for idx, row in term_results.iterrows():
                            supplier = row.get('_Supplier', 'Unknown')
                            cost = row.get('Cost per item', 'N/A')
                            try:
                                # Remove commas and convert to float
                                cost_value = float(str(cost).replace(',', '')) if pd.notna(cost) and cost != '' and cost != 'N/A' else None
                                cost_display = f"${cost_value:.2f}" if cost_value is not None else "No price"
                            except (ValueError, TypeError):
                                cost_display = "No price"
                            
                            with st.expander(f"📦 {supplier} - {cost_display}", expanded=False):
                                
                                # Create columns for product info and image
                                col_info, col_image = st.columns([2, 1])
                                
                                with col_info:
                                    # Display key Shopify product information
                                    shopify_key_fields = ['Title', 'Vendor', 'Type', 'Variant SKU', 'Variant Price', 'Cost per item', 'Variant Compare At Price', 'Variant Inventory Qty']
                                    
                                    # Show key fields first
                                    for field in shopify_key_fields:
                                        if field in row.index and pd.notna(row[field]) and row[field] != '':
                                            st.markdown(f"**{field}:** {row[field]}")
                                    
                                    # Show other fields
                                    for col in row.index:
                                        if col not in shopify_key_fields and col != 'search_term' and pd.notna(row[col]) and row[col] != '':
                                            if col in ['Tags', 'Product Category', 'Handle', 'Variant Barcode']:
                                                st.write(f"{col}: {row[col]}")
                                
                                with col_image:
                                    # Look for image URL fields
                                    image_fields = ['image', 'img', 'photo', 'picture', 'image_url', 'img_url', 'photo_url']
                                    image_found = False
                                    
                                    for col in row.index:
                                        col_lower = str(col).lower()
                                        if any(img_field in col_lower for img_field in image_fields):
                                            image_url = row[col]
                                            if pd.notna(image_url) and str(image_url).startswith(('http', 'https')):
                                                try:
                                                    st.image(image_url, caption=f"Product Image", width=200)
                                                    image_found = True
                                                    break
                                                except:
                                                    pass
                                    
                                    if not image_found:
                                        st.info("📷 No image available")
                                
                                # Show source info
                                supplier = row.get('_Supplier', 'Unknown')
                                vendor = row.get('Vendor', 'Unknown Vendor')
                                st.markdown(f"**Source:** {supplier} (Vendor: {vendor})")
                    else:
                        st.warning(f"❌ No results found for: {search_term}")
            else:
                st.warning("❌ No matching products found in quote data")
        else:
            st.error("❌ Please enter at least one SKU to search")
    
    elif search_button and not search_input:
        st.error("❌ Please enter a SKU to search")
    
    elif search_button and exported_csv is None:
        st.error("❌ Please upload your exported CSV file first")
        st.info("💡 Export your mapped data from the Export tab, then upload the CSV file here")
    
    # Display previous search results if available
    if hasattr(st.session_state, 'search_results') and len(st.session_state.search_results) > 0:
        st.markdown("---")
        st.markdown("### 📋 Export Search Results")
        
        col_export, col_clear = st.columns([1, 1])
        with col_export:
            if st.button("📥 Export to CSV", type="secondary"):
                csv_data = st.session_state.search_results.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name=f"product_search_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col_clear:
            if st.button("🗑️ Clear Results", type="secondary"):
                st.session_state.search_results = []
                st.rerun()