"""
Streamlit UI components for different application tabs.
"""

import streamlit as st
import pandas as pd
import os
from typing import List, Dict, Any, Optional, Tuple
import io

from ..core.file_handler import extract_shopify_columns, detect_supplier, load_files_from_suppliers_folder, create_file_from_path
from ..data.manager import SupplierManager, QuotingManager
from ..utils.config import ConfigManager
from .styling import show_mapping_status


class ShopifyTemplateTab:
    """Handles the Shopify template configuration tab."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def render(self) -> bool:
        """Render the Shopify template tab and return whether template is configured."""
        st.header("🏪 Shopify CSV Template")
        
        shopify_fields = self.config_manager.load_shopify_template()
        shopify_configured = len(shopify_fields) > 0
        
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
                        self.config_manager.save_shopify_template(columns)
                        st.success("🎉 Shopify template saved! Please refresh the page to continue.")
                        st.balloons()
                        if 'update_template' in st.session_state:
                            del st.session_state.update_template
                        st.rerun()
                else:
                    st.error("❌ Could not read columns from the file. Please check the file format.")
        
        return shopify_configured


class UploadTab:
    """Handles the file upload and supplier management tab."""
    
    def __init__(self, config_manager: ConfigManager, supplier_manager: SupplierManager):
        self.config_manager = config_manager
        self.supplier_manager = supplier_manager
    
    def render(self, shopify_configured: bool):
        """Render the upload tab."""
        if not shopify_configured:
            st.header("📁 Upload Supplier Files (Disabled)")
            st.warning("⚠️ Please configure your Shopify template first in the 'Shopify Template' tab.")
            return
        
        st.header("📁 Get Supplier Data")
        st.markdown("*Choose how to get your supplier data files for processing*")
        
        # Auto-download section
        self._render_auto_download_section()
        
        # Load from downloaded files section
        self._render_load_files_section()
        
        # Manual upload section
        self._render_manual_upload_section()
        
        # Supplier management section
        self._render_supplier_management_section()
        
        # Show current files status
        self._show_current_files_status()
    
    def _render_auto_download_section(self):
        """Render the auto-download section."""
        supplier_config = self.supplier_manager.get_all_suppliers()
        
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
            
            if selected_suppliers and st.button("⬇️ Download to Suppliers Folder", type="primary"):
                self.supplier_manager.download_to_suppliers_folder(selected_suppliers, supplier_config)
            
            st.divider()
    
    def _render_load_files_section(self):
        """Render the load files section."""
        supplier_files = load_files_from_suppliers_folder()
        
        if supplier_files:
            st.markdown("### 📂 Load Downloaded Files")
            st.markdown("*Use previously downloaded files from the suppliers folder*")
            
            # Show available files
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
                        file_content = create_file_from_path(file_path)
                        if file_content:
                            loaded_files.append(file_content)
                        else:
                            st.error(f"Error loading {display_name}")
                    
                    if loaded_files:
                        st.session_state.uploaded_files = loaded_files
                        st.success(f"🎉 Loaded {len(loaded_files)} files successfully!")
            
            with col_count:
                st.info(f"📊 {len(supplier_files)} file{'s' if len(supplier_files) != 1 else ''} available")
            
            st.divider()
    
    def _render_manual_upload_section(self):
        """Render the manual upload section."""
        st.markdown("### 📤 Manual File Upload")
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
    
    def _render_supplier_management_section(self):
        """Render the supplier management section."""
        st.markdown("### ⚙️ Manage Supplier URLs")
        st.markdown("*Add, edit, or remove supplier download URLs*")
        
        with st.expander("🔧 Supplier Configuration", expanded=False):
            # Add new supplier
            self._render_add_supplier_form()
            
            # Edit existing suppliers
            self._render_edit_suppliers_section()
    
    def _render_add_supplier_form(self):
        """Render the add new supplier form."""
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
                    if self.supplier_manager.add_supplier(new_supplier_key, new_supplier_name, 
                                                        new_supplier_url, new_supplier_filename):
                        st.success(f"✅ Added {new_supplier_name} successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Supplier '{new_supplier_key}' already exists")
                else:
                    st.error("❌ Please fill in all fields")
    
    def _render_edit_suppliers_section(self):
        """Render the edit existing suppliers section."""
        supplier_config = self.supplier_manager.get_all_suppliers()
        
        if supplier_config:
            st.markdown("**Edit Existing Suppliers:**")
            for key, config in supplier_config.items():
                with st.container():
                    st.markdown(f"**{config['name']}** (`{key}`)")
                    col_edit1, col_edit2 = st.columns([2, 2])
                    
                    with col_edit1:
                        new_name = st.text_input(f"Name###{key}", value=config['name'], key=f"name_{key}")
                        new_url = st.text_input(f"URL###{key}", value=config['url'], key=f"url_{key}")
                    
                    with col_edit2:
                        new_filename = st.text_input(f"Filename###{key}", value=config['filename'], key=f"filename_{key}")
                        
                        col_update, col_delete = st.columns(2)
                        with col_update:
                            if st.button(f"💾 Update", key=f"update_{key}", type="secondary"):
                                if self.supplier_manager.update_supplier(key, new_name, new_url, new_filename):
                                    st.success(f"✅ Updated {new_name}!")
                                    st.rerun()
                        
                        with col_delete:
                            if st.button(f"🗑️ Remove", key=f"delete_{key}", type="secondary"):
                                if self.supplier_manager.remove_supplier(key):
                                    st.success(f"✅ Removed supplier!")
                                    st.rerun()
                    
                    st.divider()
    
    def _show_current_files_status(self):
        """Show current files ready for processing."""
        if 'uploaded_files' in st.session_state and st.session_state.uploaded_files:
            st.divider()
            st.write("**📋 Current Files Ready for Processing:**")
            for file in st.session_state.uploaded_files:
                supplier = detect_supplier(file.name)
                st.write(f"✅ {file.name} - {supplier or 'Unknown supplier'}")


class MappingTab:
    """Handles the column mapping tab."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def render(self, shopify_configured: bool):
        """Render the mapping tab."""
        if not shopify_configured:
            st.header("🔗 Map Columns (Disabled)")
            st.warning("⚠️ Please configure your Shopify template first.")
            return
        elif 'uploaded_files' not in st.session_state:
            st.header("🔗 Map Columns")
            st.warning("⚠️ Please upload supplier files first.")
            return
        
        st.header("🔗 Map Supplier Columns to Shopify")
        
        # File selection
        file_names = [f.name for f in st.session_state.uploaded_files]
        selected_file = st.selectbox("Select file:", file_names)
        
        if selected_file:
            self._render_mapping_interface(selected_file)
    
    def _render_mapping_interface(self, selected_file: str):
        """Render the mapping interface for a selected file."""
        try:
            file = next(f for f in st.session_state.uploaded_files if f.name == selected_file)
            supplier = st.text_input("Supplier name:", detect_supplier(selected_file) or "")
        except StopIteration:
            st.error(f"Could not find file {selected_file} in uploaded files")
            return
        
        if not supplier or file is None:
            return
        
        from ..core.file_handler import read_file
        df = read_file(file)
        if df is None:
            st.error("❌ Could not read the selected file. Please check the file format or try re-downloading.")
            return
        
        # Get mapping data
        supplier_columns = [""] + list(df.columns)
        shopify_fields = self.config_manager.load_shopify_template()
        mappings = self.config_manager.load_mappings()
        existing = mappings.get(supplier, {})
        
        # Show mapping status
        self._show_mapping_status_summary(shopify_fields, existing)
        
        # Render mapping form
        mapping = self._render_mapping_form(shopify_fields, supplier_columns, existing, supplier)
        
        # Save mapping
        if st.button("💾 Save Mapping"):
            self._save_mapping(mapping, supplier, mappings)
    
    def _show_mapping_status_summary(self, shopify_fields: List[str], existing: Dict[str, str]):
        """Show mapping status summary."""
        st.subheader("Column Mappings")
        
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
            st.metric("⚠️ Missing Important", len(important_missing), 
                     delta=f"-{len(important_missing)}" if important_missing else None)
        
        if important_missing:
            st.error(f"🚨 **Critical fields missing:** {', '.join(important_missing)}")
        else:
            st.success("✅ **All critical fields are mapped!**")
        
        st.info("💡 **Color Guide:** 🟢 Green = Mapped | 🟡 Yellow = Required | 🔴 Red = Missing")
    
    def _render_mapping_form(self, shopify_fields: List[str], supplier_columns: List[str], 
                           existing: Dict[str, str], supplier: str) -> Dict[str, str]:
        """Render the mapping form and return the mapping dictionary."""
        # Initialize mapping with existing data
        mapping = existing.copy() if existing else {}
        mapping["_file_keyword"] = st.text_input(
            "🔍 File keyword (for auto-detection):", 
            value=existing.get("_file_keyword", supplier.lower()),
            help="This keyword will be used to automatically detect files from this supplier"
        )
        
        # Create columns for better layout
        col1, col2 = st.columns(2)
        
        # Map all Shopify fields
        actual_shopify_fields = [field for field in shopify_fields if field != "_file_keyword"]
        important_fields = ["Variant SKU", "Title", "Variant Price", "Cost per item", "Variant Inventory Qty"]
        
        for i, field in enumerate(actual_shopify_fields):
            with col1 if i % 2 == 0 else col2:
                current_mapping = mapping.get(field, "") or existing.get(field, "")
                current_custom = mapping.get(f"{field}_custom", "") or existing.get(f"{field}_custom", "")
                
                # Show field status
                header_html = show_mapping_status(field, current_mapping, current_custom, important_fields)
                st.markdown(header_html, unsafe_allow_html=True)
                
                # Add helpful notes for special fields
                self._show_field_help(field)
                
                # Mapping type selection
                mapping_type = st.radio(
                    f"How to set {field}:",
                    ["📋 Map from supplier column", "📝 Enter custom text", "❌ Leave empty"],
                    key=f"{field}_type",
                    horizontal=True,
                    index=0 if current_mapping and current_mapping in supplier_columns else (1 if current_custom else 2)
                )
                
                # Handle mapping based on type
                mapping = self._handle_mapping_type(mapping, field, mapping_type, supplier_columns, 
                                                 current_mapping, current_custom)
                
                st.markdown("---")
        
        return mapping
    
    def _show_field_help(self, field: str):
        """Show helpful information for special fields."""
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
    
    def _handle_mapping_type(self, mapping: Dict[str, str], field: str, mapping_type: str, 
                           supplier_columns: List[str], current_mapping: str, current_custom: str) -> Dict[str, str]:
        """Handle different mapping types and update the mapping dictionary."""
        if mapping_type == "📋 Map from supplier column":
            if field == "Tags":
                # Special handling for Tags field - allow multiple columns
                current_tag_columns = current_mapping.split(',') if current_mapping else []
                current_tag_columns = [col.strip() for col in current_tag_columns if col.strip() in supplier_columns]
                
                selected_columns = st.multiselect(
                    f"Select columns for {field}:",
                    supplier_columns[1:],  # Exclude empty option
                    default=current_tag_columns,
                    key=f"{field}_multiselect",
                    help="Select multiple columns to combine for tags. They will be processed and cleaned automatically."
                )
                
                mapping[field] = ','.join(selected_columns) if selected_columns else ''
                
                if selected_columns:
                    st.info(f"🏷️ Will generate tags from: {', '.join(selected_columns)}")
            else:
                # Regular single column selection
                mapping[field] = st.selectbox(
                    f"Select column for {field}:",
                    supplier_columns,
                    index=supplier_columns.index(current_mapping) if current_mapping in supplier_columns else 0,
                    key=f"{field}_select",
                    help=f"Map to your supplier column for {field}"
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
        
        return mapping
    
    def _save_mapping(self, mapping: Dict[str, str], supplier: str, mappings: Dict[str, Dict[str, str]]):
        """Save the mapping configuration."""
        # Clean mapping - keep file keyword, non-empty values, and custom text
        clean_mapping = {}
        for k, v in mapping.items():
            if k == "_file_keyword":
                clean_mapping[k] = v
            elif k.endswith('_custom') and v:
                clean_mapping[k] = v
            elif not k.endswith('_custom') and v:
                clean_mapping[k] = v
        
        mappings[supplier] = clean_mapping
        self.config_manager.save_mappings(mappings)
        st.session_state.supplier_mappings = mappings
        st.success(f"✅ Saved mapping for {supplier}")
        
        # Show summary of what was saved
        column_mappings = sum(1 for k, v in clean_mapping.items() 
                            if not k.endswith('_custom') and not k == '_file_keyword' and v)
        custom_mappings = sum(1 for k, v in clean_mapping.items() if k.endswith('_custom') and v)
        st.info(f"📊 Saved {column_mappings} column mappings and {custom_mappings} custom text fields")