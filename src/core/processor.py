"""
Data mapping and processing engine for ETEC+ Datafeeds application.
Handles mapping supplier data to Shopify format and removing duplicates.
"""

import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
import streamlit as st

from .file_handler import read_file, detect_supplier
from .data_processing import (
    extract_quantity, convert_weight_to_grams, truncate_title,
    normalize_dataframe_types, generate_shopify_tags
)
from ..utils.logger import AppLogger


class DataProcessor:
    """Handles data processing and mapping operations."""
    
    def __init__(self, logger: AppLogger):
        self.logger = logger
    
    def process_files(self, uploaded_files: List[Any], mappings: Dict[str, Dict[str, str]]) -> List[pd.DataFrame]:
        """Process all uploaded files and combine data."""
        all_data = []
        
        for file in uploaded_files:
            supplier = detect_supplier(file.name)
            self.logger.info(f"🔍 Processing {file.name} - Detected supplier: {supplier}")
            
            if supplier and supplier in mappings:
                self.logger.info(f"✅ Found mapping for {supplier}")
                
                df = read_file(file)
                if df is not None:
                    self.logger.info(f"📊 Read {len(df)} rows from {file.name}")
                    self.logger.info(f"📋 Available columns in {file.name}: {list(df.columns)}")
                    
                    mapping = mappings[supplier]
                    self.logger.info(f"🔗 Applying {len(mapping)} mappings for {supplier}")
                    
                    # Apply mapping
                    mapped_data = self._apply_mapping(df, mapping, supplier)
                    
                    if mapped_data:
                        result_df = pd.DataFrame(mapped_data)
                        self.logger.info(f"📊 Created DataFrame: {len(result_df)} rows × {len(result_df.columns)} columns")
                        
                        # Apply data transformations
                        result_df = self._apply_transformations(result_df, supplier)
                        
                        # Add vendor and default values
                        result_df = self._add_default_values(result_df, supplier)
                        
                        # Normalize data types
                        result_df = normalize_dataframe_types(result_df)
                        
                        # Log sample data
                        self._log_sample_data(result_df, supplier)
                        
                        all_data.append(result_df)
                        st.success(f"✅ {file.name}: {len(result_df)} products processed from {supplier}")
                        self.logger.info(f"Successfully processed {len(result_df)} products from {supplier}")
                    else:
                        st.error(f"❌ {file.name}: No valid mappings found for {supplier}")
                        self.logger.info(f"No valid mappings found for {supplier}")
                else:
                    st.error(f"❌ {file.name}: Could not read file")
            else:
                if supplier:
                    st.warning(f"⚠️ {file.name}: Detected supplier '{supplier}' but no mapping found")
                    self.logger.info(f"Detected supplier '{supplier}' but no mapping found. Available mappings: {list(mappings.keys())}")
                else:
                    st.warning(f"⚠️ {file.name}: Could not detect supplier from filename")
                    self.logger.info("Could not detect supplier from filename")
        
        return all_data
    
    def _apply_mapping(self, df: pd.DataFrame, mapping: Dict[str, str], supplier: str) -> Dict[str, List[Any]]:
        """Apply field mapping to supplier data."""
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
                    self.logger.info(f"   🏷️ Generated tags from: {', '.join(available_tag_cols)}")
                else:
                    # No valid tag columns found
                    mapped_data[shopify_field] = [""] * len(df)
                    self.logger.info(f"   ⚠️ Tag columns not found: {', '.join(tag_columns)}")
            elif f"{shopify_field}_custom" in mapping and mapping[f"{shopify_field}_custom"]:
                # Use custom text value
                custom_value = mapping[f"{shopify_field}_custom"]
                mapped_data[shopify_field] = [custom_value] * len(df)
                custom_mappings += 1
            else:
                # Leave empty
                mapped_data[shopify_field] = [""] * len(df)
                if supplier_field and supplier_field not in df.columns:
                    missing_columns.append(f"{shopify_field} → {supplier_field}")
        
        self.logger.info(f"   ✅ Column mappings: {successful_mappings}")
        self.logger.info(f"   📝 Custom values: {custom_mappings}")
        if missing_columns:
            self.logger.info(f"   ⚠️ Missing columns: {', '.join(missing_columns)}")
        
        return mapped_data
    
    def _apply_transformations(self, df: pd.DataFrame, supplier: str) -> pd.DataFrame:
        """Apply data transformations to the mapped DataFrame."""
        # Process quantity if mapped
        if 'Variant Inventory Qty' in df.columns:
            df['Variant Inventory Qty'] = df['Variant Inventory Qty'].apply(extract_quantity)
        
        # Process weight conversion to grams if mapped
        if 'Variant Grams' in df.columns:
            df['Variant Grams'] = df['Variant Grams'].apply(convert_weight_to_grams)
            self.logger.info(f"   ⚖️ Converted weights to grams for {supplier}")
        
        # Process title length limitation if mapped
        if 'Title' in df.columns:
            original_titles = df['Title'].astype(str)
            long_titles = original_titles[original_titles.str.len() > 255]
            if len(long_titles) > 0:
                df['Title'] = df['Title'].apply(truncate_title)
                self.logger.info(f"   ✂️ Truncated {len(long_titles)} long titles (>255 chars) for {supplier}")
                
                # Double-check: verify no titles exceed 255 characters after truncation
                final_titles = df['Title'].astype(str)
                still_long = final_titles[final_titles.str.len() > 255]
                if len(still_long) > 0:
                    # Emergency truncation - force to exactly 255 chars
                    df.loc[final_titles.str.len() > 255, 'Title'] = final_titles[final_titles.str.len() > 255].str[:255]
                    self.logger.info(f"   🚨 Emergency truncated {len(still_long)} titles that still exceeded 255 chars")
                else:
                    self.logger.info(f"   ✅ All titles verified to be ≤255 characters for {supplier}")
        
        return df
    
    def _add_default_values(self, df: pd.DataFrame, supplier: str) -> pd.DataFrame:
        """Add vendor and default Shopify values."""
        # Add vendor
        df['Vendor'] = supplier
        
        # Add default values for required fields
        df['Published'] = 'true'
        df['Option1 Name'] = 'Title'
        df['Option1 Value'] = 'Default Title'
        df['Variant Inventory Tracker'] = 'shopify'
        df['Variant Inventory Policy'] = 'deny'
        df['Variant Fulfillment Service'] = 'manual'
        df['Variant Requires Shipping'] = 'true'
        df['Variant Taxable'] = 'true'
        df['Gift Card'] = 'false'
        df['Status'] = 'active'
        
        return df
    
    def _log_sample_data(self, df: pd.DataFrame, supplier: str) -> None:
        """Log sample data for debugging."""
        self.logger.info(f"📋 Sample data from {supplier}:")
        sample_cols = ['Title', 'Variant SKU', 'Vendor', 'Variant Price', 'Variant Grams']
        available_cols = [col for col in sample_cols if col in df.columns]
        if available_cols:
            sample_data = df[available_cols].head(2)
            for idx, row in sample_data.iterrows():
                self.logger.info(f"   Sample {idx+1}: {dict(row)}")
    
    def find_and_remove_duplicates(self, combined_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """Find duplicates and remove them, keeping lowest cost. Returns final df and duplicates info."""
        self.logger.write("🔍 **Duplicate Removal Debug:**")
        
        # Show initial vendor breakdown
        if 'Vendor' in combined_df.columns:
            initial_counts = combined_df['Vendor'].value_counts()
            self.logger.write(f"📊 Before duplicate removal:")
            for vendor, count in initial_counts.items():
                self.logger.info(f"   • {vendor}: {count} products")
        
        if 'Variant SKU' not in combined_df.columns or 'Cost per item' not in combined_df.columns:
            self.logger.write("⚠️ Missing required columns for duplicate removal")
            return combined_df, []
        
        # Convert cost to numeric - remove commas first
        combined_df['Cost per item'] = combined_df['Cost per item'].astype(str).str.replace(',', '')
        combined_df['Cost per item'] = pd.to_numeric(combined_df['Cost per item'], errors='coerce')
        
        # Process invalid costs
        invalid_costs = combined_df[combined_df['Cost per item'].isna()]
        if len(invalid_costs) > 0:
            self.logger.write(f"⚠️ Found {len(invalid_costs)} rows with invalid costs:")
            if 'Vendor' in invalid_costs.columns:
                invalid_by_vendor = invalid_costs['Vendor'].value_counts()
                for vendor, count in invalid_by_vendor.items():
                    self.logger.info(f"   • {vendor}: {count} invalid costs")
        
        # Remove rows with invalid costs
        before_dropna = len(combined_df)
        combined_df = combined_df.dropna(subset=['Cost per item'])
        after_dropna = len(combined_df)
        
        if before_dropna != after_dropna:
            self.logger.write(f"🗑️ Removed {before_dropna - after_dropna} rows with invalid costs")
        
        # Find duplicates and preserve image URLs before removal
        duplicates_info = []
        images_preserved = self._preserve_images_from_duplicates(combined_df)
        
        # Remove duplicates keeping lowest cost (with preserved images)
        final_df = combined_df.sort_values('Cost per item').drop_duplicates('Variant SKU', keep='first')
        
        # Generate duplicate info
        if len(combined_df) > 0:
            grouped = combined_df.groupby('Variant SKU')
            for sku, group in grouped:
                if len(group) > 1:
                    group_sorted = group.sort_values('Cost per item')
                    kept_idx = group_sorted.index[0]
                    removed_rows = group_sorted.iloc[1:]
                    
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
        
        # Log results
        if images_preserved > 0:
            st.success(f"🖼️ Successfully preserved {images_preserved} image URLs from duplicate items")
        
        if 'Vendor' in final_df.columns:
            final_counts = final_df['Vendor'].value_counts()
            self.logger.write(f"📊 After duplicate removal:")
            for vendor, count in final_counts.items():
                self.logger.info(f"   • {vendor}: {count} products")
        
        return final_df, duplicates_info
    
    def _preserve_images_from_duplicates(self, combined_df: pd.DataFrame) -> int:
        """Preserve image URLs from duplicate products that are being removed."""
        images_preserved = 0
        available_image_fields = ['Image Src', 'Variant Image', 'Image', 'Product Image', 'Image URL']
        found_image_fields = [field for field in available_image_fields if field in combined_df.columns]
        
        if found_image_fields:
            self.logger.write(f"📷 Checking for images in fields: {', '.join(found_image_fields)}")
        
        if len(combined_df) > 0:
            grouped = combined_df.groupby('Variant SKU')
            
            for sku, group in grouped:
                if len(group) > 1:
                    group_sorted = group.sort_values('Cost per item')
                    kept_idx = group_sorted.index[0]
                    removed_rows = group_sorted.iloc[1:]
                    
                    for image_field in found_image_fields:
                        current_image = combined_df.loc[kept_idx, image_field]
                        
                        if pd.isna(current_image) or str(current_image).strip() == '' or str(current_image).lower() in ['none', 'null', 'n/a']:
                            for _, removed_row in removed_rows.iterrows():
                                removed_image = removed_row.get(image_field, '')
                                
                                if (pd.notna(removed_image) and 
                                    str(removed_image).strip() != '' and 
                                    str(removed_image).lower() not in ['none', 'null', 'n/a'] and
                                    (str(removed_image).startswith(('http', 'https', 'www.', 'ftp://')) or 
                                     '.' in str(removed_image))):
                                    
                                    combined_df.loc[kept_idx, image_field] = removed_image
                                    images_preserved += 1
                                    self.logger.info(f"🖼️ Preserved {image_field} for SKU {sku}")
                                    break
        
        return images_preserved