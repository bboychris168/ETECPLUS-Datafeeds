"""
Streamlit UI styling and configuration.
"""

import streamlit as st


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="ETEC+ Supplier Datafeeds",
        page_icon="📊",
        layout="wide"
    )


def apply_custom_css():
    """Apply custom CSS styling to the application."""
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

        .mapping-status {
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            margin-left: 10px;
        }
        .status-mapped {
            background: #28a745;
            color: white;
        }
        .status-custom {
            background: #17a2b8;
            color: white;
        }
        .status-missing {
            background: #dc3545;
            color: white;
        }
        .status-required {
            background: #ffc107;
            color: black;
        }
        
        /* Modern Upload Section Styling */
        .supplier-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border: 1px solid #e1e8ed;
            border-radius: 12px;
            padding: 1.2rem;
            margin: 0.8rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .supplier-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }
        
        .upload-section {
            background: #ffffff;
            border: 2px dashed #d1d5db;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            margin: 1rem 0;
            transition: all 0.3s ease;
        }
        
        .upload-section:hover {
            border-color: #667eea;
            background: #f8faff;
        }
        
        .file-list-item {
            background: #f8f9fa;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            margin: 0.3rem 0;
            border-left: 3px solid #667eea;
        }
    </style>
    """, unsafe_allow_html=True)


def show_main_header():
    """Display the main application header."""
    st.markdown(
        '<div class="main-header"><h1>🏢 ETEC+ Supplier Datafeeds</h1><p>Simple Shopify CSV Mapping</p></div>', 
        unsafe_allow_html=True
    )


def show_workflow_status(shopify_configured: bool):
    """Show workflow progress status."""
    if not shopify_configured:
        st.info("📋 **Workflow:** 1️⃣ Upload Shopify Template → 2️⃣ Upload Supplier Files → 3️⃣ Map Columns → 4️⃣ Export")
    else:
        st.success("📋 **Workflow:** ✅ Shopify Template → 2️⃣ Upload Supplier Files → 3️⃣ Map Columns → 4️⃣ Export")


def show_help_section():
    """Display the help section with usage instructions."""
    with st.expander("📖 How to Use This Application", expanded=False):
        st.markdown("""
        ### 🚀 **Quick Start Guide**

        **Step 1: Setup Shopify Template** 🏪
        - Upload your Shopify CSV template file
        - This defines the columns for your final export

        **Step 2: Get Supplier Data** 📁
        - Download data automatically from configured suppliers, OR
        - Upload supplier files manually

        **Step 3: Map Your Data** 🔗
        - Match supplier columns to Shopify fields
        - Add custom text where needed
        - Generate tags from multiple columns

        **Step 4: Export Products** ⚡
        - Review and export your mapped data
        - Download the final Shopify-ready CSV

        **Step 5: Quote Products** 💰
        - Generate quote database from your mappings
        - Search products by SKU
        - Compare prices across all suppliers

        ---
        💡 **Tips:**
        - Complete steps in order for best results
        - Use the supplier URL manager to add new suppliers
        - The quoting system shows ALL supplier options (no duplicates removed)
        """)


def create_tabs(shopify_configured: bool):
    """Create the main application tabs."""
    if shopify_configured:
        return st.tabs(["🏪 Shopify Template", "📁 Upload", "🔗 Map", "⚡ Export", "💰 Quoting"])
    else:
        return st.tabs(["🏪 Shopify Template", "📁 Upload (Disabled)", "🔗 Map (Disabled)", "⚡ Export (Disabled)", "💰 Quoting"])


def show_mapping_status(field: str, current_mapping: str, current_custom: str, important_fields: list) -> str:
    """Generate status indicator for mapping fields."""
    is_important = field in important_fields
    has_mapping = bool(current_mapping)
    has_custom = bool(current_custom)
    
    if has_mapping:
        status = "✅ MAPPED"
        status_class = "status-mapped"
    elif has_custom:
        status = "📝 CUSTOM"
        status_class = "status-custom" 
    elif is_important:
        status = "⚠️ REQUIRED"
        status_class = "status-required"
    else:
        status = "❌ MISSING"
        status_class = "status-missing"
    
    # Field header with status
    icon = "⭐" if is_important else "📋"
    # Add special icon for Variant Grams
    if field == "Variant Grams":
        icon = "⚖️"
    # Add special icon for Title
    elif field == "Title":
        icon = "📝"
    
    header_html = f"""
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="font-size: 1.1em; font-weight: bold;">{icon} {field}</span>
        <span class="mapping-status {status_class}">{status}</span>
    </div>
    """
    
    return header_html