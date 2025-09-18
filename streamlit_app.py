import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import re

# Utility functions
def extract_quantity(qty_value):
    """Extract quantity as a number from various text formats"""
    if pd.isna(qty_value) or qty_value == "":
        return 0
    
    qty_str = str(qty_value).strip().upper()
    
    # Handle common text indicators
    if qty_str in ["IN STOCK", "AVAILABLE", "YES", "TRUE"]:
        return 999
    if qty_str in ["OUT OF STOCK", "NO", "FALSE", "DISCONTINUED"]:
        return 0
    
    # Remove special characters but keep digits and comparison operators
    qty_cleaned = re.sub(r'[^\d><+=\-.]', '', qty_str)
    
    # Handle greater than cases (>20, 20+, etc.)
    if '>' in qty_str or '+' in qty_str:
        numbers = re.findall(r'\d+', qty_cleaned)
        if numbers:
            return int(numbers[0]) + 1
        return 999
    
    # Handle less than cases
    if '<' in qty_str:
        numbers = re.findall(r'\d+', qty_cleaned)
        if numbers:
            return max(0, int(numbers[0]) - 1)
        return 0
    
    # Extract pure numbers
    numbers = re.findall(r'\d+\.?\d*', qty_cleaned)
    if numbers:
        try:
            return int(float(numbers[0]))
        except ValueError:
            return 0
    
    return 0

def save_supplier_mapping(supplier_name, mapping, supplier_mappings):
    """Save supplier mapping to JSON file"""
    try:
        # Remove empty mappings
        mapping = {k: v for k, v in mapping.items() if v != ""}
        supplier_mappings[supplier_name] = mapping
        
        with open('mappings/supplier_mappings.json', 'w') as f:
            json.dump(supplier_mappings, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving mapping: {str(e)}")
        return False

def delete_supplier_mapping(supplier_name, supplier_mappings):
    """Delete supplier mapping from JSON file"""
    try:
        if supplier_name in supplier_mappings:
            del supplier_mappings[supplier_name]
            with open('mappings/supplier_mappings.json', 'w') as f:
                json.dump(supplier_mappings, f, indent=4)
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting mapping: {str(e)}")
        return False

def process_supplier_file(uploaded_file, supplier_config, item_data):
    """Process a single supplier file and update item_data"""
    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        
        # Extract column information
        item_code_col = supplier_config["item_code_col"]
        price_col = supplier_config["price_col"]
        rrp_col = supplier_config.get("rrp_col")
        description_col = supplier_config.get("description_col")
        image_url_col = supplier_config.get("image_url_col")
        qty_col = supplier_config.get("qty_col")
        supplier_name = supplier_config["name"]

        # Validate required columns
        missing_cols = []
        if item_code_col not in df.columns:
            missing_cols.append(item_code_col)
        if price_col not in df.columns:
            missing_cols.append(price_col)
        
        if missing_cols:
            return False, f"Missing columns: {', '.join(missing_cols)}", 0, 0

        # Process data
        df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
        df = df.dropna(subset=[price_col])
        
        rows_processed = 0
        for index, row in df.iterrows():
            item_code = str(row[item_code_col]).strip()
            if not item_code or item_code == 'nan':
                continue
                
            price = row[price_col]
            rrp = row[rrp_col] if rrp_col and rrp_col in df.columns else 0
            description = str(row[description_col]) if description_col and description_col in df.columns else ""
            image_url = str(row[image_url_col]) if image_url_col and image_url_col in df.columns else ""
            
            # Add quantity extraction
            quantity = 0
            if qty_col and qty_col in df.columns:
                quantity = extract_quantity(row[qty_col])
            
            # Update item data with cheapest price logic
            if item_code in item_data:
                if price < item_data[item_code]["Cheapest Price"]:
                    item_data[item_code] = {
                        "Cheapest Price": price,
                        "Supplier": supplier_name,
                        "RRP": rrp,
                        "Description": description,
                        "ImageURL": image_url,
                        "Quantity": quantity
                    }
            else:
                item_data[item_code] = {
                    "Cheapest Price": price,
                    "Supplier": supplier_name,
                    "RRP": rrp,
                    "Description": description,
                    "ImageURL": image_url,
                    "Quantity": quantity
                }
            rows_processed += 1
        
        return True, f"Successfully processed", rows_processed, len(df)
        
    except Exception as e:
        return False, str(e), 0, 0

# Page configuration
st.set_page_config(
    page_title="ETEC+ Supplier Datafeeds",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f8ff, #e6f3ff);
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
    
    .success-message {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        color: #155724;
    }
    
    .warning-message {
        padding: 1rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        color: #856404;
    }
    
    .info-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Create mappings directory if it doesn't exist
os.makedirs('mappings', exist_ok=True)

# Initialize session state
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'last_processed_files' not in st.session_state:
    st.session_state.last_processed_files = []
if 'item_data' not in st.session_state:
    st.session_state.item_data = {}

# Load Shopify template and supplier mappings
@st.cache_data
def load_mappings():
    """Load Shopify template and supplier mappings from JSON files"""
    try:
        with open('mappings/shopify_template.json', 'r') as f:
            shopify_template = json.load(f)
    except FileNotFoundError:
        st.error("⚠️ Shopify template file not found. Please ensure shopify_template.json exists in mappings folder.")
        st.stop()
    
    try:
        with open('mappings/supplier_mappings.json', 'r') as f:
            supplier_mappings = json.load(f)
    except FileNotFoundError:
        # Create empty supplier mappings if file doesn't exist
        supplier_mappings = {}
        with open('mappings/supplier_mappings.json', 'w') as f:
            json.dump(supplier_mappings, f, indent=4)
    
    return shopify_template, supplier_mappings

shopify_template, supplier_mappings = load_mappings()

# Main header
st.markdown('<div class="main-header">📊 ETEC+ Supplier Datafeeds Mapping</div>', unsafe_allow_html=True)

# Sidebar with improved navigation
st.sidebar.markdown("## 🔧 Configuration Panel")

# Quick stats in sidebar
if supplier_mappings:
    st.sidebar.markdown("### 📈 Quick Stats")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Suppliers", len(supplier_mappings))
    with col2:
        st.metric("Fields", len(shopify_template["template_columns"]))

# Supplier management section with tabs
st.sidebar.markdown("---")
supplier_tab = st.sidebar.radio(
    "**Supplier Management**",
    ["➕ Add New", "👁️ View/Edit", "🗑️ Delete"],
    key="supplier_management"
)

if supplier_tab == "➕ Add New":
    st.sidebar.markdown("**Add New Supplier**")
    new_supplier_name = st.sidebar.text_input("Supplier Name", placeholder="Enter supplier name...")
    file_keyword = st.sidebar.text_input(
        "File Keyword", 
        value=new_supplier_name,
        help="This keyword will be used to match CSV files",
        placeholder="e.g., 'auscomp', 'leaders'"
    )
    
    # File uploader with better instructions
    st.sidebar.markdown("**📁 Upload Sample File**")
    sample_file = st.sidebar.file_uploader(
        "Choose a sample CSV/Excel file to map headers",
        type=["csv", "xlsx", "xls"],
        help="Upload a sample file to automatically detect column headers"
    )
    
    if sample_file and new_supplier_name:
        try:
            # Show file info
            file_size = sample_file.size / 1024  # KB
            st.sidebar.info(f"📄 File: {sample_file.name} ({file_size:.1f} KB)")
            
            # Read the file
            if sample_file.name.endswith('.csv'):
                df = pd.read_csv(sample_file)
            else:
                df = pd.read_excel(sample_file)
            
            # Get all columns from the file
            available_columns = df.columns.tolist()
            
            mapping = {}
            mapping["_file_keyword"] = file_keyword
            
            # Main content area for mapping
            st.markdown("## 🔗 Column Mapping")
            st.markdown("Map your supplier columns to Shopify fields:")
            
            st.info("""
            📋 **Required Shopify Fields Information:**
            
            All fields marked as "Required" are mandatory by Shopify, but will use default values if not mapped:
            - **Handle**: Auto-generated from Title if not mapped
            - **Vendor**: Uses supplier name if not mapped  
            - **Published**: Defaults to "true"
            - **Option1 Name/Value**: Defaults to "Title"/"Default Title"
            - **Variant Price**: Must be mapped for pricing
            - **Variant Inventory Qty**: Uses extracted quantity or 0
            - **Status**: Defaults to "active"
            
            You only need to map the fields that contain actual data from your supplier.
            """)
            
            # Progress indicator
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Get all fields from Shopify template
            shopify_fields = shopify_template["template_columns"]
            
            # Create tabs for better organization
            essential_fields = [
                "Handle", "Vendor", "Published", "Option1 Name", "Option1 Value", 
                "Variant Grams", "Variant Inventory Qty", "Variant Inventory Policy", 
                "Variant Fulfillment Service", "Variant Price", "Variant Requires Shipping", 
                "Variant Taxable", "Gift Card", "Variant Weight Unit", 
                "Included / United States", "Included / International", "Status"
            ]
            optional_fields = [field for field in shopify_fields if field not in essential_fields]
            
            tab1, tab2 = st.tabs(["🎯 Required Fields (Shopify)", "⚙️ Optional Fields"])
            
            with tab1:
                st.markdown("### Required Shopify Fields")
                st.info("⚠️ These fields are required by Shopify. Default values will be used if left unmapped.")
                cols = st.columns(2)
                for i, field in enumerate(essential_fields):
                    with cols[i % 2]:
                        column_options = [""] + available_columns
                        mapping[field] = st.selectbox(
                            f"**{field}**",
                            options=column_options,
                            help=f"Required: {field} - Map to your supplier column or leave blank for default",
                            key=f"essential_{field}"
                        )
            
            with tab2:
                st.markdown("### Additional Shopify fields")
                cols = st.columns(3)
                for i, field in enumerate(optional_fields):
                    with cols[i % 3]:
                        column_options = [""] + available_columns
                        mapping[field] = st.selectbox(
                            field,
                            options=column_options,
                            help=f"Select the column that corresponds to Shopify's {field}",
                            key=f"optional_{field}"
                        )
            
            # Update progress
            mapped_fields = sum(1 for v in mapping.values() if v != "")
            progress = mapped_fields / len(shopify_fields)
            progress_bar.progress(progress)
            status_text.text(f"Mapped {mapped_fields}/{len(shopify_fields)} fields")
            
            # Show data preview in an expandable section
            with st.expander("📋 Data Preview", expanded=False):
                st.dataframe(df.head(), use_container_width=True)
                st.caption(f"Showing first 5 rows of {len(df)} total rows")
            
            # Save button with validation
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💾 Save Supplier Mapping", type="primary", use_container_width=True):
                    if new_supplier_name not in supplier_mappings:
                        # Since all Shopify required fields have defaults, we just need basic product info
                        basic_fields_mapped = any(mapping.get(field, "") != "" for field in ["Title", "Variant SKU", "Variant Price", "Vendor"])
                        if basic_fields_mapped:
                            if save_supplier_mapping(new_supplier_name, mapping, supplier_mappings):
                                st.success(f"✅ Successfully added supplier: {new_supplier_name}")
                                st.balloons()
                                # Clear cache to reload mappings
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            st.error("❌ Please map at least one of: Title, Variant SKU, Variant Price, or Vendor")
                    else:
                        st.error("❌ Supplier already exists!")
            
            with col2:
                if st.button("🔄 Reset Mapping", use_container_width=True):
                    st.rerun()
                    
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            st.info("💡 Please make sure the file is a valid CSV or Excel file.")

elif supplier_tab == "👁️ View/Edit":
    st.sidebar.markdown("**View/Edit Suppliers**")
    if supplier_mappings:
        selected_supplier = st.sidebar.selectbox(
            "Select Supplier",
            options=list(supplier_mappings.keys()),
            key="view_supplier"
        )
        
        if selected_supplier:
            st.sidebar.markdown(f"**Mapping for {selected_supplier}:**")
            mapping_data = supplier_mappings[selected_supplier]
            
            # Show mapping in a nice format
            for shopify_field, supplier_field in mapping_data.items():
                if supplier_field and shopify_field != "_file_keyword":
                    st.sidebar.text(f"• {shopify_field} ← {supplier_field}")
    else:
        st.sidebar.info("No suppliers configured yet.")

elif supplier_tab == "🗑️ Delete":
    st.sidebar.markdown("**Delete Supplier**")
    if supplier_mappings:
        supplier_to_delete = st.sidebar.selectbox(
            "Select supplier to delete",
            options=list(supplier_mappings.keys()),
            key="supplier_delete"
        )
        
        st.sidebar.warning("⚠️ This action cannot be undone!")
        
        if st.sidebar.button("🗑️ Delete Selected Supplier", type="secondary"):
            if delete_supplier_mapping(supplier_to_delete, supplier_mappings):
                st.success(f"✅ Successfully deleted supplier: {supplier_to_delete}")
                st.cache_data.clear()
                st.rerun()
    else:
        st.sidebar.info("No suppliers to delete.")

# Main content area
st.markdown("---")

# Define suppliers list from mappings
suppliers = [
    {
        "name": supplier,
        "file_keyword": supplier_mappings[supplier].get("_file_keyword", supplier),
        "item_code_col": supplier_mappings[supplier].get("Variant SKU", ""),
        "price_col": supplier_mappings[supplier].get("Cost per item", ""),
        "rrp_col": supplier_mappings[supplier].get("Variant Compare At Price", ""),
        "description_col": supplier_mappings[supplier].get("Title", ""),
        "image_url_col": supplier_mappings[supplier].get("Image Src", ""),
        "qty_col": supplier_mappings[supplier].get("Variant Inventory Qty", "")  # Add this line
    } for supplier in supplier_mappings
]

# File upload section with improved UI
st.markdown("## 📤 Upload Data Files")

if not suppliers:
    st.warning("⚠️ No suppliers configured. Please add suppliers first using the sidebar.")
else:
    # Show configured suppliers
    with st.expander("📋 Configured Suppliers", expanded=False):
        cols = st.columns(min(len(suppliers), 3))
        for i, supplier in enumerate(suppliers):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="info-box">
                    <strong>{supplier['name']}</strong><br>
                    <small>Keyword: {supplier['file_keyword']}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # File uploader with better instructions
    st.markdown("### 📁 Select Files to Process")
    uploaded_files = st.file_uploader(
        "Choose CSV files from your suppliers",
        type="csv",
        accept_multiple_files=True,
        help="Upload multiple CSV files. Files will be matched to suppliers based on filename keywords."
    )

    if uploaded_files:
        # Show file information
        st.markdown("### 📊 File Analysis")
        
        file_info_cols = st.columns(min(len(uploaded_files), 4))
        total_size = 0
        
        for i, file in enumerate(uploaded_files):
            file_size = file.size / (1024 * 1024)  # MB
            total_size += file_size
            
            with file_info_cols[i % 4]:
                # Match file to supplier
                matched_supplier = None
                for supplier in suppliers:
                    if supplier["file_keyword"].lower() in file.name.lower():
                        matched_supplier = supplier["name"]
                        break
                
                status_color = "🟢" if matched_supplier else "🔴"
                st.markdown(f"""
                <div class="info-box">
                    {status_color} <strong>{file.name}</strong><br>
                    <small>Size: {file_size:.1f} MB</small><br>
                    <small>Supplier: {matched_supplier or 'Unknown'}</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.info(f"📈 Total files: {len(uploaded_files)} | Total size: {total_size:.1f} MB")
        
        # Process files button
        if st.button("🚀 Process Files", type="primary", use_container_width=True):
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize data storage
            item_data = {}
            processing_errors = []
            processed_files = []
            
            # Process each uploaded file
            for file_idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}...")
                progress_bar.progress((file_idx) / len(uploaded_files))
                
                # Check file size
                file_size = uploaded_file.size / (1024 * 1024)  # Convert to MB
                if file_size > 500:  # Based on config.toml
                    processing_errors.append(f"❌ {uploaded_file.name}: File too large ({file_size:.2f} MB)")
                    continue

                try:
                    # Read the CSV file
                    df = pd.read_csv(uploaded_file)
                    
                    # Determine supplier configuration
                    supplier_config = None
                    for supplier in suppliers:
                        if supplier["file_keyword"].lower() in uploaded_file.name.lower():
                            supplier_config = supplier
                            break
                    
                    if not supplier_config:
                        processing_errors.append(f"❌ {uploaded_file.name}: No matching supplier configuration")
                        continue

                    # Process the file
                    success, message, rows_processed, total_rows = process_supplier_file(
                        uploaded_file, supplier_config, item_data
                    )
                    
                    if success:
                        processed_files.append({
                            "name": uploaded_file.name,
                            "supplier": supplier_config["name"],
                            "rows": rows_processed,
                            "total_rows": total_rows
                        })
                    else:
                        processing_errors.append(f"❌ {uploaded_file.name}: {message}")
                        
                except Exception as e:
                    processing_errors.append(f"❌ {uploaded_file.name}: {str(e)}")
            
            # Complete progress
            progress_bar.progress(1.0)
            status_text.text("Processing complete!")
            
            # Show processing results
            if processing_errors:
                st.markdown("### ⚠️ Processing Errors")
                for error in processing_errors:
                    st.error(error)
            
            if processed_files:
                st.markdown("### ✅ Successfully Processed Files")
                for file_info in processed_files:
                    st.success(f"📄 {file_info['name']} ({file_info['supplier']}): {file_info['rows']}/{file_info['total_rows']} rows")
            
            # Display results if we have data
            if item_data:
                st.session_state.processing_complete = True
                st.session_state.item_data = item_data
                st.session_state.processed_files = processed_files
                
                # Show summary statistics
                st.markdown("### 📊 Processing Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Items", len(item_data))
                with col2:
                    suppliers_used = len(set(data["Supplier"] for data in item_data.values()))
                    st.metric("Suppliers Used", suppliers_used)
                with col3:
                    avg_price = sum(data["Cheapest Price"] for data in item_data.values()) / len(item_data)
                    st.metric("Avg Price", f"${avg_price:.2f}")
                with col4:
                    total_files = len(processed_files)
                    st.metric("Files Processed", total_files)

# Display results if processing is complete
if st.session_state.processing_complete and 'item_data' in st.session_state:
    item_data = st.session_state.item_data
    
    st.markdown("---")
    st.markdown("## 📋 Results")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["🛒 Shopify Format", "📊 Analysis", "📈 Charts"])
    
    with tab1:
        # Convert to Shopify format
        shopify_data = []
        
        for item_code, data in item_data.items():
            supplier_name = data["Supplier"]
            supplier_mapping = supplier_mappings[supplier_name]
            
            shopify_row = {col: "" for col in shopify_template["template_columns"]}
            
            # Generate handle from description
            title = data["Description"] if data["Description"] else item_code
            handle = title.lower().replace(" ", "-").replace("/", "-")[:60] if title else item_code.lower()
            shopify_row["Handle"] = handle
            
            # Set required field defaults first
            shopify_row["Published"] = "true"
            shopify_row["Option1 Name"] = "Title"
            shopify_row["Option1 Value"] = "Default Title"
            shopify_row["Variant Grams"] = "0"
            shopify_row["Variant Inventory Qty"] = data.get("Quantity", 0)
            shopify_row["Variant Inventory Policy"] = "deny"
            shopify_row["Variant Fulfillment Service"] = "manual"
            shopify_row["Variant Requires Shipping"] = "true"
            shopify_row["Variant Taxable"] = "true"
            shopify_row["Gift Card"] = "false"
            shopify_row["Variant Weight Unit"] = "kg"
            shopify_row["Included / United States"] = "true"
            shopify_row["Included / International"] = "true"
            shopify_row["Status"] = "active"
            
            # Map the data using supplier mapping
            for shopify_col, supplier_col in supplier_mapping.items():
                if shopify_col == "_file_keyword":
                    continue
                    
                if supplier_col in ["Price", "ExTax", "DBP"]:
                    shopify_row[shopify_col] = data["Cheapest Price"]
                elif supplier_col == "RRP":
                    shopify_row[shopify_col] = data["RRP"]
                elif supplier_col == "Description":
                    shopify_row[shopify_col] = data["Description"]
                elif supplier_col in ["Image", "IMAGE"]:
                    shopify_row[shopify_col] = data["ImageURL"]
                elif shopify_col == "Variant SKU":
                    shopify_row[shopify_col] = item_code
                elif shopify_col == "Variant Inventory Qty":
                    shopify_row[shopify_col] = data.get("Quantity", 0)
                elif shopify_col == "Handle":
                    # Use mapped value if available, otherwise use generated handle
                    if supplier_col and supplier_col in df.columns:
                        custom_handle = str(data.get(supplier_col, "")).lower().replace(" ", "-")[:60]
                        if custom_handle:
                            shopify_row[shopify_col] = custom_handle
                elif shopify_col == "Vendor":
                    # Use mapped vendor or supplier name as default
                    shopify_row[shopify_col] = data.get("Vendor", supplier_name)
                else:
                    # For any other mapped field, use the value from data
                    if supplier_col in data:
                        shopify_row[shopify_col] = data[supplier_col]
            
            shopify_data.append(shopify_row)
        
        # Convert to DataFrame
        shopify_df = pd.DataFrame(shopify_data)
        
        # Display with better formatting
        st.markdown("### 🛒 Shopify Import Format")
        st.info("✅ All required Shopify fields are included with proper defaults. Ready for import!")
        st.dataframe(shopify_df, use_container_width=True, height=400)
        
        # Download section
        col1, col2 = st.columns([2, 1])
        with col1:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shopify_import_{timestamp}.csv"
            csv = shopify_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Shopify CSV",
                data=csv,
                file_name=filename,
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
        with col2:
            st.metric("Records", len(shopify_df))
    
    with tab2:
        st.markdown("### 📊 Data Analysis")
        
        # Create comparison DataFrame
        comparison_df = pd.DataFrame([
            {
                "Item Code": item_code,
                "Cheapest Price": data["Cheapest Price"],
                "Supplier": data["Supplier"],
                "RRP": data["RRP"],
                "Quantity": data.get("Quantity", 0),
                "Description": data["Description"][:50] + "..." if len(data["Description"]) > 50 else data["Description"],
                "Has Image": "Yes" if data["ImageURL"] else "No"
            }
            for item_code, data in item_data.items()
        ])
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            supplier_filter = st.multiselect(
                "Filter by Supplier",
                options=comparison_df["Supplier"].unique(),
                default=comparison_df["Supplier"].unique()
            )
        with col2:
            price_range = st.slider(
                "Price Range",
                min_value=float(comparison_df["Cheapest Price"].min()),
                max_value=float(comparison_df["Cheapest Price"].max()),
                value=(float(comparison_df["Cheapest Price"].min()), float(comparison_df["Cheapest Price"].max()))
            )
        
        # Apply filters
        filtered_df = comparison_df[
            (comparison_df["Supplier"].isin(supplier_filter)) &
            (comparison_df["Cheapest Price"] >= price_range[0]) &
            (comparison_df["Cheapest Price"] <= price_range[1])
        ]
        
        st.dataframe(filtered_df, use_container_width=True, height=400)
        
        # Summary stats
        st.markdown("### 📈 Summary Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Items in Filter", len(filtered_df))
        with col2:
            if len(filtered_df) > 0:
                st.metric("Avg Price", f"${filtered_df['Cheapest Price'].mean():.2f}")
        with col3:
            if len(filtered_df) > 0:
                st.metric("Price Range", f"${filtered_df['Cheapest Price'].min():.2f} - ${filtered_df['Cheapest Price'].max():.2f}")
    
    with tab3:
        st.markdown("### 📈 Data Visualization")
        
        if len(item_data) > 0:
            # Simple charts using Streamlit's built-in charting
            st.markdown("#### Price Distribution by Supplier")
            supplier_price_data = comparison_df.groupby('Supplier')['Cheapest Price'].agg(['mean', 'min', 'max', 'count']).reset_index()
            st.dataframe(supplier_price_data, use_container_width=True)
            
            # Bar chart of item counts by supplier
            st.markdown("#### Items Count by Supplier")
            supplier_counts = comparison_df["Supplier"].value_counts()
            st.bar_chart(supplier_counts)
            
            # Line chart of price distribution
            st.markdown("#### Price Distribution")
            price_bins = pd.cut(comparison_df['Cheapest Price'], bins=20)
            price_hist = price_bins.value_counts().sort_index()
            st.line_chart(price_hist)
            
            # Additional statistics table
            st.markdown("#### Detailed Statistics by Supplier")
            detailed_stats = comparison_df.groupby('Supplier').agg({
                'Cheapest Price': ['count', 'mean', 'median', 'min', 'max', 'std'],
                'Has Image': lambda x: (x == 'Yes').sum()
            }).round(2)
            detailed_stats.columns = ['Count', 'Mean Price', 'Median Price', 'Min Price', 'Max Price', 'Std Dev', 'Items with Images']
            st.dataframe(detailed_stats, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <small>ETEC+ Supplier Datafeeds Mapping Tool | Built with Streamlit</small>
    </div>
    """,
    unsafe_allow_html=True
)
