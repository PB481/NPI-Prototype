import streamlit as st
import pandas as pd
import re

def load_data(file_path):
    """
    Loads and parses the data from the custom text file.
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find the line that defines column headers (e.g., "# 1        2       3 ...")
    header_line_index = -1
    for i, line in enumerate(lines):
        if re.match(r'^#\s*\d+\s+\d+\s+\d+', line):
            header_line_index = i
            break

    if header_line_index == -1:
        st.error("Could not find the header line in the file.")
        return pd.DataFrame()

    # Extract column names from the lines starting with '#'
    column_definitions = []
    for line in lines:
        if line.startswith('#') and ' #' not in line and 'Reserved' not in line and 'EOD' not in line and not re.match(r'^#\s*\d+\s+\d+\s+\d+', line):
            parts = line.strip().split(None, 3) # Split by whitespace, max 3 splits
            if len(parts) >= 4:
                # Extract the field name, which is the third part
                column_definitions.append(parts[2])

    # The actual data starts after the "SSL>>>..." line
    data_start_index = -1
    for i, line in enumerate(lines):
        if line.startswith('SSL>>>>>>>SSV'): # This specific pattern indicates the start of data format
            data_start_index = i + 1 # Data starts on the next line
            break

    if data_start_index == -1:
        st.error("Could not find the start of data in the file.")
        return pd.DataFrame()

    # Extract raw data lines
    raw_data = []
    for line in lines[data_start_index:]:
        if line.strip() == '#EOD' or not line.strip(): # Stop at #EOD or empty lines
            break
        raw_data.append(line.strip())

    # Process each data line
    processed_data = []
    for line in raw_data:
        # Remove the leading '| ' and trailing ' |' if they exist, then split by '|'
        cleaned_line = line.strip()
        if cleaned_line.startswith('|') and cleaned_line.endswith('|'):
            cleaned_line = cleaned_line[1:-1]
        
        # Split by '|' and strip whitespace from each part
        parts = [part.strip() for part in cleaned_line.split('|')]
        processed_data.append(parts)

    # Create DataFrame
    # Ensure column_definitions has enough names for all parts
    # If the number of columns in data doesn't match the definitions,
    # we'll truncate or pad column_definitions as needed for DataFrame creation.
    if processed_data:
        num_data_columns = len(processed_data[0])
        if len(column_definitions) < num_data_columns:
            # Pad with generic names if definitions are fewer than actual data columns
            for i in range(len(column_definitions), num_data_columns):
                column_definitions.append(f"Unnamed_Column_{i+1}")
        elif len(column_definitions) > num_data_columns:
            # Truncate if definitions are more than actual data columns
            column_definitions = column_definitions[:num_data_columns]

        df = pd.DataFrame(processed_data, columns=column_definitions)
    else:
        df = pd.DataFrame()

    return df

# Streamlit App
st.title("Custom Deal Security File Viewer")

file_path = "_deal_custom_20250323_D_712743.txt" # Path to your uploaded file

if st.button("Load Data"):
    if pd.isna(file_path):
        st.warning("Please ensure the file '_deal_custom_20250323_D_712743.txt' is in the same directory.")
    else:
        df = load_data(file_path)
        if not df.empty:
            st.success("Data loaded successfully!")
            st.dataframe(df)
            st.write("First 5 rows of the data:")
            st.write(df.head())
        else:
            st.error("Failed to load data. Please check the file format.")
