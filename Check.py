# Import yfinance to manage API connections to Yahoo Finance data
import yfinance as yf

# Set our target company ticker to Apple
ticker_symbol = "AAPL"

# Create a Ticker object which serves as our data extraction pipeline
target_company = yf.Ticker(ticker_symbol)

# Pull the primary balance sheet DataFrame from the API
raw_balance_sheet = target_company.balance_sheet

# Output the top 5 rows to the PyCharm run console to confirm connection
print(f"--- Raw Balance Sheet for {ticker_symbol} ---")
print(raw_balance_sheet.head())