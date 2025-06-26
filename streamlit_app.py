import streamlit as st
import pandas as pd
import re
import io # Import the io module for handling in-memory files

def load_data_from_upload(uploaded_file):
    """
    Loads and parses the data from an uploaded custom text file.
    """
    if uploaded_file is None:
        st.warning("Please upload a file to proceed.")
        return pd.DataFrame()

    # Read the file content into a string
    string_data = uploaded_file.getvalue().decode("utf-8")
    lines = string_data.splitlines()

    # Find the line that defines column headers (e.g., "# 1        2       3 ...")
    header_line_index = -1
    for i, line in enumerate(lines):
        # This regex looks for a line starting with '#', followed by a number, then spaces, then another number
        if re.match(r'^#\s*\d+\s+\d+\s+\d+', line): [cite: 20, 21, 22, 23, 24, 25, 26, 27]
            header_line_index = i
            break

    if header_line_index == -1:
        st.error("Could not find the header line in the file. Expected pattern like '# 1        2       3 ...'")
        return pd.DataFrame()

    # Extract column names from the lines starting with '#'
    column_definitions = []
    for line in lines:
        # Check if line starts with '#' and is not the data structure line or #EOD
        # Also, ensure it's not a line of just '#' or 'Reserved' or the numbered header line
        if line.startswith('#') and \
           not re.match(r'^#\s*\d+\s+\d+\s+\d+', line) and \
           '#EOD' not in line and \
           '#' not in line[1:] and \
           'Reserved' not in line and \
           not re.match(r'^#\s*\d+\s+.*', line): # Avoid lines like '# 1        2       3 ...' and commented lines
            parts = line.strip().split(None, 3) # Split by whitespace, max 3 splits
            if len(parts) >= 3: # Ensure there's at least a number, descriptive name, and programmatic name
                column_definitions.append(parts[2]) # programmatic name is the third part

    # The actual data starts after the "SSL>>>..." line
    data_start_index = -1
    for i, line in enumerate(lines):
        # Relaxed regex to match 'SSL' followed by any number of '>' and then 'SSV' or 'SSL'
        if re.match(r'SSL>+(SSV|SSL)', line): [cite: 27]
            data_start_index = i + 1 # Data starts on the next line
            break

    if data_start_index == -1:
        st.error("Could not find the start of data in the file. Expected a pattern like 'SSL>>>>>>SSV...' or 'SSL>>>>>>SSL...'")
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
        if cleaned_line.startswith('|') and cleaned_line.endswith('|'): [cite: 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43]
            cleaned_line = cleaned_line[1:-1] # Remove first and last pipe
        
        parts = [part.strip() for part in cleaned_line.split('|')] [cite: 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43]
        processed_data.append(parts)

    # Create DataFrame
    if processed_data:
        num_data_columns = len(processed_data[0])
        
        # Adjust column_definitions to match the actual number of data columns
        if len(column_definitions) < num_data_columns:
            # Pad with generic names if definitions are fewer than actual data columns
            for i in range(len(column_definitions), num_data_columns):
                column_definitions.append(f"Reserved_{i+1}") # Simplified for dynamically added 'Reserved'
        elif len(column_definitions) > num_data_columns:
            # Truncate if definitions are more than actual data columns
            column_definitions = column_definitions[:num_data_columns]

        df = pd.DataFrame(processed_data, columns=column_definitions)
    else:
        df = pd.DataFrame()

    return df

# Streamlit App
st.title("Custom Deal Security File Uploader")

uploaded_file = st.file_uploader("Choose a .txt file", type="txt")

if uploaded_file is not None:
    st.write(f"File uploaded: {uploaded_file.name}")
    
    # You can add a button to trigger processing after upload, or process immediately
    if st.button("Process Uploaded File"):
        df = load_data_from_upload(uploaded_file)
        if not df.empty:
            st.success("Data loaded successfully!")
            st.write("---")
            st.subheader("Raw Data Preview (First 5 Rows)")
            st.dataframe(df.head())
            st.write("---")
            st.subheader("Full Loaded Data")
            st.dataframe(df)
        else:
            st.warning("No data was loaded. Please check the uploaded file format and content.")
else:
    st.info("Upload a .txt file to view its structured data.")
