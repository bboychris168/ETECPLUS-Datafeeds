"""
Data management for supplier information and downloads.
Handles supplier configuration and automated file downloads.
"""

import requests
import os
from typing import Dict, Any, List, Tuple
import streamlit as st

from ..utils.config import ConfigManager
from ..core.file_handler import download_supplier_file


class SupplierManager:
    """Manages supplier configuration and downloads."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def download_to_suppliers_folder(self, selected_suppliers: List[str], supplier_config: Dict[str, Any]) -> None:
        """Download files directly to suppliers folder."""
        # Create suppliers folder if it doesn't exist
        os.makedirs("suppliers", exist_ok=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, supplier_key in enumerate(selected_suppliers):
            config = supplier_config[supplier_key]
            status_text.text(f"Downloading {config['name']}...")
            
            success, message = download_supplier_file(
                config['url'], 
                config['filename'], 
                "suppliers"
            )
            
            if success:
                st.success(f"✅ {config['name']}: {message}")
            else:
                st.error(f"❌ {config['name']}: {message}")
            
            # Update progress
            progress_bar.progress((i + 1) / len(selected_suppliers))
        
        status_text.text("Download complete!")
    
    def add_supplier(self, key: str, name: str, url: str, filename: str, description: str = "") -> bool:
        """Add a new supplier to the configuration."""
        supplier_config = self.config_manager.load_supplier_config()
        
        if key in supplier_config:
            return False  # Supplier already exists
        
        supplier_config[key] = {
            "name": name,
            "url": url,
            "filename": filename,
            "file_type": "csv",
            "description": description or f"{name} product datafeed"
        }
        
        self.config_manager.save_supplier_config(supplier_config)
        return True
    
    def update_supplier(self, key: str, name: str, url: str, filename: str) -> bool:
        """Update an existing supplier configuration."""
        supplier_config = self.config_manager.load_supplier_config()
        
        if key not in supplier_config:
            return False  # Supplier doesn't exist
        
        supplier_config[key].update({
            "name": name,
            "url": url,
            "filename": filename
        })
        
        self.config_manager.save_supplier_config(supplier_config)
        return True
    
    def remove_supplier(self, key: str) -> bool:
        """Remove a supplier from the configuration."""
        supplier_config = self.config_manager.load_supplier_config()
        
        if key not in supplier_config:
            return False  # Supplier doesn't exist
        
        del supplier_config[key]
        self.config_manager.save_supplier_config(supplier_config)
        return True
    
    def get_all_suppliers(self) -> Dict[str, Any]:
        """Get all configured suppliers."""
        return self.config_manager.load_supplier_config()


class QuotingManager:
    """Manages product quoting and search functionality."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def generate_quote_data(self, uploaded_files: List[Any], mappings: Dict[str, Dict[str, str]], 
                          shopify_columns: List[str]) -> Tuple[bool, str]:
        """Generate quote data CSV from supplier mappings."""
        from ..core.file_handler import read_file, detect_supplier
        import pandas as pd
        
        try:
            # Create quoting folder
            os.makedirs("quoting", exist_ok=True)
            quoting_file_path = "quoting/export_data_for_quoting.csv"
            
            combined_data = []
            
            for file in uploaded_files:
                supplier = detect_supplier(file.name)
                if supplier and supplier in mappings:
                    mapping = mappings[supplier]
                    
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
                import pandas as pd
                # Combine ALL supplier data (NO duplicate removal)
                quote_df = pd.concat(combined_data, ignore_index=True)
                
                # Save to quoting folder
                quote_df.to_csv(quoting_file_path, index=False)
                
                # Count by supplier
                supplier_counts = quote_df['_Supplier'].value_counts()
                count_text = ", ".join([f"{supplier}: {count}" for supplier, count in supplier_counts.items()])
                
                return True, f"Generated quote data with {len(quote_df)} products ({count_text})"
            else:
                return False, "No data to export. Please check your supplier files and mappings."
                
        except Exception as e:
            return False, f"Error generating quote data: {str(e)}"
    
    def search_products(self, search_terms: List[str], quote_data_path: str) -> Tuple[bool, Any]:
        """Search for products in quote data."""
        try:
            import pandas as pd
            df = pd.read_csv(quote_data_path, low_memory=False)
            
            all_results = []
            
            for search_term in search_terms:
                mask = pd.Series([False] * len(df))
                
                # Primary search in Variant SKU column
                if 'Variant SKU' in df.columns:
                    mask |= df['Variant SKU'].astype(str).str.upper().str.contains(search_term.upper(), na=False)
                
                # Fallback search in other text columns
                for col in df.columns:
                    if df[col].dtype == 'object' and col not in ['Image Src', 'Body (HTML)', 'SEO Description']:
                        mask |= df[col].astype(str).str.upper().str.contains(search_term.upper(), na=False)
                
                matches = df[mask].copy()
                
                if not matches.empty:
                    matches['search_term'] = search_term
                    all_results.append(matches)
            
            if all_results:
                combined_results = pd.concat(all_results, ignore_index=True)
                return True, combined_results
            else:
                return False, "No matching products found"
                
        except Exception as e:
            return False, f"Error searching products: {str(e)}"