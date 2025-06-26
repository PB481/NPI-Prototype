import streamlit as st
import pandas as pd
import re
import io

def load_data_from_upload(uploaded_file):
    if uploaded_file is None:
        st.warning("Please upload a file to proceed.")
        return pd.DataFrame()

    string_data = uploaded_file.getvalue().decode("utf-8")
    lines = string_data.splitlines()

    st.info("Starting file parsing process...")
    st.write("---") # Separator for clarity in debug messages

    # --- Step 1: Extract Column Definitions (Programmatic Names) ---
    column_definitions = []
    in_column_definition_section = False
    
    st.info("Step 1: Attempting to extract column definitions...")
    for i, line in enumerate(lines):
        # Trigger point for starting to collect column definitions
        if line.strip() == '*':
            if not in_column_definition_section:
                in_column_definition_section = True
                st.info(f"Found first '*' at line {i+1}. Starting to look for column definitions.")
                continue # Skip the '*' line itself
            else:
                # Found the second '*' or another delimiter, so we're out of the section
                st.info(f"Found second '*' at line {i+1}. Stopping column definition collection.")
                break # Stop processing lines for column definitions

        if in_column_definition_section:
            # Match lines like "# 1 Calculation Date calc_date D 8 0"
            # Capture the programmatic name (e.g., 'calc_date')
            col_match = re.match(r'#\s*\d+\s+(.+?)\s+(\w+)\s+[DNST]\s+\d+\s+\d+', line)
            if col_match:
                programmatic_name = col_match.group(2)
                column_definitions.append(programmatic_name)
                # st.write(f"Line {i+1}: Matched column definition: '{programmatic_name}'") # Uncomment for very detailed debug
            # else:
                # st.write(f"Line {i+1}: No column definition match found.") # Uncomment for very detailed debug

    if not column_definitions:
        st.error("Error in Step 1: Could not extract any column definitions. Please ensure lines like '# 1 Calculation Date calc_date D 8 0' are present and correctly formatted.")
        return pd.DataFrame()
    else:
        st.info(f"Step 1: Successfully extracted {len(column_definitions)} column names: {column_definitions[:5]}... (showing first 5)") # Show first few names
    st.write("---")


    # --- Step 2: Find the Data Start Index (The SSL line) ---
    data_start_index = -1
    st.info("Step 2: Attempting to find the start of the data section (SSL line)...")
    for i, line in enumerate(lines):
        # This regex should be robust to your SSL line with 'a' and varying '>' counts
        if re.match(r'SSL>+(SSV|SSL)', line.strip()):
            data_start_index = i + 1 # Data starts on the next line
            st.info(f"Step 2: Found data start pattern at line {i+1}. Raw data expected to begin from line {data_start_index + 1}.")
            break

    if data_start_index == -1:
        st.error("Error in Step 2: Could not find the start of data in the file. Expected a pattern like 'SSL>>>>>>SSV...' or 'SSL>>>>>>SSL...' (on a line of its own).")
        return pd.DataFrame()
    st.write("---")


    # --- Step 3: Extract Raw Data Lines ---
    raw_data = []
    st.info("Step 3: Extracting raw data rows...")
    for i, line in enumerate(lines[data_start_index:]):
        # The line index relative to the start of the slice
        original_line_number = data_start_index + i + 1
        if line.strip() == '#EOD':
            st.info(f"Found '#EOD' at line {original_line_number}. Stopping raw data extraction.")
            break
        if not line.strip(): # Skip empty lines
            # st.write(f"Line {original_line_number}: Skipping empty line.") # Uncomment for very detailed debug
            continue
        raw_data.append(line.strip())
    
    if not raw_data:
        st.error("Error in Step 3: No data rows found after the data start pattern and before '#EOD'. Please ensure data rows are present.")
        return pd.DataFrame()
    else:
        st.info(f"Step 3: Successfully extracted {len(raw_data)} raw data rows.")
        # st.write(f"First raw data line: '{raw_data[0]}'") # Uncomment for detailed debug
    st.write("---")


    # --- Step 4: Process Each Data Line (Split into parts) ---
    processed_data = []
    st.info("Step 4: Processing raw data rows into columns...")
    for i, line in enumerate(raw_data):
        cleaned_line = line.strip()
        if cleaned_line.startswith('|') and cleaned_line.endswith('|'):
            cleaned_line = cleaned_line[1:-1] # Remove first and last pipe
        
        parts = [part.strip() for part in cleaned_line.split('|')]
        processed_data.append(parts)
    
    if not processed_data:
        st.error("Error in Step 4: Failed to parse data lines into columns. Processed data is empty.")
        return pd.DataFrame()
    else:
        st.info(f"Step 4: Successfully processed {len(processed_data)} data rows. First row has {len(processed_data[0])} parts.")
        # st.write(f"First processed data parts: {processed_data[0]}") # Uncomment for detailed debug
    st.write("---")


    # --- Step 5: Create DataFrame ---
    st.info("Step 5: Creating DataFrame...")
    num_data_columns = len(processed_data[0])
    
    # Adjust column_definitions to match the actual number of data columns
    if len(column_definitions) < num_data_columns:
        for i in range(len(column_definitions), num_data_columns):
            column_definitions.append(f"Unnamed_Col_{i + 1}")
        st.warning(f"Warning in Step 5: Number of extracted column definitions ({len(column_definitions)}) is less than data columns ({num_data_columns}). Padded column names.")
    elif len(column_definitions) > num_data_columns:
        st.warning(f"Warning in Step 5: Number of extracted column definitions ({len(column_definitions)}) is greater than data columns ({num_data_columns}). Truncating column names.")
        column_definitions = column_definitions[:num_data_columns]

    df = pd.DataFrame(processed_data, columns=column_definitions)
    st.info("Step 5: DataFrame created.")
    
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
