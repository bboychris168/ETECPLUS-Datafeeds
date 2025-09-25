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
    if 'Variant SKU' not in combined_df.columns or 'Cost per item' not in combined_df.columns:
        return combined_df, []
    
    # Convert cost to numeric
    combined_df['Cost per item'] = pd.to_numeric(combined_df['Cost per item'], errors='coerce')
    # Remove rows with invalid costs
    combined_df = combined_df.dropna(subset=['Cost per item'])
    
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
    
    return final_df, duplicates_info

def process_files(uploaded_files, mappings):
    """Process all uploaded files and combine data"""
    all_data = []
    
    for file in uploaded_files:
        supplier = detect_supplier(file.name)
        
        if supplier and supplier in mappings:
            df = read_file(file)
            if df is not None:
                mapping = mappings[supplier]
                
                # Apply mapping
                mapped_data = {}
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
                    elif f"{shopify_field}_custom" in mapping and mapping[f"{shopify_field}_custom"]:
                        # Use custom text value
                        custom_value = mapping[f"{shopify_field}_custom"]
                        mapped_data[shopify_field] = custom_value
                    else:
                        # Leave empty
                        mapped_data[shopify_field] = ""
                
                # Create DataFrame
                result_df = pd.DataFrame(mapped_data)
                
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
                
                all_data.append(result_df)
                st.success(f"✅ {file.name}: {len(result_df)} products processed")
        else:
            st.warning(f"⚠️ {file.name}: No mapping found")
    
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
        if st.button("🚀 Process Files"):
            all_data = process_files(st.session_state.uploaded_files, st.session_state.supplier_mappings)
            
            if all_data:
                # Normalize data types before combining to prevent type conflicts
                normalized_data = []
                for df in all_data:
                    df_copy = df.copy()
                    # Convert all object columns to string to ensure compatibility
                    for col in df_copy.columns:
                        if df_copy[col].dtype == 'object' and col not in ['Variant Inventory Qty', 'Variant Price', 'Cost per item']:
                            df_copy[col] = df_copy[col].astype(str)
                    normalized_data.append(df_copy)
                
                # Combine data
                try:
                    combined_df = pd.concat(normalized_data, ignore_index=True)
                except Exception as e:
                    st.error(f"Error combining data: {str(e)}")
                    st.info("This usually happens when suppliers have different data types. Trying alternative method...")
                    
                    # Alternative: combine with string conversion
                    combined_df = pd.DataFrame()
                    for df in normalized_data:
                        if combined_df.empty:
                            combined_df = df.copy()
                        else:
                            # Ensure all columns exist in both DataFrames
                            all_columns = set(combined_df.columns) | set(df.columns)
                            for col in all_columns:
                                if col not in combined_df.columns:
                                    combined_df[col] = ""
                                if col not in df.columns:
                                    df[col] = ""
                            
                            # Reorder columns to match
                            df = df.reindex(columns=combined_df.columns, fill_value="")
                            combined_df = pd.concat([combined_df, df], ignore_index=True)
                
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