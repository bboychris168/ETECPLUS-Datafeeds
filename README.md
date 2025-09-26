# 🛒 ETECPLUS Supplier Datafeeds Management System

A comprehensive Streamlit application for managing supplier product data, mapping it to Shopify format, and providing advanced quoting capabilities.

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Detailed Usage Guide](#-detailed-usage-guide)
- [Supplier Configuration](#-supplier-configuration)
- [File Structure](#-file-structure)
- [Troubleshooting](#-troubleshooting)

## ✨ Features

### � **Shopify Integration**
- Upload and configure Shopify CSV templates
- Map supplier data to Shopify product format
- Export ready-to-import Shopify CSV files

### 📁 **Supplier Data Management**
- Automatic downloading from supplier APIs
- Manual file upload support
- Intelligent supplier detection
- Persistent file storage in organized folders

### 🔗 **Advanced Mapping System**
- Visual column mapping interface
- Custom text field support
- Multi-column tag generation
- Status indicators for mapping completion

### ⚡ **Smart Export Processing**
- Duplicate removal with cost optimization
- Vendor breakdown and statistics
- Export history and file management

### 💰 **Comprehensive Quoting System**
- Multi-supplier price comparison
- SKU-based product search
- Automatic best price identification
- Bulk search capabilities
- Image display support

### ⚙️ **Supplier URL Management**
- Add/edit/remove supplier configurations
- API URL and credential management
- Easy supplier onboarding

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/bboychris168/ETECPLUS-Datafeeds.git
   cd ETECPLUS-Datafeeds
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run streamlit_app.py
   ```

4. **Configure Supplier URLs (Local Development):**
   ```bash
   # Copy the secrets template
   cp .streamlit/secrets.toml .streamlit/secrets.toml.local
   # Edit the file and add your actual supplier URLs
   ```

5. **Access the application:**
   Open your browser and navigate to `http://localhost:8501`

## ☁️ Streamlit Cloud Deployment (Production)

### Setup Steps

1. **Deploy to Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your private GitHub repository
   - Deploy the app

2. **Configure Secrets in Streamlit Cloud:**
   - In your app dashboard, go to Settings → Secrets
   - Add your supplier URLs in TOML format:
   ```toml
   [supplier_urls]
   leader_systems = "https://partner.leadersystems.com.au/WSDataFeed.asmx/DownLoad?CustomerCode=YOUR_CODE&WithHeading=true&WithLongDescription=true&DataType=7"
   auscomp = "https://api.auscomp.au/downloadfeed?token=YOUR_TOKEN&filetype=csv"  
   compuworld = "https://www.compuworld.com.au/products/exportproductpricelist?email=YOUR_EMAIL&id=YOUR_ID"
   ```

3. **App Automatically Detects Configuration:**
   - Production: Uses Streamlit Cloud secrets
   - Local: Uses `.streamlit/secrets.toml` or `supplier_config.json`
   - Fallback: Manual URL entry via the app interface

## 🎯 Quick Start

### Basic Workflow (5 Steps)

1. **🏪 Shopify Template Tab**
   - Upload your Shopify CSV template
   - System extracts column structure

2. **📁 Upload Tab** 
   - Download supplier data automatically OR upload files manually
   - Configure new supplier URLs if needed

3. **🔗 Map Tab**
   - Map supplier columns to Shopify fields
   - Add custom text and tags
   - Save mappings for each supplier

4. **⚡ Export Tab**
   - Review mapped data
   - Export final CSV for Shopify import

5. **💰 Quoting Tab**
   - Generate searchable product database
   - Search by SKU for price comparison

## 📖 Detailed Usage Guide

### Step 1: Shopify Template Configuration

**Purpose:** Define the output format for your product data.

**Process:**
1. Go to the **🏪 Shopify Template** tab
2. Click "Browse files" and select your Shopify CSV template
3. The system automatically extracts all column headers
4. Template is saved for future use

**File Requirements:**
- CSV format with Shopify column headers
- Must include standard fields like: Handle, Title, Vendor, Variant SKU, Cost per item, etc.

### Step 2: Supplier Data Management

**Purpose:** Get product data from your suppliers.

#### Option A: Automatic Download
1. Go to **📁 Upload** tab
2. Select suppliers from the configured list
3. Click "📥 Download Selected Files"
4. Files are automatically saved to `suppliers/` folder

#### Option B: Manual Upload
1. Use the "Manual File Upload" section
2. Select CSV/Excel files from your computer
3. System automatically detects supplier based on filename

#### Option C: Load Previously Downloaded Files
1. Use "Load Downloaded Files" section
2. View available files with supplier detection
3. Load all files with one click

### Step 3: Data Mapping

**Purpose:** Connect supplier data columns to Shopify format.

**Process:**
1. Go to **🔗 Map** tab
2. Select a supplier file to configure
3. For each Shopify field, choose:
   - **Column Mapping:** Select corresponding supplier column
   - **Custom Text:** Enter fixed text value
   - **Tags:** Select multiple columns to combine

**Mapping Types:**
- **🔗 Column Mapping:** Direct field-to-field mapping
- **📝 Custom Text:** Fixed values (e.g., "Published" = "TRUE")
- **🏷️ Tags:** Combine multiple supplier columns into one tag field

**Status Indicators:**
- 🟢 **Mapped:** Column successfully mapped
- 🔵 **Custom:** Using custom text value
- 🟡 **Required:** Field marked as required but not mapped
- 🔴 **Missing:** No mapping configured

### Step 4: Export Processing

**Purpose:** Generate final Shopify-ready CSV file.

**Features:**
- **Duplicate Handling:** Automatically removes duplicate SKUs, keeping lowest cost
- **Vendor Statistics:** Shows product count by supplier
- **Cost Optimization:** Displays savings from choosing best prices
- **Export Options:** Download processed CSV file

**Process:**
1. Go to **⚡ Export** tab
2. Review vendor breakdown and statistics
3. Click "📥 Download CSV" to get final file
4. Import into Shopify

### Step 5: Product Quoting

**Purpose:** Search and compare prices across all suppliers.

#### Generate Quote Database
1. Go to **💰 Quoting** tab
2. Click "🔄 Generate Quote Data"
3. System creates searchable database with ALL supplier entries (no duplicates removed)

#### Search Products
1. Enter SKU(s) in search box or use bulk search
2. Click "🔍 Search Products"
3. View results with:
   - **🏆 Best Price:** Lowest cost product highlighted at top
   - **📊 All Options:** Every supplier option with pricing
   - **🖼️ Images:** Product photos when available

#### Export Search Results
1. Use "📥 Export to CSV" to save search results
2. Clear results with "🗑️ Clear Results"

## ⚙️ Supplier Configuration

### Adding New Suppliers

1. Go to **📁 Upload** tab
2. Expand "🔧 Supplier Configuration"
3. Fill in new supplier details:
   - **Supplier Key:** Unique identifier (lowercase, no spaces)
   - **Display Name:** Human-readable name
   - **Download URL:** API endpoint for data retrieval
   - **Filename:** Local filename for downloaded data
4. Click "➕ Add Supplier"

### Editing Existing Suppliers

1. In the same configuration section
2. Update supplier information
3. Click "💾 Update" to save changes
4. Use "🗑️ Remove" to delete suppliers

### Default Suppliers

The system comes pre-configured with:
- **Leader Systems:** Partner API integration
- **AusComp:** Token-based API access
- **CompuWorld:** Email/ID parameter system

## 📁 File Structure

```
ETECPLUS-Datafeeds/
├── streamlit_app.py          # Main application
├── requirements.txt          # Python dependencies
├── supplier_config.json     # Supplier API configurations
├── suppliers/               # Downloaded supplier files
│   ├── leader_systems_*.csv
│   ├── auscomp_*.csv
│   └── compuworld_*.csv
├── mappings/               # Saved configurations
│   └── shopify_template.json
└── quoting/               # Quote database
    └── export_data_for_quoting.csv
```

## 🔧 Troubleshooting

### Common Issues

#### "No supplier mappings found"
- **Solution:** Complete the mapping process in the Map tab
- **Check:** Ensure supplier files are uploaded and recognized

#### "Cost per item not found"
- **Solution:** Map the supplier's cost column to "Cost per item" field
- **Alternative:** Use another price field if cost data isn't available

#### Search returns no results
- **Solution:** Generate quote data first using "🔄 Generate Quote Data"
- **Check:** Ensure SKUs exist in your supplier data

#### File download fails
- **Solution:** Check supplier URL configuration
- **Check:** Verify internet connection and API credentials

### Performance Tips

- **Large Files:** Process one supplier at a time for very large datasets
- **Memory Usage:** Close browser tabs when processing multiple large files
- **Search Speed:** Use specific SKUs rather than broad searches

### Data Quality

- **SKU Consistency:** Ensure SKUs are formatted consistently across suppliers
- **Price Format:** Check that cost data is in numeric format
- **Image URLs:** Verify image links are accessible HTTP/HTTPS URLs

## 📞 Support

For issues, questions, or feature requests:
- Create an issue on GitHub
- Check the in-app help section (📖 expandable guide)
- Review error messages in the Streamlit interface

## 🔄 Updates

The application automatically handles:
- Session state management
- File persistence
- Configuration updates
- Template changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using Streamlit, Pandas, and Python**
