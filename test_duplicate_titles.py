#!/usr/bin/env python3
"""
Test script to verify the duplicate title handling functionality
"""

import pandas as pd
import sys
import os

# Add the current directory to path so we can import from streamlit_app
sys.path.append(os.path.dirname(__file__))

def test_duplicate_title_handling():
    """Test the duplicate title handling with sample data"""
    
    # Create sample data with duplicate titles but different costs
    test_data = {
        'Title': [
            'Gaming Mouse RGB',
            'Gaming Mouse RGB',  # Duplicate
            'Gaming Mouse RGB',  # Duplicate
            'Wireless Keyboard',
            'Gaming Headset',
            'Gaming Headset',    # Duplicate
        ],
        'Variant SKU': ['GM001', 'GM002', 'GM003', 'WK001', 'GH001', 'GH002'],
        'Cost per item': [25.99, 19.99, 35.50, 45.00, 75.00, 65.00],
        'Vendor': ['VendorA', 'VendorB', 'VendorC', 'VendorA', 'VendorB', 'VendorC'],
        'Variant Price': [39.99, 29.99, 49.99, 69.99, 99.99, 89.99]
    }
    
    df = pd.DataFrame(test_data)
    
    print("📋 Original Data:")
    print(df[['Title', 'Variant SKU', 'Cost per item', 'Vendor']].to_string(index=False))
    print()
    
    # Apply the duplicate title handling function
    def create_unique_handles_and_titles(df):
        """Create unique handles and titles by adding numbered suffixes for duplicates based on cost ranking"""
        if df.empty:
            return df
        
        # Make a copy to work with
        df_copy = df.copy()
        
        # Convert cost to numeric for sorting
        if 'Cost per item' in df_copy.columns:
            df_copy['_cost_numeric'] = pd.to_numeric(df_copy['Cost per item'].astype(str).str.replace(',', ''), errors='coerce')
        else:
            df_copy['_cost_numeric'] = 0
        
        # Group by title to find duplicates
        title_groups = df_copy.groupby('Title')
        modified_titles = 0
        
        for title, group in title_groups:
            if len(group) > 1:  # We have duplicates
                print(f"🔍 Processing duplicates for: '{title}'")
                
                # Sort by cost (lowest first)
                group_sorted = group.sort_values('_cost_numeric')
                
                print("   Cost ranking (lowest to highest):")
                for i, (idx, row) in enumerate(group_sorted.iterrows()):
                    print(f"   {i+1}. ${row['_cost_numeric']:.2f} - {row['Variant SKU']} ({row['Vendor']})")
                
                # Add numbered suffixes starting from the second item
                for i, (idx, row) in enumerate(group_sorted.iterrows()):
                    if i > 0:  # First item keeps original title
                        new_title = f"{title} ({i+1})"
                        df_copy.loc[idx, 'Title'] = new_title
                        modified_titles += 1
                        print(f"   ➡️ Renamed to: '{new_title}'")
                print()
        
        # Clean up temporary column
        df_copy = df_copy.drop(columns=['_cost_numeric'])
        
        if modified_titles > 0:
            print(f"🏷️ Added numbered suffixes to {modified_titles} duplicate titles (ranked by cost)")
        
        return df_copy
    
    # Apply the function
    result_df = create_unique_handles_and_titles(df)
    
    print("📋 After Duplicate Title Processing:")
    print(result_df[['Title', 'Variant SKU', 'Cost per item', 'Vendor']].to_string(index=False))
    print()
    
    # Generate handles to show the result
    result_df['Handle'] = result_df['Title'].str.lower().str.replace(' ', '-').str.replace('[^a-z0-9-]', '', regex=True)
    
    print("📋 Final Result with Handles:")
    print(result_df[['Title', 'Handle', 'Variant SKU', 'Cost per item']].to_string(index=False))
    print()
    
    # Check for unique handles
    handle_counts = result_df['Handle'].value_counts()
    duplicate_handles = handle_counts[handle_counts > 1]
    
    if len(duplicate_handles) == 0:
        print("✅ SUCCESS: All handles are unique!")
    else:
        print("❌ FAILED: Found duplicate handles:")
        print(duplicate_handles)
    
    return result_df

if __name__ == "__main__":
    print("🧪 Testing Duplicate Title Handling\n")
    test_duplicate_title_handling()