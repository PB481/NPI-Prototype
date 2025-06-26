import streamlit as st
import pandas as pd
import re
import io

# --- Function to load and parse the custom TXT file ---
def load_txt_data(uploaded_txt_file):
    if uploaded_txt_file is None:
        return pd.DataFrame(), "No TXT file uploaded."

    try:
        string_data = uploaded_txt_file.getvalue().decode("utf-8")
        lines = string_data.splitlines()

        column_definitions = []
        in_column_definition_section = False
        for line in lines:
            if line.strip() == '*':
                if not in_column_definition_section:
                    in_column_definition_section = True
                    continue
                else:
                    break
            if in_column_definition_section:
                col_match = re.match(r'#\s*\d+\s+(.+?)\s+(\w+)\s+[DNST]\s+\d+\s+\d+', line)
                if col_match:
                    programmatic_name = col_match.group(2)
                    column_definitions.append(programmatic_name)

        if not column_definitions:
            return pd.DataFrame(), "Error: Could not extract any column definitions from TXT file."

        data_start_index = -1
        for i, line in enumerate(lines):
            if re.match(r'SSL>+(SSV|SSL)', line.strip()):
                data_start_index = i + 1
                break

        if data_start_index == -1:
            return pd.DataFrame(), "Error: Could not find the start of data in TXT file."

        raw_data = []
        for line in lines[data_start_index:]:
            if line.strip() == '#EOD' or not line.strip():
                break
            if not line.strip():
                continue
            raw_data.append(line.strip())

        if not raw_data:
            return pd.DataFrame(), "Error: No raw data rows found in TXT file."

        processed_data = []
        for line in raw_data:
            cleaned_line = line.strip()
            if cleaned_line.startswith('|') and cleaned_line.endswith('|'):
                cleaned_line = cleaned_line[1:-1]
            parts = [part.strip() for part in cleaned_line.split('|')]
            processed_data.append(parts)

        if not processed_data:
            return pd.DataFrame(), "Error: Failed to parse data lines into columns from TXT file."

        num_data_columns = len(processed_data[0])
        if len(column_definitions) < num_data_columns:
            for i in range(len(column_definitions), num_data_columns):
                column_definitions.append(f"Unnamed_Col_{i + 1}")
        elif len(column_definitions) > num_data_columns:
            column_definitions = column_definitions[:num_data_columns]

        txt_df = pd.DataFrame(processed_data, columns=column_definitions)
        return txt_df, "TXT file loaded successfully."

    except Exception as e:
        return pd.DataFrame(), f"An unexpected error occurred while processing TXT: {e}"


# --- Streamlit App ---
st.set_page_config(layout="wide") # Use wide layout for better table viewing
st.title("Dividend Data Merger & NPI Calculator")
st.write("Upload your Dividend Receivable Report (CSV/Excel) and the custom Deal Security TXT file.")

# File uploaders
uploaded_excel_file = st.file_uploader("Upload Dividends Receivable Report (CSV/Excel)", type=["csv", "xlsx"])
uploaded_txt_file = st.file_uploader("Upload Custom Deal Security TXT File", type=["txt"])

# Process files only if both are uploaded
if uploaded_excel_file and uploaded_txt_file:
    st.success("Both files uploaded! Click 'Process Data' to continue.")
    
    if st.button("Process Data"):
        # --- Load Excel (CSV) Data ---
        excel_df = pd.DataFrame()
        excel_load_status = ""
        try:
            if uploaded_excel_file.name.endswith('.csv'):
                excel_df = pd.read_csv(uploaded_excel_file, header=18)
            elif uploaded_excel_file.name.endswith('.xlsx'):
                excel_df = pd.read_excel(uploaded_excel_file, header=18)
            
            excel_df.columns = excel_df.columns.str.strip() # Clean up column names
            excel_load_status = "Excel file loaded successfully."

            # Debugging: Check if key columns exist in Excel DF
            if 'ISIN' not in excel_df.columns:
                excel_load_status += "\nWarning: 'ISIN' column not found in Excel file. Merge might fail."
            if 'Accured Income Net (Base)' not in excel_df.columns:
                 excel_load_status += "\nWarning: 'Accured Income Net (Base)' column not found in Excel file. NPI calculation might fail."

            st.subheader("Dividends Receivable Report Preview")
            st.dataframe(excel_df.head())
            st.info(excel_load_status)

        except Exception as e:
            excel_load_status = f"Error loading Excel file: {e}"
            st.error(excel_load_status)
            excel_df = pd.DataFrame() # Ensure df is empty on error


        # --- Load TXT Data ---
        txt_df, txt_load_status = load_txt_data(uploaded_txt_file)
        if not txt_df.empty:
            st.subheader("Custom Deal Security TXT File Preview")
            st.dataframe(txt_df.head())
            st.info(txt_load_status)
            # Debugging: Check if key columns exist in TXT DF
            if 'isin' not in txt_df.columns:
                txt_load_status += "\nWarning: 'isin' column not found in TXT file. Merge might fail."
            if 'net_domestic_amount_to_purify' not in txt_df.columns:
                 txt_load_status += "\nWarning: 'net_domestic_amount_to_purify' column not found in TXT file. NPI calculation might fail."
        else:
            st.error(txt_load_status) # Display the error message from load_txt_data

        # --- Merge and Calculate NPI if both DFs are loaded ---
        if not excel_df.empty and not txt_df.empty:
            st.subheader("Merging DataFrames...")
            # Ensure the key columns are of compatible types (string) and clean them
            excel_df['ISIN'] = excel_df['ISIN'].astype(str).str.strip()
            txt_df['isin'] = txt_df['isin'].astype(str).str.strip()

            # Perform the merge using 'ISIN' from both dataframes
            merged_df = pd.merge(excel_df, txt_df[['isin', 'net_domestic_amount_to_purify']],
                                 left_on='ISIN', right_on='isin', how='left')

            # Drop the duplicate 'isin' column from the merge
            merged_df.drop(columns=['isin'], inplace=True, errors='ignore') # errors='ignore' to prevent error if 'isin' doesn't exist

            st.success("DataFrames merged!")
            
            # --- Calculate NPI ---
            st.subheader("Calculating NPI...")
            # Ensure 'Accured Income Net (Base)' and 'net_domestic_amount_to_purify' are numeric
            if 'Accured Income Net (Base)' in merged_df.columns:
                # Clean the 'Accured Income Net (Base)' column: remove non-numeric chars except digits, dot, and minus sign
                merged_df['Accured Income Net (Base)'] = merged_df['Accured Income Net (Base)'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                merged_df['Accured Income Net (Base)'] = pd.to_numeric(merged_df['Accured Income Net (Base)'], errors='coerce')
            else:
                st.warning("'Accured Income Net (Base)' column not found after merge. Cannot calculate NPI accurately.")

            if 'net_domestic_amount_to_purify' in merged_df.columns:
                merged_df['net_domestic_amount_to_purify'] = pd.to_numeric(merged_df['net_domestic_amount_to_purify'], errors='coerce')
            else:
                st.warning("'net_domestic_amount_to_purify' column not found after merge. Cannot calculate NPI accurately.")

            # Perform calculation only if both columns exist and are numeric
            if 'Accured Income Net (Base)' in merged_df.columns and 'net_domestic_amount_to_purify' in merged_df.columns:
                merged_df['Accured Income Net (Base)'].fillna(0, inplace=True)
                merged_df['net_domestic_amount_to_purify'].fillna(0, inplace=True)
                merged_df['NPI'] = merged_df['Accured Income Net (Base)'] * merged_df['net_domestic_amount_to_purify']
                st.success("NPI calculated!")
            else:
                st.error("NPI calculation skipped due to missing or invalid source columns.")
                merged_df['NPI'] = None # Assign None or NaN if calculation can't proceed

            st.subheader("Final Merged Data with NPI")
            st.dataframe(merged_df)

            st.subheader("Sample of Key Columns and NPI")
            # Filter for relevant columns if they exist
            display_cols = ['ISIN', 'Accured Income Net (Base)', 'net_domestic_amount_to_purify', 'NPI']
            display_cols = [col for col in display_cols if col in merged_df.columns]
            st.dataframe(merged_df[display_cols].head(10))

        else:
            st.error("Cannot perform merge and NPI calculation. Please resolve issues with file uploads/parsing.")

elif uploaded_excel_file or uploaded_txt_file:
    st.info("Please upload both files to proceed.")

else:
    st.info("Waiting for file uploads...")
