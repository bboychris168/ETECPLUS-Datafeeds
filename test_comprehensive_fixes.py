#!/usr/bin/env python3
"""
Test script to verify both URL encoding and duplicate title fixes
"""

import pandas as pd
import sys
import os
from urllib.parse import quote

# Add the current directory to path so we can import from streamlit_app
sys.path.append(os.path.dirname(__file__))

def test_url_encoding():
    """Test the URL encoding functionality"""
    print("🔗 Testing URL Encoding Fix")
    print("=" * 50)
    
    # Import the function from streamlit_app
    try:
        from streamlit_app import fix_image_url_encoding
    except ImportError:
        print("❌ Could not import fix_image_url_encoding function")
        return
    
    test_urls = [
        "https://www.compuworld.com.au/app/webroot/stuff/product_image/productImage_2740807461519262928.main (002).jpg",
        "https://example.com/path with spaces/image.jpg",
        "http://site.com/normal-url.png", 
        "https://test.com/multiple spaces here/file (1).jpg",
        "",  # Empty string
        None,  # None value
        "not-a-url"  # Not a URL
    ]
    
    for url in test_urls:
        fixed = fix_image_url_encoding(url)
        print(f"Original: {url}")
        print(f"Fixed:    {fixed}")
        print()
    
    print("✅ URL Encoding test completed!\n")

def test_complete_duplicate_handling():
    """Test the complete duplicate handling including Option1 Value"""
    print("🏷️ Testing Complete Duplicate Title Handling")
    print("=" * 50)
    
    # Create sample data that would cause both types of duplicates
    test_data = {
        'Title': [
            'Gaming Mouse RGB',
            'Gaming Mouse RGB',  # Same title - should get numbered
            'Wireless Keyboard',
            'Gaming Headset Pro',
            'Gaming Headset Pro',  # Same title - should get numbered
        ],
        'Variant SKU': ['GM001', 'GM002', 'WK001', 'GH001', 'GH002'],
        'Cost per item': [25.99, 19.99, 45.00, 75.00, 65.00],
        'Vendor': ['VendorA', 'VendorB', 'VendorA', 'VendorB', 'VendorC'],
        'Variant Price': [39.99, 29.99, 69.99, 99.99, 89.99],
        'Image Src': [
            'https://example.com/image with spaces.jpg',
            'https://site.com/another image (1).png',
            'https://test.com/normal-image.jpg',
            'https://vendor.com/product image (final).jpg',
            'https://store.com/headset-pic.png'
        ]
    }
    
    df = pd.DataFrame(test_data)
    
    print("📋 Original Data:")
    print(df[['Title', 'Variant SKU', 'Cost per item', 'Image Src']].to_string(index=False))
    print()
    
    # Test duplicate title handling
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
    
    # Apply duplicate title handling
    result_df = create_unique_handles_and_titles(df)
    
    # Generate handles
    result_df['Handle'] = result_df['Title'].str.lower().str.replace(' ', '-').str.replace('[^a-z0-9-]', '', regex=True)
    
    # Test URL encoding
    try:
        from streamlit_app import fix_image_url_encoding
        result_df['Image Src'] = result_df['Image Src'].apply(fix_image_url_encoding)
        print("🔗 Applied URL encoding to Image Src field")
    except ImportError:
        print("⚠️ Could not import URL encoding function")
    
    # Create Option1 Value using titles (like the fix does)
    result_df['Option1 Value'] = result_df['Title'].astype(str)
    
    print("📋 After Processing:")
    print(result_df[['Title', 'Handle', 'Option1 Value', 'Variant SKU', 'Cost per item', 'Image Src']].to_string(index=False))
    print()
    
    # Check for uniqueness
    handle_counts = result_df['Handle'].value_counts()
    duplicate_handles = handle_counts[handle_counts > 1]
    
    option_counts = result_df['Option1 Value'].value_counts()
    duplicate_options = option_counts[option_counts > 1]
    
    print("🔍 Uniqueness Check:")
    if len(duplicate_handles) == 0:
        print("✅ All handles are unique!")
    else:
        print("❌ Found duplicate handles:")
        print(duplicate_handles)
    
    if len(duplicate_options) == 0:
        print("✅ All Option1 Values are unique!")
    else:
        print("❌ Found duplicate Option1 Values:")
        print(duplicate_options)
    
    return result_df

if __name__ == "__main__":
    print("🧪 Testing URL Encoding and Duplicate Handling Fixes\\n")
    
    test_url_encoding()
    test_complete_duplicate_handling()
    
    print("\\n🎉 All tests completed!")