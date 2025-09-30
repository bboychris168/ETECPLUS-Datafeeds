"""
ETEC+ Supplier Datafeeds - Refactored Main Application
A clean, modular Streamlit application for processing supplier datafeeds into Shopify format.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Import our refactored modules
from src.utils.config import ConfigManager
from src.utils.logger import AppLogger
from src.core.processor import DataProcessor
from src.data.manager import SupplierManager, QuotingManager
from src.ui.styling import (
    configure_page, apply_custom_css, show_main_header, 
    show_workflow_status, show_help_section, create_tabs
)
from src.ui.components import ShopifyTemplateTab, UploadTab, MappingTab


class ETECDatafeedsApp:
    """Main application class for ETEC+ Datafeeds."""
    
    def __init__(self):
        # Initialize configuration and logging
        self.config_manager = ConfigManager()
        
        # Initialize logging in session state if not exists
        if 'logger' not in st.session_state:
            st.session_state.logger = AppLogger()
        
        self.logger = st.session_state.logger
        
        # Initialize data managers
        self.supplier_manager = SupplierManager(self.config_manager)
        self.quoting_manager = QuotingManager(self.config_manager)
        self.data_processor = DataProcessor(self.logger)
        
        # Initialize UI components
        self.shopify_template_tab = ShopifyTemplateTab(self.config_manager)
        self.upload_tab = UploadTab(self.config_manager, self.supplier_manager)
        self.mapping_tab = MappingTab(self.config_manager)
        
        # Initialize session state
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables."""
        if 'supplier_mappings' not in st.session_state:
            st.session_state.supplier_mappings = self.config_manager.load_mappings()
        if 'update_template' not in st.session_state:
            st.session_state.update_template = False
    
    def run(self):
        """Run the main application."""
        # Configure page and styling
        configure_page()
        apply_custom_css()
        
        # Show main header
        show_main_header()
        
        # Load configuration
        shopify_fields = self.config_manager.load_shopify_template()
        shopify_configured = len(shopify_fields) > 0
        
        # Show workflow status
        show_workflow_status(shopify_configured)
        
        if not shopify_configured:
            st.warning("⚠️ Please upload your Shopify CSV template first to configure the column headers.")
        
        # Show help section
        show_help_section()
        
        # Create and handle tabs
        self._handle_tabs(shopify_configured, shopify_fields)
        
        # Show sidebar
        self._render_sidebar()
    
    def _handle_tabs(self, shopify_configured: bool, shopify_fields: list):
        """Handle the main application tabs."""
        tabs = create_tabs(shopify_configured)
        
        # Shopify Template Tab
        with tabs[0]:
            shopify_configured = self.shopify_template_tab.render()
        
        # Upload Tab
        with tabs[1]:
            self.upload_tab.render(shopify_configured)
        
        # Mapping Tab
        with tabs[2]:
            self.mapping_tab.render(shopify_configured)
        
        # Export Tab
        with tabs[3]:
            self._render_export_tab(shopify_configured, shopify_fields)
        
        # Quoting Tab
        with tabs[4]:
            self._render_quoting_tab(shopify_configured, shopify_fields)
    
    def _render_export_tab(self, shopify_configured: bool, shopify_fields: list):
        """Render the export and processing tab."""
        if not shopify_configured:
            st.header("⚡ Process & Export (Disabled)")
            st.warning("⚠️ Please configure your Shopify template first.")
            return
        elif 'uploaded_files' not in st.session_state:
            st.header("⚡ Process & Export")
            st.warning("⚠️ Please upload supplier files first.")
            return
        elif not st.session_state.supplier_mappings:
            st.header("⚡ Process & Export")
            st.warning("⚠️ Please create column mappings first.")
            return
        
        st.header("⚡ Process & Export")
        
        # Debug section
        with st.expander("🔍 Debug Info", expanded=False):
            self._show_debug_info()
        
        # Process files button
        if st.button("🚀 Process Files"):
            self._process_and_export_files(shopify_fields)
    
    def _show_debug_info(self):
        """Show debug information about uploaded files and mappings."""
        st.write("**Uploaded Files:**")
        for file in st.session_state.uploaded_files:
            from src.core.file_handler import detect_supplier
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
    
    def _process_and_export_files(self, shopify_fields: list):
        """Process uploaded files and generate export."""
        # Process files
        all_data = self.data_processor.process_files(
            st.session_state.uploaded_files, 
            st.session_state.supplier_mappings
        )
        
        if not all_data:
            st.error("❌ No data was processed. Please check your files and mappings.")
            return
        
        # Show processing details
        st.write(f"📊 Processing {len(all_data)} supplier files...")
        for i, df in enumerate(all_data):
            vendor = df['Vendor'].iloc[0] if 'Vendor' in df.columns and len(df) > 0 else f"Supplier {i+1}"
            st.write(f"📋 Supplier {i+1} ({vendor}): {len(df)} rows, {len(df.columns)} columns")
        
        # Combine data
        try:
            combined_df = self._combine_dataframes(all_data)
        except Exception as e:
            st.error(f"❌ Error combining data: {str(e)}")
            return
        
        # Remove duplicates
        final_df, duplicates_info = self.data_processor.find_and_remove_duplicates(combined_df)
        
        # Ensure all required Shopify fields are present
        actual_shopify_fields = [field for field in shopify_fields if field != "_file_keyword"]
        for field in actual_shopify_fields:
            if field not in final_df.columns:
                final_df[field] = ""
        
        # Remove _file_keyword if it exists
        if "_file_keyword" in final_df.columns:
            final_df = final_df.drop(columns=["_file_keyword"])
        
        # Generate Handle from Title if not mapped
        if 'Handle' not in final_df.columns or final_df['Handle'].isna().all():
            final_df['Handle'] = final_df['Title'].str.lower().str.replace(' ', '-').str.replace('[^a-z0-9-]', '', regex=True)
        
        st.success(f"🎉 {len(final_df)} unique products ready!")
        
        # Show duplicate removal stats
        self._show_duplicate_stats(duplicates_info)
        
        # Preview and download
        self._show_preview_and_download(final_df, duplicates_info)
    
    def _combine_dataframes(self, all_data: list) -> pd.DataFrame:
        """Combine multiple dataframes with error handling."""
        from src.core.data_processing import normalize_dataframe_types
        
        # Normalize all dataframes first
        normalized_data = []
        for i, df in enumerate(all_data):
            vendor = df['Vendor'].iloc[0] if 'Vendor' in df.columns and len(df) > 0 else f"Supplier {i+1}"
            st.write(f"🔄 Normalizing {vendor}: {len(df)} rows")
            df_normalized = normalize_dataframe_types(df)
            normalized_data.append(df_normalized)
        
        # Try pandas concat first
        try:
            st.write("🔗 Attempting to combine data...")
            combined_df = pd.concat(normalized_data, ignore_index=True)
            st.success(f"✅ Successfully combined {len(combined_df)} rows")
            return combined_df
        except Exception as e:
            st.warning(f"⚠️ Pandas concat failed: {str(e)}")
            st.info("🔧 Trying manual combination method...")
            
            # Manual combination with column alignment
            combined_df = pd.DataFrame()
            for i, df in enumerate(normalized_data):
                st.write(f"🔄 Adding supplier {i+1}...")
                
                if combined_df.empty:
                    combined_df = df.copy()
                else:
                    # Align columns
                    all_columns = list(set(combined_df.columns) | set(df.columns))
                    
                    # Add missing columns
                    for col in all_columns:
                        if col not in combined_df.columns:
                            combined_df[col] = ""
                        if col not in df.columns:
                            df[col] = ""
                    
                    # Ensure same column order
                    combined_df = combined_df.reindex(columns=all_columns, fill_value="")
                    df = df.reindex(columns=all_columns, fill_value="")
                    
                    # Force string types for non-numeric columns
                    numeric_columns = ['Variant Inventory Qty', 'Variant Price', 'Cost per item', 'Variant Grams']
                    for col in all_columns:
                        if col not in numeric_columns:
                            combined_df[col] = combined_df[col].astype(str)
                            df[col] = df[col].astype(str)
                    
                    # Combine
                    combined_df = pd.concat([combined_df, df], ignore_index=True)
                    st.write(f"   ✅ Added: {len(df)} rows. Total: {len(combined_df)} rows")
            
            return combined_df
    
    def _show_duplicate_stats(self, duplicates_info: list):
        """Show duplicate removal statistics."""
        duplicates_removed = len(duplicates_info)
        if duplicates_removed > 0:
            total_savings = sum(dup['Savings'] for dup in duplicates_info)
            st.info(f"📊 Removed {duplicates_removed} duplicates, kept lowest cost prices. Total potential savings: ${total_savings:.2f}")
            
            # Show duplicates in expandable section
            with st.expander(f"🔍 View {duplicates_removed} Removed Duplicates", expanded=False):
                if duplicates_info:
                    from src.core.data_processing import normalize_dataframe_types
                    
                    duplicates_df = pd.DataFrame(duplicates_info)
                    duplicates_df['Cost (Removed)'] = duplicates_df['Cost (Removed)'].apply(lambda x: f"${x:.2f}")
                    duplicates_df['Cost (Kept)'] = duplicates_df['Cost (Kept)'].apply(lambda x: f"${x:.2f}")
                    duplicates_df['Savings'] = duplicates_df['Savings'].apply(lambda x: f"${x:.2f}")
                    
                    display_duplicates_df = normalize_dataframe_types(duplicates_df)
                    st.dataframe(display_duplicates_df, use_container_width=True)
        else:
            st.info("📊 No duplicates found - all products have unique SKUs")
    
    def _show_preview_and_download(self, final_df: pd.DataFrame, duplicates_info: list):
        """Show data preview and download options."""
        # Preview
        st.subheader("Final Dataset Preview")
        from src.core.data_processing import normalize_dataframe_types
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
            log_file_path = self.logger.get_log_file_path()
            if log_file_path and os.path.exists(log_file_path):
                log_data = self.logger.read_log_file()
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
    
    def _render_quoting_tab(self, shopify_configured: bool, shopify_fields: list):
        """Render the quoting tab."""
        st.header("💰 Product Quoting")
        st.markdown("Search for products using variant SKUs and view product information with images.")
        
        # Initialize session state for quoting
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        
        # Check if we have mapped suppliers
        has_mapped_suppliers = bool(st.session_state.supplier_mappings)
        
        if has_mapped_suppliers and shopify_fields:
            self._render_quote_data_generation(shopify_fields)
            self._render_product_search()
        else:
            st.warning("⚠️ No supplier mappings found")
            st.info("💡 Please go to the Upload and Map tabs to set up your supplier data first")
            
            with st.expander("📋 Setup Workflow", expanded=True):
                st.markdown("""
                **To use the quoting system:**
                1. 🏪 **Shopify Template**: Upload your Shopify CSV template
                2. 📁 **Upload**: Upload supplier data files  
                3. 🔗 **Map**: Map supplier columns to Shopify fields
                4. 💰 **Quoting**: Return here to search products and find best prices
                """)
    
    def _render_quote_data_generation(self, shopify_fields: list):
        """Render the quote data generation section."""
        st.markdown("### 🔄 Automatic Data Loading")
        st.success("✅ Supplier mappings detected - automatically generating quote data")
        
        os.makedirs("quoting", exist_ok=True)
        quoting_file_path = "quoting/export_data_for_quoting.csv"
        
        col_generate, col_status = st.columns([1, 2])
        
        with col_generate:
            if st.button("🔄 Generate Quote Data", type="primary"):
                if 'uploaded_files' in st.session_state and st.session_state.uploaded_files:
                    success, message = self.quoting_manager.generate_quote_data(
                        st.session_state.uploaded_files,
                        st.session_state.supplier_mappings,
                        shopify_fields
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.session_state.quoting_data_generated = True
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ No uploaded files found. Please upload supplier files first.")
        
        with col_status:
            if os.path.exists(quoting_file_path):
                file_stats = os.stat(quoting_file_path)
                file_size = file_stats.st_size / 1024  # KB
                modified_time = pd.Timestamp.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                st.info(f"📄 Quote data available: {file_size:.1f}KB (Updated: {modified_time})")
                
                if st.button("🔄 Refresh Data", type="secondary", help="Regenerate quote data with latest mappings"):
                    st.session_state.quoting_data_generated = False
                    st.rerun()
            else:
                st.warning("⚠️ No quote data generated yet.")
                st.info("💡 Click 'Generate Quote Data' to create searchable product database")
    
    def _render_product_search(self):
        """Render the product search section."""
        st.markdown("### 🔍 Product Search")
        
        # Search input
        col_search, col_button = st.columns([3, 1])
        with col_search:
            search_input = st.text_input(
                "Enter SKU/Product Code",
                placeholder="e.g., ABC123, DEF456, GHI789",
                help="Enter one or multiple SKUs separated by commas"
            )
        
        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)
            search_button = st.button("🔍 Search Products", type="primary", use_container_width=True)
        
        # Bulk search
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
        
        # Perform search
        if search_button and search_input:
            self._perform_product_search(search_input)
    
    def _perform_product_search(self, search_input: str):
        """Perform the actual product search."""
        search_terms = [term.strip().upper() for term in search_input.replace('\n', ',').split(',') if term.strip()]
        
        if not search_terms:
            st.error("❌ Please enter at least one SKU to search")
            return
        
        quoting_file_path = "quoting/export_data_for_quoting.csv"
        if not os.path.exists(quoting_file_path):
            st.error("❌ No quote data available. Please generate quote data first.")
            return
        
        # Search for products
        success, results = self.quoting_manager.search_products(search_terms, quoting_file_path)
        
        if success:
            st.session_state.search_results = results
            st.success(f"✅ Found {len(results)} matching products")
            
            # Display results (simplified version - you can expand this)
            self._display_search_results(results, search_terms)
        else:
            st.warning(f"❌ {results}")
    
    def _display_search_results(self, results: pd.DataFrame, search_terms: list):
        """Display search results."""
        st.markdown("### 📊 Search Results")
        
        # Find best price
        best_price_product = self._find_best_price_product(results)
        
        if best_price_product is not None:
            st.markdown("### 🏆 Best Price Found")
            col_info, col_image = st.columns([2, 1])
            
            with col_info:
                st.markdown(f"**🏷️ Best Price: ${best_price_product['_cost_value']:.2f}** ({best_price_product['_cost_field']})")
                st.markdown(f"**📦 Supplier:** {best_price_product.get('_Supplier', 'Unknown')}")
                
                # Show key product info
                for field in ['Title', 'Vendor', 'Variant SKU', 'Variant Price', 'Cost per item']:
                    if field in best_price_product.index and pd.notna(best_price_product[field]):
                        st.markdown(f"**{field}:** {best_price_product[field]}")
            
            with col_image:
                self._display_product_image(best_price_product, results)
        
        # Show all results grouped by search term
        st.markdown("### 📋 All Search Results")
        for search_term in search_terms:
            term_results = results[results['search_term'] == search_term]
            if not term_results.empty:
                st.markdown(f"#### 🔍 Results for: **{search_term}** ({len(term_results)} supplier options)")
                
                for idx, row in term_results.iterrows():
                    supplier = row.get('_Supplier', 'Unknown')
                    cost = row.get('Cost per item', 'N/A')
                    cost_display = f"${float(str(cost).replace(',', '')):.2f}" if pd.notna(cost) and cost != 'N/A' else "No price"
                    
                    with st.expander(f"📦 {supplier} - {cost_display}", expanded=False):
                        # Show product details
                        for field in ['Title', 'Vendor', 'Variant SKU', 'Variant Price', 'Cost per item']:
                            if field in row.index and pd.notna(row[field]) and row[field] != '':
                                st.markdown(f"**{field}:** {row[field]}")
    
    def _find_best_price_product(self, results: pd.DataFrame):
        """Find the product with the best (lowest) price."""
        shopify_cost_fields = ['Cost per item', 'Variant Price']
        lowest_cost_value = float('inf')
        best_product = None
        
        for idx, row in results.iterrows():
            for col in row.index:
                if col in shopify_cost_fields:
                    try:
                        raw_value = row[col]
                        if pd.isna(raw_value) or raw_value == '':
                            continue
                        
                        price_str = str(raw_value).replace('$', '').replace(',', '').strip()
                        if price_str and price_str not in ['nan', 'none', '', 'null', '0', '0.0', '0.00']:
                            price_value = float(price_str)
                            if price_value > 0 and price_value < lowest_cost_value:
                                lowest_cost_value = price_value
                                best_product = row.copy()
                                best_product['_cost_field'] = col
                                best_product['_cost_value'] = price_value
                    except (ValueError, TypeError):
                        continue
        
        return best_product
    
    def _display_product_image(self, product: pd.Series, all_results: pd.DataFrame):
        """Display product image, searching across suppliers if needed."""
        # Look for image in the best price product first
        image_fields = ['Image Src', 'Variant Image', 'Image', 'Product Image', 'Image URL']
        image_found = False
        
        for field in image_fields:
            if field in product.index and pd.notna(product[field]):
                url = str(product[field]).strip()
                if url.startswith(('http', 'https')):
                    try:
                        st.image(url, caption="Product Image", width=200)
                        image_found = True
                        break
                    except:
                        pass
        
        if not image_found:
            st.warning("📷 No image available")
    
    def _render_sidebar(self):
        """Render the sidebar with current mappings and log info."""
        st.sidebar.header("Current Mappings")
        
        # Show log file info
        log_file_path = self.logger.get_log_file_path()
        if log_file_path and os.path.exists(log_file_path):
            file_size = self.logger.get_log_file_size()
            st.sidebar.info(f"📋 Processing log: {file_size} bytes")
            st.sidebar.caption("Log will be available for download after processing")
        
        # Show current mappings
        if st.session_state.supplier_mappings:
            for supplier, mapping in st.session_state.supplier_mappings.items():
                with st.sidebar.expander(f"📋 {supplier}"):
                    for field, value in mapping.items():
                        if field == "_file_keyword":
                            st.write(f"🔍 File keyword: {value}")
                        elif field.endswith('_custom'):
                            original_field = field.replace('_custom', '')
                            if value:
                                st.write(f"📝 {original_field} ← Custom: '{value}'")
                        elif value and not mapping.get(f"{field}_custom"):
                            st.write(f"🔗 {field} ← {value}")
        else:
            st.sidebar.info("No mappings created yet")


def main():
    """Main application entry point."""
    app = ETECDatafeedsApp()
    app.run()


if __name__ == "__main__":
    main()