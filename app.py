import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. Page Configuration & Title
st.set_page_config(layout="wide", page_title="Financial Benchmarking Dashboard")
st.title("🚀 Institutional Financial Benchmarking Dashboard")
st.markdown("Interact with real-time SEC data pulled directly from the Yahoo Finance API engine.")

# 2. Interactive Sidebar Setup
st.sidebar.header("🔧 Analytics Controller")
selected_tickers = st.sidebar.multiselect(
    "Select Peer Group Tickers:",
    options=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"],
    default=["AAPL", "MSFT", "GOOGL"]
)

# Global Display Fix for Streamlit Data Processing
pd.set_option('display.float_format', lambda x: '%.2f' % x)

# 3. Data Processing Action Button
if st.sidebar.button("Execute Quantitative Model", type="primary"):
    if not selected_tickers:
        st.warning("Please select at least one ticker to begin analysis.")
    else:
        with st.spinner("Connecting to API and processing structural data..."):
            processed_market_data = {}

            # --- PHASE 2: INGESTION LOOP ---
            for ticker in selected_tickers:
                company = yf.Ticker(ticker)
                bs = company.balance_sheet
                is_stmt = company.income_stmt


                def extract_financial_row(dataframe, potential_labels):
                    for label in potential_labels:
                        if label in dataframe.index:
                            return dataframe.loc[label]
                    return pd.Series(0, index=dataframe.columns if not dataframe.empty else [])


                extracted_metrics = {
                    "Current_Assets": extract_financial_row(bs, ["Current Assets", "Total Current Assets"]),
                    "Current_Liabilities": extract_financial_row(bs,
                                                                 ["Current Liabilities", "Total Current Liabilities"]),
                    "Total_Debt": extract_financial_row(bs, ["Total Debt"]),
                    "Stockholders_Equity": extract_financial_row(bs,
                                                                 ["Stockholders Equity", "Total Stockholder Equity"]),
                    "Total_Revenue": extract_financial_row(is_stmt, ["Total Revenue"]),
                    "Operating_Income": extract_financial_row(is_stmt, ["Operating Income"]),
                    "Net_Income": extract_financial_row(is_stmt, ["Net Income"])
                }

                company_df = pd.DataFrame(extracted_metrics).fillna(0)
                processed_market_data[ticker] = company_df

            # --- PHASE 3: FINANCIAL MODELING ENGINE ---
            for ticker, df in processed_market_data.items():
                df['Current_Ratio'] = df['Current_Assets'] / df['Current_Liabilities']
                df['Debt_to_Equity'] = df['Total_Debt'] / df['Stockholders_Equity']
                df['Operating_Margin'] = df['Operating_Income'] / df['Total_Revenue']
                df['Return_on_Equity'] = df['Net_Income'] / df['Stockholders_Equity']

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                processed_market_data[ticker] = df.fillna(0)

            # --- PHASE 4: BENCHMARKING MATRIX ---
            benchmarking_rows = []
            for ticker, df in processed_market_data.items():
                df.sort_index(ascending=False, inplace=True)  # Lock descending order
                active_data = df[df['Total_Revenue'] > 0]

                if not active_data.empty:
                    latest_row = active_data.iloc[0].copy()
                    latest_row['Fiscal_Year'] = str(active_data.index[0])[:4]
                    latest_row['Company'] = ticker
                    benchmarking_rows.append(latest_row)

            competitive_matrix = pd.DataFrame(benchmarking_rows)
            competitive_matrix.set_index('Company', inplace=True)

            reporting_columns = ['Fiscal_Year', 'Current_Ratio', 'Debt_to_Equity', 'Operating_Margin',
                                 'Return_on_Equity']
            final_display_df = competitive_matrix[reporting_columns]

            # 4. Render User Interface Layout
            st.success("Analysis complete!")

            # Display Main Cross-Sectional Table
            st.subheader("📊 Cross-Sectional Competitive Matrix")
            st.dataframe(final_display_df.style.format({
                'Current_Ratio': '{:.2f}',
                'Debt_to_Equity': '{:.2f}',
                'Operating_Margin': '{:.2%}',  # Automatically format margins as percentages!
                'Return_on_Equity': '{:.2%}'
            }), use_container_width=True)
            # Add a professional financial glossary dropdown right below the data table
            with st.expander("Click here for the Financial Glossary"):
                st.markdown("""
                * **Current Ratio (Liquidity):** Measures the company's ability to cover its short-term obligations due within one year with its short-term assets. A ratio above 1.00 means the company is safely in the green.
                * **Debt-to-Equity (Leverage):** Shows how much of the company's capital structure is financed by debt versus investor cash. Lower numbers indicate a more financially stable, self-funded business.
                * **Operating Margin (Operational Profitability):** The percentage of revenue left over after paying for core operational costs (like R&D, marketing, and wages). It shows how efficient the core business model is before taxes and interest enter the picture.
                * **Return on Equity / ROE (Shareholder Efficiency):** Measures how effectively management is turning investor equity into net profits. It reveals exactly how many cents of profit are generated per dollar of shareholder wealth.
                """)

            # Interactive Chart Layout (Side by Side)
            st.subheader("📈 Visual Performance Analytics")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Operating Margin Comparison**")
                st.bar_chart(final_display_df['Operating_Margin'])

            with col2:
                st.markdown("**Return on Equity (ROE) Comparison**")
                st.bar_chart(final_display_df['Return_on_Equity'])
else:
    st.info("👈 Use the cosntroller on the left side to choose your peer group and click 'Execute Quantitative Model'.")