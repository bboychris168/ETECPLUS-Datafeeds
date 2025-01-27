import streamlit as st
import pandas as pd

# Title of the app
st.title("ETEC+ Supplier Datafeeds")

# Define a list of supplier configurations
suppliers = [
    {
        "name": "Auscomp",
        "file_keyword": "Auscomp",  # Keyword to identify the file
        "item_code_col": "Manufacturer ID",
        "price_col": "Price",
        "rrp_col": "RRP",  # Column for RRP Price
        "description_col": "Description",  # Column for Item Description
        "image_url_col": "ImageURL"  # Column for Image URL
    },
    {
        "name": "Compuworld",
        "file_keyword": "Compuworld",
        "item_code_col": "Manufacture Code",
        "price_col": "ExTax",
        "rrp_col": "RRP",  # Column for RRP Price
        "description_col": "Description",  # Column for Item Description
        "image_url_col": "ImageURL"  # Column for Image URL
    },
    {
        "name": "Leaders",
        "file_keyword": "Leaders",
        "item_code_col": "MANUFACTURER SKU",
        "price_col": "DBP",
        "rrp_col": "RRP",  # Column for RRP Price
        "description_col": "Description",  # Column for Item Description
        "image_url_col": "ImageURL"  # Column for Image URL
    }
    # Add more suppliers here as needed
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
        st.write("### Item Codes, Cheapest Prices, Suppliers, RRP, Descriptions, and Image URLs")
        # Convert the dictionary to a DataFrame
        result_df = pd.DataFrame([
            {
                "Item Code": item_code,
                "Cheapest Price": data["Cheapest Price"],
                "Supplier": data["Supplier"],
                "RRP": data["RRP"],  # Include RRP
                "Description": data["Description"],  # Include Description
                "ImageURL": data["ImageURL"]  # Include Image URL
            }
            for item_code, data in item_data.items()
        ])

        # Add a column with HTML image tags for display
        result_df["Image"] = result_df["ImageURL"].apply(
            lambda url: f'<img src="{url}" width="100">' if url else ""
        )

        # Display the DataFrame with images using HTML
        st.write(
            result_df[["Item Code", "Cheapest Price", "Supplier", "RRP", "Description", "Image"]].to_html(escape=False),
            unsafe_allow_html=True
        )

        # Export the results as a CSV file (without the HTML image column)
        csv = result_df.drop(columns=["Image"]).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="cheapest_prices_with_rrp_description_and_images.csv",
            mime="text/csv",
        )
    else:
        st.warning("No valid data found in the uploaded files.")
else:
    st.info("Please upload CSV files to get started.")