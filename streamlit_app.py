import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(layout="wide")
st.title("Dividend Receivable Report Generator")

st.write("Upload your _deal_custom_ text file and Divdends_Receivable_Report_Test Excel file to generate the combined report.")

# File uploaders
deal_file = st.file_uploader("Upload _deal_custom_20250323_D_712743.txt", type=["txt"])
excel_file = st.file_uploader("Upload Divdends_Receivable_Report_Test.xlsx", type=["xlsx"])

if deal_file and excel_file:
    st.success("Files uploaded successfully!")

    try:
        # --- 1. Read deal data from text file ---
        deal_lines = deal_file.getvalue().decode("utf-8").splitlines()

        data = []
        for line in deal_lines:
            if line.startswith('|'):
                fields = [x.strip() for x in line.split('|')[1:-1]]
                data.append(fields)

        columns = [
            'calc_date', 'msci_index_code', 'msci_dividend_code', 'xd_date', 'reinvestment_in_index_date',
            'dividend_description', 'msci_security_code', 'msci_timeseries_code', 'msci_issuer_code',
            'security_name', 'bb_ticker', 'dividend_ISO_currency_symbol', 'unadjusted_dividend_amount',
            'dividend_sub_unit', 'dividend_adjustment_factor', 'adjusted_grs_dividend_amount',
            'withholding_tax_rate', 'adj_net_dividend_amount_int', 'adj_net_dividend_amount_dom',
            'purified_dividend_adjust_fact', 'purified_adj_grs_div_amount', 'purified_adj_net_div_amnt_int',
            'purified_adj_net_div_amnt_dom', 'gross_amount_to_purify', 'net_intl_amount_to_purify',
            'net_domestic_amount_to_purify', 'isin', 'reserved_1', 'reserved_2', 'reserved_3', 'reserved_4',
            'reserved_5', 'reserved_6', 'reserved_7', 'reserved_8', 'reserved_9', 'reserved_10',
            'reserved_11', 'reserved_12', 'reserved_13', 'reserved_14', 'reserved_15', 'reserved_16',
            'reserved_17', 'reserved_18', 'reserved_19'
        ]
        deal_df = pd.DataFrame(data, columns=columns)
        deal_subset = deal_df[['isin', 'net_domestic_amount_to_purify']]

        # --- 2. Read report data from Excel file ---
        excel_data = io.BytesIO(excel_file.getvalue())
        report_df = pd.read_excel(excel_data, header=None)

        # --- 3. Split report into summary and details ---
        details_start_index = report_df[report_df[0] == 'DIVIDENDS RECIEVABLE DEATAILS'].index[0]
        details_header_index = details_start_index + 2
        details_data_start_index = details_header_index + 1

        summary_df = report_df.iloc[:details_header_index].copy()
        details_df = report_df.iloc[details_data_start_index:].copy()
        details_df.columns = report_df.iloc[details_header_index]

        # Ensure 'Security Sedol' is string type for merging
        details_df['Security Sedol'] = details_df['Security Sedol'].astype(str)

        # --- Validation Checks ---
        # Check 1: Security Count Check
        excel_securities = set(details_df['Security Sedol'].unique())
        deal_securities = set(deal_df['isin'].unique())

        if len(excel_securities) != len(deal_securities):
            st.warning(f"Security count mismatch! Excel file has {len(excel_securities)} unique securities, while text file has {len(deal_securities)}.")
            st.warning(f"Securities only in Excel: {excel_securities - deal_securities}")
            st.warning(f"Securities only in Text: {deal_securities - excel_securities}")
            # Do not stop, just warn

        # New Check: Duplicate ISINs in deal_df
        duplicate_isins = deal_df[deal_df.duplicated(subset=['isin'], keep=False)]['isin'].unique()
        if len(duplicate_isins) > 0:
            st.warning(f"Multiple entries found for the following ISIN(s) in the text file: {', '.join(duplicate_isins)}.")
            st.warning("This might lead to unexpected results in the NPI Base calculation if not handled as intended.")
            # Do not stop, just warn

        # --- 4. Merge and calculate (using the original details_df for the main merge) ---
        merged_df = pd.merge(details_df, deal_subset, left_on='Security Sedol', right_on='isin', how='left')

        if merged_df.empty:
            st.warning("No matching ISINs found between the uploaded files. Please check the 'Security Sedol' column in your Excel file and 'isin' in your text file.")
            st.stop()

        merged_df['net_domestic_amount_to_purify'] = pd.to_numeric(merged_df['net_domestic_amount_to_purify'].replace('', np.nan), errors='coerce')
        merged_df['Accured Income Net (Base)'] = pd.to_numeric(merged_df['Accured Income Net (Base)'], errors='coerce')
        merged_df['NPI Base'] = merged_df['net_domestic_amount_to_purify'] * merged_df['Accured Income Net (Base)']

        # --- 5. Clean up and calculate total ---
        merged_df['net_domestic_amount_to_purify'] = merged_df['net_domestic_amount_to_purify'].fillna(0)
        merged_df['NPI Base'] = merged_df['NPI Base'].fillna(0)
        details_df = merged_df.drop(columns=['isin']) # drop redundant isin column
        npi_base_total = details_df['NPI Base'].sum()

        # --- 6. Add total to summary ---
        total_row_index = summary_df[summary_df[0] == 'Total'].index[0]
        new_row_data = {
            0: 'Total NPI',
            3: npi_base_total
        }
        new_row = pd.DataFrame(new_row_data, index=[0])

        summary_df = pd.concat([summary_df.iloc[:total_row_index+1], new_row, summary_df.iloc[total_row_index+1:]]).reset_index(drop=True)

        # --- 7. Provide download button ---
        output_excel_buffer = io.BytesIO()
        with pd.ExcelWriter(output_excel_buffer, engine='openpyxl') as writer:
            summary_df.to_excel(writer, index=False, header=False, sheet_name='Sheet1')
            details_df.to_excel(writer, index=False, header=True, sheet_name='Sheet1', startrow=len(summary_df))
        output_excel_buffer.seek(0)

        st.download_button(
            label="Download Generated Report",
            data=output_excel_buffer,
            file_name="Dividends_Receivable_Report_with_NPI.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"An error occurred during processing: {e}")
        st.error("Please ensure the uploaded files are correct and match the expected format.")
