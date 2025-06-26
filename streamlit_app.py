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

    st.info("Attempting to parse uploaded file...")

    # --- Step 1: Extract Column Definitions ---
    column_definitions = []
    # This flag indicates when we are in the section where column names are listed
    in_column_definition_section = False
    
    # Iterate through lines to find the section containing column definitions
    for line in lines:
        if line.strip() == '*': # '*' acts as a section delimiter
            if not in_column_definition_section:
                in_column_definition_section = True # Found the start of the column definition section
                continue # Skip the '*' line itself
            else:
                # Found the second '*' or another delimiter, so we're out of the section
                break # Stop processing lines for column definitions

        if in_column_definition_section:
            # Regex to match lines like "# 1 Calculation Date calc_date D 8 0"
            # Group 1: Descriptive Name (e.g., "Calculation Date")
            # Group 2: Programmatic Name (e.g., "calc_date") - this is what we want
            col_match = re.match(r'#\s*\d+\s+(.+?)\s+(\w+)\s+[DNST]\s+\d+\s+\d+', line)
            if col_match:
                column_definitions.append(col_match.group(2)) # Extract the programmatic name

    if not column_definitions:
        st.error("Could not extract any column definitions. Please check the format of the header lines.")
        return pd.DataFrame()
    else:
        st.info(f"Detected {len(column_definitions)} column names.")
        # st.write(f"Extracted column definitions: {column_definitions}") # For deep debugging


    # --- Step 2: Find the Data Start Index ---
    data_start_index = -1
    for i, line in enumerate(lines):
        # Relaxed regex to match 'SSL' followed by any number of '>' and then 'SSV' or 'SSL'
        # This covers patterns like "SSL>>>>>>>SSV" or "SSL>>>>>>>>>>>>>>>a>>>>SSL"
        if re.match(r'SSL>+(SSV|SSL)', line.strip()):
            data_start_index = i + 1 # Data starts on the next line
            st.info(f"Found data start pattern at line {i+1}. Data expected to start at line {data_start_index + 1}.")
            break

    if data_start_index == -1:
        st.error("Could not find the start of data in the file. Expected a pattern like 'SSL>>>>>>SSV...' or 'SSL>>>>>>SSL...'.")
        return pd.DataFrame()


    # --- Step 3: Extract Raw Data Lines ---
    raw_data = []
    for line in lines[data_start_index:]:
        if line.strip() == '#EOD' or not line.strip(): # Stop at #EOD or empty lines
            break
        raw_data.append(line.strip())
    
    if not raw_data:
        st.error("No data rows found after the data start pattern and before '#EOD'.")
        return pd.DataFrame()
    else:
        st.info(f"Extracted {len(raw_data)} raw data rows.")


    # --- Step 4: Process Each Data Line ---
    processed_data = []
    for line in raw_data:
        # Remove the leading '|' and trailing '|' if they exist, then split by '|'
        cleaned_line = line.strip()
        if cleaned_line.startswith('|') and cleaned_line.endswith('|'):
            cleaned_line = cleaned_line[1:-1] # Remove first and last pipe
        
        parts = [part.strip() for part in cleaned_line.split('|')]
        processed_data.append(parts)

    if not processed_data:
        st.error("Failed to parse data lines into columns. Processed data is empty.")
        return pd.DataFrame()

    # --- Step 5: Create DataFrame ---
    # Adjust column_definitions to match the actual number of data columns
    num_data_columns = len(processed_data[0])
    st.info(f"First data row has {num_data_columns} columns.")
    st.info(f"Number of extracted column definitions: {len(column_definitions)}")

    if len(column_definitions) < num_data_columns:
        # Pad with generic names if definitions are fewer than actual data columns
        for i in range(len(column_definitions), num_data_columns):
            column_definitions.append(f"Unnamed_Col_{i + 1}")
        st.warning(f"Column definitions ({len(column_definitions)}) mismatch data columns ({num_data_columns}). Padded column names.")
    elif len(column_definitions) > num_data_columns:
        # Truncate if definitions are more than actual data columns
        st.warning(f"Column definitions ({len(column_definitions)}) mismatch data columns ({num_data_columns}). Truncating column names.")
        column_definitions = column_definitions[:num_data_columns]

    df = pd.DataFrame(processed_data, columns=column_definitions)
    
    return df

# Streamlit App
st.title("Custom Deal Security File Uploader")

uploaded_file = st.file_uploader("Choose a .txt file", type="txt")

if uploaded_file is not None:
    st.write(f"File uploaded: **{uploaded_file.name}**")
    
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
            st.warning("No data was loaded. Please check the uploaded file format and content, and any error messages above.")
else:
    st.info("Upload a .txt file to view its structured data.")
