# Import the required data engineering libraries
import yfinance as yf
import pandas as pd

# Configure pandas to display all columns without truncating them with dots
pd.set_option('display.max_columns', None)

# Configure pandas to display the full width of the data rows in a single line
pd.set_option('display.width', 1000)

# Optional: Display all rows as well if the dataset gets longer
pd.set_option('display.max_rows', None)

# Define our financial benchmarking peer group
tickers = ["AAPL", "MSFT", "GOOGL"]

# This dictionary will store our clean, isolated metrics for each company
processed_market_data = {}

print("--- Data Extraction & Ingestion ---")

for ticker in tickers:
    print(f"Connecting to API and downloading data for: {ticker}...")
    company = yf.Ticker(ticker)

    # Extract the raw balance sheet and income statements
    bs = company.balance_sheet
    is_stmt = company.income_stmt


    # Create a protective fallback function to avoid 'KeyError' crashes if
    # different tickers use slightly different names for the same financial line item.
    def extract_financial_row(dataframe, potential_labels):
        for label in potential_labels:
            if label in dataframe.index:
                return dataframe.loc[label]
        # Return zeros aligned with the statement's active dates if the item isn't found
        return pd.Series(0, index=dataframe.columns if not dataframe.empty else [])


    # Target specific metrics required for Liquidity, Leverage, and Profitability calculations
    extracted_metrics = {
        "Current_Assets": extract_financial_row(bs, ["Current Assets", "Total Current Assets"]),
        "Current_Liabilities": extract_financial_row(bs, ["Current Liabilities", "Total Current Liabilities"]),
        "Total_Debt": extract_financial_row(bs, ["Total Debt"]),
        "Stockholders_Equity": extract_financial_row(bs, ["Stockholders Equity", "Total Stockholder Equity"]),
        "Total_Revenue": extract_financial_row(is_stmt, ["Total Revenue"]),
        "Operating_Income": extract_financial_row(is_stmt, ["Operating Income"]),
        "Net_Income": extract_financial_row(is_stmt, ["Net Income"])
    }

    # Construct a cleanly formatted DataFrame where rows map to Dates and columns map to our Metrics
    company_df = pd.DataFrame(extracted_metrics)

    # Data Cleaning: Replace any empty spaces or unreported API data items seamlessly with 0
    company_df = company_df.fillna(0)

    # Save the polished data frame to our dictionary using the ticker symbol as the key
    processed_market_data[ticker] = company_df

print("\n--- Data Extraction Completed Successfully! ---")

# Print a preview of Apple's structured data matrix to verify data alignment
print("\nAligned Financial Matrix for AAPL:")
print(processed_market_data["AAPL"].head())
# ==========================================
# PHASE 3: QUANTITATIVE FINANCIAL MODELING
# ==========================================
# ==========================================
# PHASE 3: QUANTITATIVE FINANCIAL MODELING
# ==========================================
print("\n--- Initiating Phase 3: Financial Ratio Calculations ---")

# Loop through each company in our storage dictionary to apply calculations row-by-row
for ticker, df in processed_market_data.items():
    # --- 1. Liquidity Calculation ---
    df['Current_Ratio'] = df['Current_Assets'] / df['Current_Liabilities']

    # --- 2. Leverage Calculation ---
    df['Debt_to_Equity'] = df['Total_Debt'] / df['Stockholders_Equity']

    # --- 3. Profitability Calculations ---
    df['Operating_Margin'] = df['Operating_Income'] / df['Total_Revenue']
    df['Return_on_Equity'] = df['Net_Income'] / df['Stockholders_Equity']

    # --- 4. Post-Calculation Data Cleaning ---
    import numpy as np

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.fillna(0)

    # Save our updated DataFrame back into the central dictionary repository
    processed_market_data[ticker] = df

print("Financial modeling loop complete.")

# CRITICAL STEP: Define the list variables FIRST so Python knows what columns to look for
ratio_columns = ['Current_Ratio', 'Debt_to_Equity', 'Operating_Margin', 'Return_on_Equity']

# NOW run the verification loop for all peers safely
print("\n--- Phase 3 Verification: Calculated Ratios for All Peers ---")
for ticker in tickers:
    print(f"\n📊 {ticker} Historical Ratios:")
    print(processed_market_data[ticker][ratio_columns])

# ==========================================
# PHASE 4: COMPETITIVE BENCHMARKING MATRIX
# ==========================================
print("\n--- Initiating Phase 4: Compiling Competitive Benchmarking Matrix ---")

# Create an empty list to collect the summary rows for each company
benchmarking_rows = []

for ticker, df in processed_market_data.items():
    # FIX: Explicitly sort the dates descending so the newest year (2025) is ALWAYS at index 0
    df.sort_index(ascending=False, inplace=True)

    # Filter out any historical placeholder rows that contain zeros
    active_data = df[df['Total_Revenue'] > 0]

    if not active_data.empty:
        # Extract the absolute most recent year of data (the top row)
        latest_row = active_data.iloc[0].copy()

        # Pull the specific year string from the index timestamp (e.g., '2025')
        latest_row['Fiscal_Year'] = str(active_data.index[0])[:4]
        latest_row['Company'] = ticker

        benchmarking_rows.append(latest_row)

# Combine the individual rows into a unified, cross-sectional DataFrame
competitive_matrix = pd.DataFrame(benchmarking_rows)
competitive_matrix.set_index('Company', inplace=True)

# Select the target ratios we want to present to senior stakeholders
reporting_columns = ['Fiscal_Year', 'Current_Ratio', 'Debt_to_Equity', 'Operating_Margin', 'Return_on_Equity']

# Print the final polished executive dashboard
print("\n" + "=" * 85)
print("             GLOBAL TECH PEER GROUP: COMPETITIVE BENCHMARKING DASHBOARD")
print("=" * 85)
print(competitive_matrix[reporting_columns])
print("=" * 85)
print("Note: Ratios are calculated using the most recent full-year SEC filings via Yahoo Finance.")