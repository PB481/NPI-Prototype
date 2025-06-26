import streamlit as st
import pandas as pd
import numpy as np
import io
import inspect # Import the inspect module
import datetime # Import datetime module

st.set_page_config(layout="wide")
st.title("Dividend Receivable Report Generator")

st.markdown("""
This application helps in enriching a standard **Dividend Receivable Report** with **MSCI data** to calculate **Non-Permissible Income (NPI)** under Shariah Fund Policy.

**How it works:**
1.  **Upload two files:**
    *   A custom deal text file (e.g., `_deal_custom_20250323_D_712743.txt`) containing detailed MSCI dividend information, including `net_domestic_amount_to_purify`.
    *   Your standard Dividend Receivable Excel report (e.g., `Divdends_Receivable_Report_Test.xlsx`).
2.  The app merges the two datasets based on security identifiers (ISIN/Security Sedol).
3.  It then calculates **Non-Permissible Income (NPI Base)** for each security by multiplying `net_domestic_amount_to_purify` from the MSCI data with the `Accrued Income Net (Base)` from your dividend report.
4.  A **Total NPI** is also calculated and added to the summary section of the report.
5.  The enriched report is then available for download as an Excel file.

**Note:** The app includes checks for security count mismatches between files and highlights if multiple entries for the same ISIN are found in the MSCI data.
""")

# Date input for calculation
calculation_date = st.date_input("Select NPI Calculation Date", datetime.date.today())

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

        # Convert xd_date to datetime objects for filtering
        deal_df['xd_date'] = pd.to_datetime(deal_df['xd_date'], format='%Y%m%d', errors='coerce')

        # Filter deal_df based on calculation_date
        deal_df_filtered = deal_df[deal_df['xd_date'] <= pd.to_datetime(calculation_date)]

        deal_subset = deal_df_filtered[['isin', 'net_domestic_amount_to_purify']]

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
        deal_securities = set(deal_df_filtered['isin'].unique()) # Use filtered deal_df for this check

        if len(excel_securities) != len(deal_securities):
            st.warning(f"Security count mismatch! Excel file has {len(excel_securities)} unique securities, while filtered text file has {len(deal_securities)}.")
            st.warning(f"Securities only in Excel: {excel_securities - deal_securities}")
            st.warning(f"Securities only in Filtered Text: {deal_securities - excel_securities}")
            # Do not stop, just warn

        # New Check: Duplicate ISINs in deal_df_filtered
        duplicate_isins = deal_df_filtered[deal_df_filtered.duplicated(subset=['isin'], keep=False)]['isin'].unique()
        if len(duplicate_isins) > 0:
            st.warning(f"Multiple entries found for the following ISIN(s) in the filtered text file: {', '.join(duplicate_isins)}.")
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

st.markdown("---") # Add a horizontal rule

# --- Source Code Expander ---
with st.expander("View Application Source Code"):
    source_code = inspect.getsource(inspect.currentframe())
    st.code(source_code, language='python')

st.markdown("---") # Add another horizontal rule

# --- NPI Calculation Scenarios Expander ---
with st.expander("Understanding NPI Calculation and Daily Runs"):
    st.markdown("""
    This section clarifies the implications of various data points and the rationale behind daily report generation for NPI.

    ### Ex-Dividend Date (Ex Date) vs. Payment Date (Pay Date)

    *   **Ex-Dividend Date (Ex Date):** This is the date on which a stock begins trading without the right to receive the next dividend. For NPI calculation, which is typically an accrual-based purification, the ex-date (or the date of accrual) is usually more relevant than the payment date. The NPI is calculated on the *accrued* income, not necessarily the *received* cash.
    *   **Payment Date (Pay Date):** This is when the dividend is actually paid out to shareholders.

    As long as your "Accrued Income Net (Base)" in the Dividend Receivable Report correctly reflects the dividend accrual as per your accounting standards (which typically align with ex-date), the NPI calculation will follow that.

    ### FX Conversion and `net_domestic_amount_to_purify`

    Our NPI calculation is: `NPI Base = net_domestic_amount_to_purify * Accrued Income Net (Base)`.

    *   **`Accrued Income Net (Base)`:** This value from your Excel report is already in your base currency, having been converted using a specific FX rate at the time of accrual or reporting.
    *   **`net_domestic_amount_to_purify`:** This value from the MSCI text file is understood to be a **currency-agnostic ratio or factor** (e.g., 0.0205% of the dividend is non-permissible), rather than an absolute monetary amount. Therefore, no additional FX conversion is needed for this factor itself, as it's applied to an already base-currency-converted accrued income.

    ### Rationale for Daily Report Generation

    The need for daily runs of this application is driven by:

    1.  **Freshness of Input Data:**
        *   **MSCI Data (`_deal_custom_...txt`):** While the MSCI purification factors (`net_domestic_amount_to_purify`) are updated quarterly and look forward, your daily runs will ensure you are always using the *latest available* quarterly MSCI file. More importantly, the `xd_date` filtering ensures that only relevant factors for the selected calculation date are applied.
        *   **Dividend Receivable Report (`Divdends_Receivable_Report_Test.xlsx`):** If your internal dividend accrual report is generated daily and incorporates new dividends as they go ex-dividend, then running this app daily ensures the NPI calculation uses the most current accrued income figures.

    2.  **Reporting and Compliance Requirements:**
        *   **Shariah Compliance:** Shariah purification often requires timely calculation and distribution of non-permissible income. If your fund's policy dictates daily or frequent NPI calculation for compliance or operational purposes, then daily runs are necessary.
        *   **Daily NAV:** Given that the fund in question has a daily Net Asset Value (NAV), calculating NPI on a daily basis ensures that the purification amount is accurately reflected in the daily NAV, providing a precise and up-to-date picture of the fund's Shariah compliance status.

    By selecting a specific "NPI Calculation Date" in the app, you can generate the report as of any given day, ensuring the NPI calculation aligns with your daily NAV and reporting needs.
    """)
