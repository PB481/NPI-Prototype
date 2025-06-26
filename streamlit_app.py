import streamlit as st
import pandas as pd
import re
import os # Import the os module for path operations

def load_data(file_path):
    """
    Loads and parses the data from the custom text file.
    """
    if not os.path.exists(file_path):
        st.error(f"Error: The file '{file_path}' was not found. Please ensure it's in the same directory as the script or provide the full path.")
        return pd.DataFrame()

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find the line that defines column headers (e.g., "# 1        2       3 ...")
    header_line_index = -1
    for i, line in enumerate(lines):
        if re.match(r'^#\s*\d+\s+\d+\s+\d+', line):
            header_line_index = i
            break

    if header_line_index == -1:
        st.error("Could not find the header line in the file. Expected pattern like '# 1        2       3 ...'")
        return pd.DataFrame()

    # Extract column names from the lines starting with '#'
    column_definitions = []
    # Iterate through lines to find column definitions
    for line in lines:
        # Check if line starts with '#' and is not the data structure line or #EOD
        if line.startswith('#') and \
           not re.match(r'^#\s*\d+\s+\d+\s+\d+', line) and \
           '#EOD' not in line and \
           '#' not in line[1:]: # Ensure it's a primary definition line, not a commented out data line
            parts = line.strip().split(None, 3) # Split by whitespace, max 3 splits
            if len(parts) >= 3: # Ensure there's at least a number, descriptive name, and programmatic name
                # The programmatic name is typically the third part
                column_definitions.append(parts[2])

    # The actual data starts after the "SSL>>>..." line
    data_start_index = -1
    for i, line in enumerate(lines):
        if line.startswith('SSL>>>>>>>SSV'): # This specific pattern indicates the start of data format
            data_start_index = i + 1 # Data starts on the next line
            break

    if data_start_index == -1:
        st.error("Could not find the start of data in the file. Expected pattern 'SSL>>>>>>>SSV...'")
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
        # Remove the leading '|' and trailing '|' if they exist, then split by '|'
        cleaned_line = line.strip()
        if cleaned_line.startswith('|') and cleaned_line.endswith('|'):
            cleaned_line = cleaned_line[1:-1] # Remove first and last pipe
        
        # Split by '|' and strip whitespace from each part
        parts = [part.strip() for part in cleaned_line.split('|')]
        processed_data.append(parts)

    # Create DataFrame
    if processed_data:
        num_data_columns = len(processed_data[0])
        
        # Adjust column_definitions to match the actual number of data columns
        if len(column_definitions) < num_data_columns:
            # Pad with generic names if definitions are fewer than actual data columns
            for i in range(len(column_definitions), num_data_columns):
                column_definitions.append(f"Reserved_{i+1-len(column_definitions)}") # More specific naming for padding
        elif len(column_definitions) > num_data_columns:
            # Truncate if definitions are more than actual data columns
            column_definitions = column_definitions[:num_data_columns]

        df = pd.DataFrame(processed_data, columns=column_definitions)
    else:
        df = pd.DataFrame()

    return df

# Streamlit App
st.title("Custom Deal Security File Viewer")

# Define the file path. Adjust this if your file is not in the same directory.
# Example for a specific path:
# file_path = "/path/to/your/_deal_custom_20250323_D_712743.txt"
file_path = "_deal_custom_20250323_D_712743.txt"

st.write(f"Looking for data file at: `{os.path.abspath(file_path)}`")

if st.button("Load Data"):
    df = load_data(file_path)
    if not df.empty:
        st.success("Data loaded successfully!")
        st.write("---") # Separator
        st.subheader("Raw Data Preview (First 5 Rows)")
        st.dataframe(df.head())
        st.write("---") # Separator
        st.subheader("Full Loaded Data")
        st.dataframe(df)
    else:
        st.warning("No data was loaded. Please check the file and the error messages above.")
