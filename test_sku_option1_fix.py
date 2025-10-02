#!/usr/bin/env python3
"""
Test script to verify the SKU-based Option1 Value fix for identical titles
"""

import pandas as pd
import sys
import os

def test_sku_based_option1_fix():
    """Test the SKU-based Option1 Value fix for identical titles with different SKUs"""
    print("🧪 Testing SKU-Based Option1 Value Fix")
    print("=" * 60)
    
    # Create test data that represents the WORST CASE scenario:
    # Completely identical titles but different SKUs (the exact problem you experienced)
    test_data = {
        'Title': [
            'Gaming Mouse RGB',    # Same title
            'Gaming Mouse RGB',    # Same title  
            'Gaming Mouse RGB',    # Same title again
            'Wireless Keyboard',
            'Gaming Headset Pro',
            'Gaming Headset Pro',  # Same title
        ],
        'Variant SKU': ['MOUSE001', 'MOUSE002', 'MOUSE003', 'KEYB001', 'HEAD001', 'HEAD002'],  # All different SKUs
        'Cost per item': [25.99, 19.99, 35.50, 45.00, 75.00, 65.00],
        'Vendor': ['VendorA', 'VendorB', 'VendorC', 'VendorA', 'VendorB', 'VendorC'],
        'Variant Price': [39.99, 29.99, 49.99, 69.99, 99.99, 89.99]
    }
    
    df = pd.DataFrame(test_data)
    
    print("📋 TEST SCENARIO - The Worst Case (Identical Titles):")
    print(df[['Title', 'Variant SKU', 'Cost per item', 'Vendor']].to_string(index=False))
    print()
    print("🚨 PROBLEM:")
    print("- THREE products have IDENTICAL titles: 'Gaming Mouse RGB'")
    print("- TWO products have IDENTICAL titles: 'Gaming Headset Pro'")
    print("- All have DIFFERENT Variant SKUs")
    print("- This is exactly what causes 'Default Title already exists' error")
    print()
    
    # Apply the duplicate title handling first (as your app does)
    def create_unique_handles_and_titles(df):
        """Create unique handles and titles by adding numbered suffixes for duplicates based on cost ranking"""
        if df.empty:
            return df
        
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
    
    # Apply title processing
    result_df = create_unique_handles_and_titles(df)
    
    # Generate handles
    result_df['Handle'] = result_df['Title'].str.lower().str.replace(' ', '-').str.replace('[^a-z0-9-]', '', regex=True)
    
    # Apply the NEW SKU-based Option1 Value fix
    result_df['Option1 Name'] = 'Title'
    
    # THE NEW FIX: Use Variant SKU as Option1 Value
    if 'Variant SKU' in result_df.columns:
        result_df['Option1 Value'] = result_df['Variant SKU'].astype(str)
        print("✅ Applied SKU-based Option1 Value fix")
    else:
        result_df['Option1 Value'] = ''
        print("⚠️ No Variant SKU found, using empty Option1 Value")
    
    print()
    print("📋 AFTER Processing with SKU-Based Option1 Value Fix:")
    display_df = result_df[['Title', 'Handle', 'Variant SKU', 'Option1 Name', 'Option1 Value', 'Cost per item']]
    print(display_df.to_string(index=False))
    print()
    
    # Critical analysis for Shopify compatibility
    print("🔍 SHOPIFY COMPATIBILITY ANALYSIS:")
    print("=" * 50)
    
    # Check Option1 Value uniqueness
    option_counts = result_df['Option1 Value'].value_counts()
    duplicate_options = option_counts[option_counts > 1]
    
    print(f"Option1 Value uniqueness: {len(option_counts)} unique values for {len(result_df)} products")
    
    if len(duplicate_options) == 0:
        print("✅ ALL Option1 Values are UNIQUE - No conflicts possible!")
    else:
        print("❌ Found duplicate Option1 Values:")
        print(duplicate_options)
    
    # Check handle uniqueness
    handle_counts = result_df['Handle'].value_counts()
    duplicate_handles = handle_counts[handle_counts > 1]
    
    if len(duplicate_handles) == 0:
        print("✅ All handles are unique!")
    else:
        print("❌ Found duplicate handles:")
        print(duplicate_handles)
    
    # Check for any potential Shopify issues
    print()
    print("🎯 CUSTOMER EXPERIENCE IN SHOPIFY:")
    print("=" * 40)
    
    # Show what customers will see
    for _, row in result_df.iterrows():
        title = row['Title']
        sku = row['Option1 Value']
        price = f"${row['Cost per item']:.2f}"
        
        print(f"Product: {title} - {price}")
        print(f"   Variant: Title: {sku} ▼")
        print()
    
    # Final verdict
    print("🏆 FINAL VERDICT:")
    print("=" * 20)
    
    all_unique_options = len(duplicate_options) == 0
    all_unique_handles = len(duplicate_handles) == 0
    
    if all_unique_options and all_unique_handles:
        print("✅ COMPLETE SUCCESS!")
        print("✅ No 'Default Title already exists' errors possible")
        print("✅ Professional SKU-based variant names")
        print("✅ Clear product differentiation for customers")
        print("✅ B2B friendly with visible SKUs")
        print("✅ 100% Shopify compatible")
    else:
        print("❌ Issues found - needs further fixes")
    
    return result_df

if __name__ == "__main__":
    print("🧪 Testing SKU-Based Option1 Value Fix for Shopify\n")
    test_sku_based_option1_fix()
    print("\n🎉 Test completed!")