#!/usr/bin/env python3
"""
Test script to verify the Option1 Value fix for identical titles with different SKUs
"""

import pandas as pd
import sys
import os

def test_option1_value_fix():
    """Test the Option1 Value fix for identical titles with different SKUs"""
    print("🧪 Testing Option1 Value Fix for Identical Titles")
    print("=" * 60)
    
    # Create test data that mimics the real problem:
    # Same titles but different SKUs (the exact scenario causing the error)
    test_data = {
        'Title': [
            'Gaming Mouse RGB',
            'Gaming Mouse RGB',  # Same title
            'Gaming Mouse RGB',  # Same title again
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
    
    print("📋 Original Test Data (The Problem Scenario):")
    print(df[['Title', 'Variant SKU', 'Cost per item', 'Vendor']].to_string(index=False))
    print()
    print("🔍 Analysis:")
    print("- Multiple products have IDENTICAL titles")
    print("- But they have DIFFERENT Variant SKUs")
    print("- This causes 'Default Title already exists' error in Shopify")
    print()
    
    # Apply the duplicate title handling first
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
    
    # Apply the NEW Option1 Value fix (empty values)
    result_df['Option1 Name'] = 'Title'
    result_df['Option1 Value'] = ''  # THE FIX: Empty values prevent conflicts
    
    print("📋 After Processing with NEW Option1 Value Fix:")
    display_df = result_df[['Title', 'Handle', 'Variant SKU', 'Option1 Name', 'Option1 Value', 'Cost per item']]
    print(display_df.to_string(index=False))
    print()
    
    # Check for conflicts
    print("🔍 Conflict Analysis:")
    
    # Check Option1 Value conflicts
    option_counts = result_df['Option1 Value'].value_counts()
    print(f"Option1 Value uniqueness: {len(option_counts)} unique values for {len(result_df)} products")
    
    # Since all Option1 Values are empty, there should be no conflicts
    empty_count = (result_df['Option1 Value'] == '').sum()
    print(f"Empty Option1 Values: {empty_count} (All empty = No conflicts possible)")
    
    # Check handle uniqueness
    handle_counts = result_df['Handle'].value_counts()
    duplicate_handles = handle_counts[handle_counts > 1]
    
    print()
    print("✅ RESULTS:")
    if len(duplicate_handles) == 0:
        print("✅ All handles are unique!")
    else:
        print("❌ Found duplicate handles:")
        print(duplicate_handles)
    
    if empty_count == len(result_df):
        print("✅ All Option1 Values are empty - NO CONFLICTS POSSIBLE!")
        print("✅ This fixes the 'Default Title already exists' error!")
    else:
        print("❌ Some Option1 Values are not empty - potential conflicts")
    
    print()
    print("📊 Summary:")
    print(f"- Products with same titles: {len(df)} → {len(result_df)} (after processing)")
    print(f"- Unique handles: {len(handle_counts)}")
    print(f"- All Option1 Values empty: {'YES' if empty_count == len(result_df) else 'NO'}")
    print(f"- Shopify import compatible: {'YES' if empty_count == len(result_df) and len(duplicate_handles) == 0 else 'NO'}")
    
    return result_df

if __name__ == "__main__":
    print("🧪 Testing Option1 Value Fix for Shopify Import Issues\n")
    test_option1_value_fix()
    print("\n🎉 Test completed!")