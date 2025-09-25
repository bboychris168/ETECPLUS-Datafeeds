import streamlit as st
import pandas as pd
import json
import os
import re

# Configure page
st.set_page_config(
    page_title="ETEC+ Supplier Datafeeds",
    page_icon="📊",
    layout="wide"
)

# Simple CSS
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
                    df = pd.read_csv(file, delimiter=delimiter, nrows=0)  # Just get headers
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

def normalize_dataframe_types(df):
    """Normalize DataFrame column types to prevent concatenation errors"""
    df_normalized = df.copy()
    
    # Define columns that should remain numeric
    numeric_columns = ['Variant Inventory Qty', 'Variant Price', 'Cost per item', 'Variant Grams']
    
    for col in df_normalized.columns:
        if col in numeric_columns:
            # Keep numeric columns as numeric, convert to float to handle mixed int/float
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
                    df = pd.read_csv(file, delimiter=delimiter)
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
    st.write("🔍 **Duplicate Removal Debug:**")
    
    # Show initial vendor breakdown
    if 'Vendor' in combined_df.columns:
        initial_counts = combined_df['Vendor'].value_counts()
        st.write(f"📊 Before duplicate removal:")
        for vendor, count in initial_counts.items():
            st.write(f"   • {vendor}: {count} products")
    
    if 'Variant SKU' not in combined_df.columns or 'Cost per item' not in combined_df.columns:
        st.write("⚠️ Missing required columns for duplicate removal")
        return combined_df, []
    
    # Convert cost to numeric
    combined_df['Cost per item'] = pd.to_numeric(combined_df['Cost per item'], errors='coerce')
    
    # Check for invalid costs by vendor
    invalid_costs = combined_df[combined_df['Cost per item'].isna()]
    if len(invalid_costs) > 0:
        st.write(f"⚠️ Found {len(invalid_costs)} rows with invalid costs:")
        if 'Vendor' in invalid_costs.columns:
            invalid_by_vendor = invalid_costs['Vendor'].value_counts()
            for vendor, count in invalid_by_vendor.items():
                st.write(f"   • {vendor}: {count} invalid costs")
    
    # Remove rows with invalid costs
    before_dropna = len(combined_df)
    combined_df = combined_df.dropna(subset=['Cost per item'])
    after_dropna = len(combined_df)
    
    if before_dropna != after_dropna:
        st.write(f"🗑️ Removed {before_dropna - after_dropna} rows with invalid costs")
        
        # Show vendor breakdown after removing invalid costs
        if 'Vendor' in combined_df.columns:
            after_invalid_removal = combined_df['Vendor'].value_counts()
            st.write(f"📊 After removing invalid costs:")
            for vendor, count in after_invalid_removal.items():
                st.write(f"   • {vendor}: {count} products")
    
    # Find duplicates before removal
    duplicates_info = []
    if len(combined_df) > 0:
        # Group by Variant SKU to find duplicates
        grouped = combined_df.groupby('Variant SKU')
        
        for sku, group in grouped:
            if len(group) > 1:
                # Sort by cost to see which ones will be removed
                group_sorted = group.sort_values('Cost per item')
                kept_row = group_sorted.iloc[0]  # Lowest cost (kept)
                removed_rows = group_sorted.iloc[1:]  # Higher cost (removed)
                
                for _, removed_row in removed_rows.iterrows():
                    duplicates_info.append({
                        'Variant SKU': sku,
                        'Title': removed_row.get('Title', ''),
                        'Vendor (Removed)': removed_row.get('Vendor', ''),
                        'Cost (Removed)': removed_row.get('Cost per item', 0),
                        'Vendor (Kept)': kept_row.get('Vendor', ''),
                        'Cost (Kept)': kept_row.get('Cost per item', 0),
                        'Savings': removed_row.get('Cost per item', 0) - kept_row.get('Cost per item', 0)
                    })
    
    # Remove duplicates keeping lowest cost
    final_df = combined_df.sort_values('Cost per item').drop_duplicates('Variant SKU', keep='first')
    
    # Show final vendor breakdown after duplicate removal
    if 'Vendor' in final_df.columns:
        final_counts = final_df['Vendor'].value_counts()
        st.write(f"📊 After duplicate removal:")
        for vendor, count in final_counts.items():
            st.write(f"   • {vendor}: {count} products")
        
        # Show what was removed by vendor
        if len(duplicates_info) > 0:
            removed_by_vendor = {}
            for dup in duplicates_info:
                vendor = dup['Vendor (Removed)']
                removed_by_vendor[vendor] = removed_by_vendor.get(vendor, 0) + 1
            
            st.write(f"🗑️ Duplicates removed by vendor:")
            for vendor, count in removed_by_vendor.items():
                st.write(f"   • {vendor}: {count} products removed")
    
    return final_df, duplicates_info

def process_files(uploaded_files, mappings):
    """Process all uploaded files and combine data"""
    all_data = []
    
    for file in uploaded_files:
        supplier = detect_supplier(file.name)
        st.write(f"🔍 Processing {file.name} - Detected supplier: {supplier}")  # Debug info
        
        if supplier and supplier in mappings:
            st.write(f"✅ Found mapping for {supplier}")  # Debug info
            
            df = read_file(file)
            if df is not None:
                st.write(f"📊 Read {len(df)} rows from {file.name}")  # Debug info
                st.write(f"📋 Available columns in {file.name}: {list(df.columns)}")  # Show actual columns
                
                mapping = mappings[supplier]
                st.write(f"🔗 Applying {len(mapping)} mappings for {supplier}")
                
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
                
                st.write(f"   ✅ Column mappings: {successful_mappings}")
                st.write(f"   📝 Custom values: {custom_mappings}")
                if missing_columns:
                    st.write(f"   ⚠️ Missing columns: {', '.join(missing_columns)}")
                
                # Create DataFrame
                if mapped_data:
                    result_df = pd.DataFrame(mapped_data)
                    st.write(f"📊 Created DataFrame: {len(result_df)} rows × {len(result_df.columns)} columns")
                    
                    # Process quantity if mapped
                    if 'Variant Inventory Qty' in result_df.columns:
                        result_df['Variant Inventory Qty'] = result_df['Variant Inventory Qty'].apply(extract_quantity)
                    
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
                    
                    # Show sample data for debugging
                    st.write(f"📋 Sample data from {supplier}:")
                    sample_cols = ['Title', 'Variant SKU', 'Vendor', 'Variant Price']
                    available_cols = [col for col in sample_cols if col in result_df.columns]
                    if available_cols:
                        st.dataframe(result_df[available_cols].head(2))
                    
                    all_data.append(result_df)
                    st.success(f"✅ {file.name}: {len(result_df)} products processed from {supplier}")
                else:
                    st.error(f"❌ {file.name}: No valid mappings found for {supplier}")
                    st.write(f"Mapped data keys: {list(mapped_data.keys()) if mapped_data else 'None'}")
            else:
                st.error(f"❌ {file.name}: Could not read file")
        else:
            if supplier:
                st.warning(f"⚠️ {file.name}: Detected supplier '{supplier}' but no mapping found")
                st.write(f"Available mappings: {list(mappings.keys())}")
            else:
                st.warning(f"⚠️ {file.name}: Could not detect supplier from filename")
                st.write("Available suppliers with keywords:")
                for supp, map_data in mappings.items():
                    keyword = map_data.get('_file_keyword', 'No keyword')
                    st.write(f"• {supp}: '{keyword}'")
    
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

# Tabs
if shopify_configured:
    tab1, tab2, tab3, tab4 = st.tabs(["🏪 Shopify Template", "📁 Upload", "🔗 Map", "⚡ Export"])
else:
    tab1, tab2, tab3, tab4 = st.tabs(["🏪 Shopify Template", "📁 Upload (Disabled)", "🔗 Map (Disabled)", "⚡ Export (Disabled)"])

# Shopify Template Tab
with tab1:
    st.markdown('<div class="step-box">', unsafe_allow_html=True)
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
    
    st.markdown('</div>', unsafe_allow_html=True)

# Upload Tab
with tab2:
    st.markdown('<div class="step-box">', unsafe_allow_html=True)
    
    if not shopify_configured:
        st.header("📁 Upload Files (Disabled)")
        st.warning("⚠️ Please configure your Shopify template first in the 'Shopify Template' tab.")
    else:
        st.header("📁 Upload Supplier Files")
        
        uploaded_files = st.file_uploader(
            "Upload CSV or Excel files from your suppliers",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            help="Upload multiple supplier data files to process"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} files uploaded")
            for file in uploaded_files:
                supplier = detect_supplier(file.name)
                st.write(f"📄 {file.name} - {supplier or 'Unknown supplier'}")
            st.session_state.uploaded_files = uploaded_files
    
    st.markdown('</div>', unsafe_allow_html=True)

# Mapping Tab
with tab3:
    st.markdown('<div class="step-box">', unsafe_allow_html=True)
    
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
            file = next(f for f in st.session_state.uploaded_files if f.name == selected_file)
            supplier = st.text_input("Supplier name:", detect_supplier(selected_file) or "")
            
            if supplier:
                df = read_file(file)
                if df is not None:
                    supplier_columns = [""] + list(df.columns)
                    existing = st.session_state.supplier_mappings.get(supplier, {})
                    
                    st.subheader("Column Mappings")
                    st.info("💡 Map your supplier columns to Shopify fields. Leave blank if not available in your data.")
                    
                    # File keyword for auto-detection
                    mapping = {}
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
                            current_mapping = existing.get(field, "")
                            current_custom = existing.get(f"{field}_custom", "")
                            
                            # Highlight important fields
                            important_fields = ["Variant SKU", "Title", "Variant Price", "Cost per item", "Variant Inventory Qty"]
                            label = f"⭐ {field}" if field in important_fields else field
                            
                            st.markdown(f"**{label}**")
                            
                            # Radio button to choose mapping type
                            mapping_type = st.radio(
                                f"How to set {field}:",
                                ["Map from supplier column", "Enter custom text", "Leave empty"],
                                key=f"{field}_type",
                                horizontal=True,
                                index=0 if current_mapping and current_mapping in supplier_columns else (1 if current_custom else 2)
                            )
                            
                            if mapping_type == "Map from supplier column":
                                mapping[field] = st.selectbox(
                                    f"Select column for {field}:",
                                    supplier_columns,
                                    index=supplier_columns.index(current_mapping) if current_mapping in supplier_columns else 0,
                                    key=f"{field}_select",
                                    help=f"Map to your supplier column for {field}" + (" (Recommended)" if field in important_fields else "")
                                )
                                # Clear custom text if mapping from column
                                if f"{field}_custom" in mapping:
                                    del mapping[f"{field}_custom"]
                                    
                            elif mapping_type == "Enter custom text":
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
                            
                            st.markdown("---")  # Separator between fields
                    
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
    
    st.markdown('</div>', unsafe_allow_html=True)

# Export Tab
with tab4:
    st.markdown('<div class="step-box">', unsafe_allow_html=True)
    
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
                
                # Download
                csv_data = final_df.to_csv(index=False)
                st.download_button(
                    "💾 Download Shopify CSV",
                    csv_data,
                    "shopify_products.csv",
                    "text/csv",
                    type="primary"
                )
                
                # Store in session for reference
                st.session_state.processed_data = final_df
                st.session_state.duplicates_info = duplicates_info
    
    st.markdown('</div>', unsafe_allow_html=True)

# Show current mappings in sidebar
st.sidebar.header("Current Mappings")
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