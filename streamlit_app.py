import streamlit as st
import pandas as pd
import json
import os

# Create mappings directory if it doesn't exist
os.makedirs('mappings', exist_ok=True)

# Title of the app
st.title("ETEC+ Supplier Datafeeds")

# Load Shopify template and supplier mappings
try:
    with open('mappings/shopify_template.json', 'r') as f:
        shopify_template = json.load(f)
    with open('mappings/supplier_mappings.json', 'r') as f:
        supplier_mappings = json.load(f)
except FileNotFoundError:
    st.error("Mapping files not found. Please ensure the mapping files are in the correct location.")
    st.stop()

# Supplier management section
st.sidebar.header("Supplier Management")

# Add new supplier
with st.sidebar.expander("Add New Supplier"):
    new_supplier_name = st.text_input("Supplier Name")
    
    if new_supplier_name:
        mapping = {}
        st.write("Map supplier columns to Shopify columns:")
        
        # Only show important Shopify fields for mapping
        important_fields = [
            "Title", "Vendor", "Variant SKU", "Variant Price",
            "Variant Compare At Price", "Image Src", "Cost per item"
        ]
        
        for field in important_fields:
            mapping[field] = st.text_input(f"{field} maps to supplier column:")
        
        if st.button("Save Supplier Mapping"):
            if new_supplier_name not in supplier_mappings:
                supplier_mappings[new_supplier_name] = mapping
                with open('mappings/supplier_mappings.json', 'w') as f:
                    json.dump(supplier_mappings, f, indent=4)
                st.success(f"Added new supplier: {new_supplier_name}")
            else:
                st.error("Supplier already exists!")

# View/Edit existing suppliers
with st.sidebar.expander("View/Edit Suppliers"):
    for supplier in supplier_mappings:
        st.write(f"### {supplier}")
        st.json(supplier_mappings[supplier])

# Define suppliers list from mappings
suppliers = [
    {
        "name": supplier,
        "file_keyword": supplier,
        "item_code_col": supplier_mappings[supplier].get("Variant SKU", ""),
        "price_col": supplier_mappings[supplier].get("Cost per item", ""),
        "rrp_col": supplier_mappings[supplier].get("Variant Compare At Price", ""),
        "description_col": supplier_mappings[supplier].get("Title", ""),
        "image_url_col": supplier_mappings[supplier].get("Image Src", "")
    } for supplier in supplier_mappings
]

# Upload multiple CSV files
uploaded_files = st.file_uploader("Upload your CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    # Initialize a dictionary to store item codes, their cheapest prices, supplier, RRP, description, and image URL
    item_data = {}

    # Process each uploaded file
    for uploaded_file in uploaded_files:
        # Check file size (Streamlit's default limit is 200MB)
        file_size = uploaded_file.size / (1024 * 1024)  # Convert to MB
        if file_size > 200:
            st.error(f"File {uploaded_file.name} is too large ({file_size:.2f} MB). Please upload files smaller than 200MB.")
            continue

        # Read the CSV file into a DataFrame
        df = pd.read_csv(uploaded_file)
        
        # Debugging: Print file name and columns
        #st.write(f"Processing file: {uploaded_file.name}")
        #st.write(f"Columns in file: {df.columns.tolist()}")

        # Determine the supplier configuration based on the file name
        supplier_config = None
        for supplier in suppliers:
            if supplier["file_keyword"] in uploaded_file.name:
                supplier_config = supplier
                break
        else:
            st.error(f"File {uploaded_file.name} does not match any expected file format.")
            continue

        # Extract column names and supplier name from the configuration
        item_code_col = supplier_config["item_code_col"]
        price_col = supplier_config["price_col"]
        rrp_col = supplier_config.get("rrp_col")  # Optional column for RRP Price
        description_col = supplier_config.get("description_col")  # Optional column for Item Description
        image_url_col = supplier_config.get("image_url_col")  # Optional column for Image URL
        supplier_name = supplier_config["name"]

        # Check if the required columns exist
        if item_code_col in df.columns and price_col in df.columns:
            # Convert the price column to numeric (float), coercing errors to NaN
            df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
            
            # Drop rows with NaN values in the price column
            df = df.dropna(subset=[price_col])
            
            # Iterate through rows and update item_data
            for index, row in df.iterrows():
                item_code = row[item_code_col]
                price = row[price_col]
                rrp = row[rrp_col] if rrp_col in df.columns else 0  # Default to 0 if RRP column is missing
                description = row[description_col] if description_col in df.columns else ""  # Default to empty string if Description column is missing
                image_url = row[image_url_col] if image_url_col in df.columns else ""  # Default to empty string if Image URL column is missing
                
                # If the item code already exists, compare prices and keep the cheapest one
                if item_code in item_data:
                    if price < item_data[item_code]["Cheapest Price"]:
                        item_data[item_code] = {
                            "Cheapest Price": price,
                            "Supplier": supplier_name,
                            "RRP": rrp,  # Include RRP
                            "Description": description,  # Include Description
                            "ImageURL": image_url  # Include Image URL
                        }
                else:
                    item_data[item_code] = {
                        "Cheapest Price": price,
                        "Supplier": supplier_name,
                        "RRP": rrp,  # Include RRP
                        "Description": description,  # Include Description
                        "ImageURL": image_url  # Include Image URL
                    }
        else:
            # Provide detailed error message for missing columns
            missing_columns = []
            if item_code_col not in df.columns:
                missing_columns.append(item_code_col)
            if price_col not in df.columns:
                missing_columns.append(price_col)
            st.error(f"File {uploaded_file.name} is missing the following required columns: {', '.join(missing_columns)}.")

    # Display the results
    if item_data:
        # Convert the data to Shopify format
        shopify_data = []
        
        for item_code, data in item_data.items():
            supplier_name = data["Supplier"]
            supplier_mapping = supplier_mappings[supplier_name]
            
            shopify_row = {col: "" for col in shopify_template["template_columns"]}
            
            # Generate handle from description (if available)
            handle = data["Description"].lower().replace(" ", "-")[:60] if data["Description"] else item_code
            shopify_row["Handle"] = handle
            
            # Map the data using supplier mapping
            for shopify_col, supplier_col in supplier_mapping.items():
                if supplier_col in ["Price", "ExTax", "DBP"]:
                    shopify_row[shopify_col] = data["Cheapest Price"]
                elif supplier_col == "RRP":
                    shopify_row[shopify_col] = data["RRP"]
                elif supplier_col == "Description":
                    shopify_row[shopify_col] = data["Description"]
                elif supplier_col in ["Image", "IMAGE"]:
                    shopify_row[shopify_col] = data["ImageURL"]
            
            # Set default values
            shopify_row["Variant Inventory Policy"] = "deny"
            shopify_row["Variant Fulfillment Service"] = "manual"
            shopify_row["Variant Requires Shipping"] = "true"
            shopify_row["Variant Taxable"] = "true"
            shopify_row["Status"] = "active"
            
            shopify_data.append(shopify_row)
        
        # Convert to DataFrame
        shopify_df = pd.DataFrame(shopify_data)
        
        # Display preview
        st.write("### Preview of Shopify Format")
        st.dataframe(shopify_df)
        
        # Export the results as a Shopify CSV file
        csv = shopify_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Shopify CSV",
            data=csv,
            file_name="shopify_import.csv",
            mime="text/csv",
        )
        
        # Also show the original comparison data
        st.write("### Original Comparison Data")
        comparison_df = pd.DataFrame([
            {
                "Item Code": item_code,
                "Cheapest Price": data["Cheapest Price"],
                "Supplier": data["Supplier"],
                "RRP": data["RRP"],
                "Description": data["Description"],
                "ImageURL": data["ImageURL"]
            }
            for item_code, data in item_data.items()
        ])
        st.dataframe(comparison_df)
    else:
        st.warning("No valid data found in the uploaded files.")
else:
    st.info("Please upload CSV files to get started.")