"""
Corporate Competitor Benchmarking Terminal
===========================================

A Streamlit dashboard that pulls live financial statements via yfinance,
computes a standard set of liquidity, leverage, and profitability ratios,
and renders a cross-sectional comparison across a user-defined cohort of
companies.

Run with:
    streamlit run benchmarking_dashboard.py
"""

import html
import re

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ---------------------------------------------------------------------------
# Constants and configuration
# ---------------------------------------------------------------------------

DEFAULT_TICKERS = "AAPL, MSFT, GOOGL, NVDA"

# Candidate row labels for each financial statement line item we need, listed
# in priority order. yfinance's standardized labels can vary slightly by
# company and filing type, so each item has at least one fallback.
ROW_NAME_CANDIDATES = {
    "current_assets": ["Current Assets", "Total Current Assets"],
    "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
    "total_debt": ["Total Debt", "Net Debt"],
    "stockholders_equity": [
        "Stockholders Equity",
        "Common Stock Equity",
        "Total Equity Gross Minority Interest",
    ],
    "total_assets": ["Total Assets"],
    "total_revenue": ["Total Revenue", "Operating Revenue"],
    "operating_income": ["Operating Income", "Total Operating Income As Reported"],
    "net_income": [
        "Net Income",
        "Net Income Common Stockholders",
        "Net Income Continuous Operations",
    ],
}

RATIO_FORMAT_COLUMNS = ["Current Ratio", "Debt-to-Equity", "Debt-to-Assets", "Asset Turnover"]
PERCENT_FORMAT_COLUMNS = ["Operating Margin", "Net Profit Margin", "Return on Equity"]

DISPLAY_COLUMNS = [
    "Company",
    "Fiscal Year End",
    "Current Ratio",
    "Debt-to-Equity",
    "Debt-to-Assets",
    "Operating Margin",
    "Net Profit Margin",
    "Return on Equity",
    "Asset Turnover",
]

GLOSSARY_ENTRIES = [
    (
        "Current Ratio",
        "Liquidity",
        "Current Assets &divide; Current Liabilities",
        "Measures whether a company holds enough short-term assets to cover "
        "obligations coming due within a year. A reading above 1.00x generally "
        "signals adequate short-term liquidity, while a reading below 1.00x can "
        "flag near-term solvency stress. Unusually high values can also suggest "
        "idle cash or inventory that isn't being deployed efficiently.",
    ),
    (
        "Debt-to-Equity",
        "Leverage",
        "Total Debt &divide; Stockholders Equity",
        "Shows how much of the company's financing comes from debt relative to "
        "shareholder capital. Higher values mean more financial leverage and "
        "more risk in a downturn, but leverage can also amplify returns when "
        "borrowed capital is deployed productively. Healthy levels vary widely "
        "by industry, capital-intensive sectors like utilities typically run "
        "far higher than asset-light software businesses.",
    ),
    (
        "Debt-to-Assets",
        "Leverage",
        "Total Debt &divide; Total Assets",
        "Shows the share of a company's total asset base financed by debt "
        "rather than equity. It complements Debt-to-Equity and is less "
        "sensitive to swings in the equity balance from buybacks or losses. "
        "Values near 0 indicate a conservative balance sheet, while values "
        "approaching 1.00 indicate heavy reliance on borrowed capital.",
    ),
    (
        "Operating Margin",
        "Profitability",
        "Operating Income &divide; Total Revenue",
        "Measures core operating efficiency before interest and taxes. "
        "Because it excludes financing costs and tax jurisdiction effects, "
        "it isolates how much profit the underlying business generates per "
        "dollar of sales, making it one of the cleanest ways to compare "
        "operating performance across companies with different capital "
        "structures.",
    ),
    (
        "Net Profit Margin",
        "Profitability",
        "Net Income &divide; Total Revenue",
        "The bottom-line share of revenue that survives as profit after "
        "every expense, interest payment, and tax. It is useful for judging "
        "overall profitability, but it can be distorted by one-off items, "
        "tax effects, or financing decisions that have nothing to do with "
        "core operating performance.",
    ),
    (
        "Return on Equity",
        "Profitability",
        "Net Income &divide; Stockholders Equity",
        "Measures how efficiently a company turns shareholders' invested "
        "capital into profit, a core metric for equity investors. Because "
        "equity sits in the denominator, high leverage can mechanically "
        "inflate this ratio even without any real operating improvement, so "
        "it is worth reading alongside Debt-to-Equity rather than in "
        "isolation.",
    ),
    (
        "Asset Turnover",
        "Efficiency",
        "Total Revenue &divide; Total Assets",
        "Measures how efficiently a company converts its asset base into "
        "sales. Capital-light businesses such as retail or services "
        "typically post much higher turnover than capital-intensive ones "
        "such as utilities or manufacturing, so this metric is most "
        "meaningful when compared within the same industry rather than "
        "across very different business models.",
    ),
]

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
    --bg-primary: #0A0E17;
    --bg-secondary: #11182B;
    --bg-elevated: #1A2238;
    --border-subtle: #232B45;
    --text-primary: #E7EAF2;
    --text-secondary: #8B95AC;
    --accent-gradient: linear-gradient(135deg, #6366F1 0%, #14B8A6 100%);
}

.stApp {
    background-color: var(--bg-primary);
    font-family: 'Inter', sans-serif;
    color: var(--text-primary);
}

[data-testid="stHeader"] {
    background-color: transparent;
}

[data-testid="stSidebar"] {
    background-color: var(--bg-secondary);
    border-right: 1px solid var(--border-subtle);
}

.app-header {
    padding: 0.5rem 0 1.5rem 0;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 1.5rem;
}

.app-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
    line-height: 1.15;
}

.app-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
}

.sidebar-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.75rem;
}

.sidebar-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    margin: 1.1rem 0 0.4rem 0;
}

.section-header {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 1.25rem 0 0.75rem 0;
}

.kpi-card {
    position: relative;
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 1.3rem 1.2rem 1.1rem 1.2rem;
    height: 100%;
    overflow: hidden;
}

.kpi-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--accent-gradient);
}

.kpi-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-secondary);
    margin-bottom: 0.4rem;
}

.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 600;
    background: var(--accent-gradient);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
    line-height: 1.1;
}

.kpi-subtext {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: var(--text-secondary);
    margin-top: 0.35rem;
}

[data-testid="stButton"] button {
    background: var(--accent-gradient);
    color: #0A0E17;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    border: none;
    border-radius: 8px;
}

[data-testid="stButton"] button p {
    color: #0A0E17;
    font-weight: 600;
}

[data-testid="stButton"] button:hover {
    opacity: 0.88;
}

[data-testid="stDownloadButton"] button {
    background-color: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
}

[data-testid="stExpander"] {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
}

[data-baseweb="tab-highlight"] {
    background: var(--accent-gradient) !important;
}

[data-testid="stDataFrame"] {
    font-family: 'JetBrains Mono', monospace;
}
</style>
"""


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def sanitize_ticker(raw_symbol):
    """
    Strip a user-entered ticker down to a safe character set (letters,
    digits, dots, and hyphens, e.g. 'BRK.B') and enforce a sane length cap.
    Returns None if nothing valid remains after cleaning.
    """
    if not isinstance(raw_symbol, str):
        return None

    cleaned = re.sub(r"[^A-Za-z0-9.\-]", "", raw_symbol).upper().strip()

    if not cleaned or len(cleaned) > 10:
        return None

    return cleaned


def parse_cohort_tickers(raw_text):
    """
    Convert the free-text, comma-separated sidebar input into a clean,
    de-duplicated list of sanitized ticker symbols. Invalid entries are
    silently dropped instead of being allowed to crash the pipeline.
    """
    raw_entries = raw_text.split(",")
    unique_tickers = []

    for entry in raw_entries:
        cleaned = sanitize_ticker(entry)
        if cleaned and cleaned not in unique_tickers:
            unique_tickers.append(cleaned)

    return unique_tickers


def safe_divide(numerator, denominator):
    """
    Perform numerator / denominator while neutralizing the failure modes
    common in scraped financial data: a zero or missing denominator, or a
    result that resolves to NaN or infinity. Returns 0.0 instead of raising
    or letting a non-finite value leak into the comparison matrix.
    """
    try:
        if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
            return 0.0
        result = numerator / denominator
    except (TypeError, ZeroDivisionError):
        return 0.0

    if not np.isfinite(result):
        return 0.0

    return float(result)


def find_financial_row(statement_df, possible_row_names):
    """
    Search the row index of a financial statement DataFrame for the first
    label that matches, case-insensitively, any of the candidate names.
    Tries an exact match first, then falls back to a substring match. If
    nothing matches, returns a row of zeros so downstream math never fails
    on a missing line item.
    """
    normalized_index = {str(label).lower(): label for label in statement_df.index}

    for candidate in possible_row_names:
        candidate_lower = candidate.lower()

        if candidate_lower in normalized_index:
            return statement_df.loc[normalized_index[candidate_lower]]

        for lower_label, original_label in normalized_index.items():
            if candidate_lower in lower_label:
                return statement_df.loc[original_label]

    return pd.Series(0.0, index=statement_df.columns)


def format_ratio(value):
    """Render a ratio-style metric as a two-decimal multiple, e.g. '1.45x'."""
    return f"{value:.2f}x"


def format_percent(value):
    """Render a margin-style metric as a two-decimal percentage, e.g. '24.52%'."""
    return f"{value * 100:.2f}%"


FORMAT_MAP = {column: format_ratio for column in RATIO_FORMAT_COLUMNS}
FORMAT_MAP.update({column: format_percent for column in PERCENT_FORMAT_COLUMNS})


# ---------------------------------------------------------------------------
# Data acquisition layer (cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def search_company_tickers(company_name):
    """
    Query Yahoo Finance's search engine for tickers matching a free-text
    company name. Returns (candidates, error_message). candidates is a list
    of up to three dicts with 'symbol' and 'name' keys, restricted to equity
    listings. error_message is None on success, or a short string describing
    a hard failure (e.g. a network problem) so the caller can distinguish
    "search failed" from "search succeeded but found nothing".
    """
    try:
        raw_results = yf.Search(company_name, max_results=8).quotes
    except Exception as exc:
        return [], str(exc)

    candidates = []
    for item in raw_results:
        if item.get("quoteType") != "EQUITY":
            continue

        symbol = item.get("symbol")
        if not symbol:
            continue

        display_name = (
            item.get("shortname")
            or item.get("longname")
            or item.get("shortName")
            or item.get("longName")
            or symbol
        )
        candidates.append({"symbol": symbol, "name": display_name})

        if len(candidates) >= 3:
            break

    return candidates, None


@st.cache_data(ttl=3600, show_spinner=False)
def get_company_name(ticker_symbol):
    """
    Fetch a clean display name for a ticker (e.g. 'Apple Inc.' instead of
    'AAPL'). Falls back to the raw ticker symbol if Yahoo doesn't return one.
    """
    try:
        info = yf.Ticker(ticker_symbol).info
        return info.get("shortName") or info.get("longName") or ticker_symbol
    except Exception:
        return ticker_symbol


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_financials(ticker_symbol):
    """
    Pull the annual balance sheet and income statement for one ticker.
    Returns (None, None) if the ticker is invalid, unreachable, or Yahoo
    has no statement data on file for it, so callers can skip it cleanly.
    """
    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        balance_sheet = ticker_obj.balance_sheet
        income_statement = ticker_obj.income_stmt
    except Exception:
        return None, None

    if balance_sheet is None or balance_sheet.empty:
        return None, None
    if income_statement is None or income_statement.empty:
        return None, None

    return balance_sheet, income_statement


# ---------------------------------------------------------------------------
# Financial modeling layer
# ---------------------------------------------------------------------------

def compute_latest_metrics(ticker_symbol):
    """
    Pull the financial statements for one ticker, isolate the most recent
    fiscal year column in each statement, and return a dict containing the
    seven benchmarking ratios plus metadata. Returns None if the ticker has
    no usable statement data.
    """
    balance_sheet, income_statement = fetch_company_financials(ticker_symbol)
    if balance_sheet is None or income_statement is None:
        return None

    latest_bs_date = max(balance_sheet.columns)
    latest_is_date = max(income_statement.columns)

    current_assets = find_financial_row(
        balance_sheet, ROW_NAME_CANDIDATES["current_assets"]
    )[latest_bs_date]
    current_liabilities = find_financial_row(
        balance_sheet, ROW_NAME_CANDIDATES["current_liabilities"]
    )[latest_bs_date]
    total_debt = find_financial_row(
        balance_sheet, ROW_NAME_CANDIDATES["total_debt"]
    )[latest_bs_date]
    equity = find_financial_row(
        balance_sheet, ROW_NAME_CANDIDATES["stockholders_equity"]
    )[latest_bs_date]
    total_assets = find_financial_row(
        balance_sheet, ROW_NAME_CANDIDATES["total_assets"]
    )[latest_bs_date]

    total_revenue = find_financial_row(
        income_statement, ROW_NAME_CANDIDATES["total_revenue"]
    )[latest_is_date]
    operating_income = find_financial_row(
        income_statement, ROW_NAME_CANDIDATES["operating_income"]
    )[latest_is_date]
    net_income = find_financial_row(
        income_statement, ROW_NAME_CANDIDATES["net_income"]
    )[latest_is_date]

    if hasattr(latest_bs_date, "strftime"):
        fiscal_year_end = latest_bs_date.strftime("%Y-%m-%d")
    else:
        fiscal_year_end = str(latest_bs_date)

    return {
        "Ticker": ticker_symbol,
        "Fiscal Year End": fiscal_year_end,
        "Current Ratio": safe_divide(current_assets, current_liabilities),
        "Debt-to-Equity": safe_divide(total_debt, equity),
        "Debt-to-Assets": safe_divide(total_debt, total_assets),
        "Operating Margin": safe_divide(operating_income, total_revenue),
        "Net Profit Margin": safe_divide(net_income, total_revenue),
        "Return on Equity": safe_divide(net_income, equity),
        "Asset Turnover": safe_divide(total_revenue, total_assets),
    }


@st.cache_data(ttl=3600, show_spinner="Pulling live statements and computing ratios...")
def build_benchmark_matrix(ticker_tuple):
    """
    Run the full extraction-and-ratio pipeline for every ticker in the
    cohort and assemble the results into a single comparison DataFrame
    indexed by ticker. Tickers that fail to return usable data are skipped
    and returned separately so the UI can flag them without crashing.
    """
    rows = []
    failed_tickers = []

    for symbol in ticker_tuple:
        metrics = compute_latest_metrics(symbol)
        if metrics is None:
            failed_tickers.append(symbol)
            continue
        metrics["Company"] = get_company_name(symbol)
        rows.append(metrics)

    if not rows:
        return pd.DataFrame(), failed_tickers

    matrix = pd.DataFrame(rows).set_index("Ticker")

    ratio_columns = RATIO_FORMAT_COLUMNS + PERCENT_FORMAT_COLUMNS
    matrix[ratio_columns] = matrix[ratio_columns].replace([np.inf, -np.inf], np.nan)
    matrix[ratio_columns] = matrix[ratio_columns].fillna(0.0)

    return matrix, failed_tickers


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def render_section_header(text):
    """Render a styled section header using the app's gradient typography."""
    st.markdown(
        f'<div class="section-header">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def inject_custom_css():
    """Inject the dashboard's dark slate / gradient fintech theme."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header():
    """Render the top-of-page gradient title and subtitle."""
    st.markdown(
        """
        <div class="app-header">
            <div class="app-title">Corporate Competitor Benchmarking Terminal</div>
            <div class="app-subtitle">
                Live cross-sectional financial diagnostics, sourced directly from Yahoo Finance
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _add_ticker_to_cohort(new_symbol):
    """
    Callback for the sidebar 'Add to cohort' button. Appends the resolved
    ticker symbol to the persistent text-area state if it is not already
    present. Runs before the script reruns, so the text area picks up the
    change cleanly on the next render.
    """
    cleaned_symbol = sanitize_ticker(new_symbol)
    if cleaned_symbol is None:
        return

    current_tickers = parse_cohort_tickers(st.session_state.cohort_tickers_raw)
    if cleaned_symbol not in current_tickers:
        current_tickers.append(cleaned_symbol)

    st.session_state.cohort_tickers_raw = ", ".join(current_tickers)


def render_sidebar():
    """
    Render the full sidebar: the persistent editable cohort list, the
    name-based ticker search engine, and the run trigger. Returns the
    resolved list of sanitized cohort tickers and whether the run button
    was clicked on this script execution.
    """
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Cohort Configuration</div>', unsafe_allow_html=True)

        if "cohort_tickers_raw" not in st.session_state:
            st.session_state.cohort_tickers_raw = DEFAULT_TICKERS

        st.text_area(
            "Active cohort (comma-separated tickers)",
            key="cohort_tickers_raw",
            height=80,
            help="Edit this list directly, or use the search box below to look up a company by name.",
        )

        st.markdown('<div class="sidebar-subtitle">Find a company by name</div>', unsafe_allow_html=True)
        search_query = st.text_input(
            "Company name",
            key="company_search_query",
            placeholder="e.g. Apple, Tesla, Nvidia",
            label_visibility="collapsed",
        )

        if search_query:
            candidates, search_error = search_company_tickers(search_query)

            if search_error is not None:
                st.error(f"Search engine unavailable right now: {search_error}")
            elif not candidates:
                st.warning(
                    f'No matching companies found for "{search_query}". '
                    "Try a shorter or more common name."
                )
            else:
                option_labels = [
                    f"{candidate['name']} ({candidate['symbol']})" for candidate in candidates
                ]
                selected_label = st.selectbox(
                    "Matching companies", option_labels, key="search_result_choice"
                )
                selected_symbol = candidates[option_labels.index(selected_label)]["symbol"]
                st.button(
                    f"Add {selected_symbol} to cohort",
                    key="add_ticker_button",
                    on_click=_add_ticker_to_cohort,
                    args=(selected_symbol,),
                    width="stretch",
                )

        st.divider()
        run_clicked = st.button(
            "Run Benchmark", key="run_benchmark_button", type="primary", width="stretch"
        )
        st.caption(
            "Results are cached for one hour per ticker to keep the app fast and to "
            "avoid overloading Yahoo Finance's free data feed."
        )

        cohort_tickers = parse_cohort_tickers(st.session_state.cohort_tickers_raw)

    return cohort_tickers, run_clicked


def render_kpi_leaderboard(matrix):
    """Render the three standout-leader KPI cards above the main matrix."""
    leaderboard_specs = [
        ("Highest Operating Margin", "Operating Margin", "percent"),
        ("Top Return on Equity", "Return on Equity", "percent"),
        ("Best Asset Velocity", "Asset Turnover", "ratio"),
    ]

    kpi_columns = st.columns(len(leaderboard_specs))

    for kpi_column, (title, metric_column, value_kind) in zip(kpi_columns, leaderboard_specs):
        leader_ticker = matrix[metric_column].idxmax()
        leader_value = matrix.loc[leader_ticker, metric_column]
        leader_company = matrix.loc[leader_ticker, "Company"]

        if value_kind == "percent":
            display_value = format_percent(leader_value)
        else:
            display_value = format_ratio(leader_value)

        safe_title = html.escape(title)
        safe_value = html.escape(display_value)
        safe_company = html.escape(str(leader_company))
        safe_ticker = html.escape(str(leader_ticker))

        with kpi_column:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">{safe_title}</div>
                    <div class="kpi-value">{safe_value}</div>
                    <div class="kpi-subtext">{safe_company} ({safe_ticker})</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_executive_tab(matrix, failed_tickers, has_run):
    """Render the Executive Cross-Sectional Matrix tab."""
    if not has_run:
        st.info("Configure your cohort in the sidebar and click **Run Benchmark** to populate the matrix.")
        return

    if matrix.empty:
        st.error(
            "None of the tickers in the current cohort returned usable financial data. "
            "Double-check the symbols and try again."
        )
        return

    if failed_tickers:
        readable_failed = ", ".join(failed_tickers)
        st.warning(f"Skipped {len(failed_tickers)} ticker(s) with no usable data: {readable_failed}")

    render_kpi_leaderboard(matrix)
    render_section_header("Cross-Sectional Ratio Matrix")

    styled_matrix = matrix[DISPLAY_COLUMNS].style.format(FORMAT_MAP)
    st.dataframe(styled_matrix, width="stretch")

    csv_bytes = matrix[DISPLAY_COLUMNS].to_csv().encode("utf-8")
    st.download_button(
        label="Download benchmark matrix as CSV",
        data=csv_bytes,
        file_name="corporate_benchmark_matrix.csv",
        mime="text/csv",
        width="stretch",
    )


def render_charts_tab(matrix, has_run):
    """Render the Advanced Performance Charts tab."""
    if not has_run or matrix.empty:
        st.info("Run the benchmark from the sidebar to generate comparison charts.")
        return

    profitability_data = matrix[["Operating Margin", "Net Profit Margin", "Return on Equity"]] * 100
    profitability_data.columns = [
        "Operating Margin (%)",
        "Net Profit Margin (%)",
        "Return on Equity (%)",
    ]

    leverage_data = matrix[["Current Ratio", "Debt-to-Equity", "Debt-to-Assets"]]

    chart_left, chart_right = st.columns(2)

    with chart_left:
        render_section_header("Profitability Components")
        st.bar_chart(profitability_data, width="stretch")

    with chart_right:
        render_section_header("Leverage Boundaries")
        st.bar_chart(leverage_data, width="stretch")


def render_glossary_tab():
    """Render the Institutional Diagnostic Glossary tab."""
    render_section_header("Institutional Diagnostic Glossary")

    for metric_name, category, formula, explanation in GLOSSARY_ENTRIES:
        with st.expander(f"{metric_name}  \u00b7  {category}"):
            st.markdown(f"**Formula:** {formula}", unsafe_allow_html=True)
            st.write(explanation)


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Corporate Competitor Benchmarking Terminal",
        page_icon="\U0001F4CA",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_custom_css()
    render_header()

    cohort_tickers, run_clicked = render_sidebar()

    if "has_run" not in st.session_state:
        st.session_state.has_run = False
    if run_clicked:
        st.session_state.has_run = True

    matrix = pd.DataFrame()
    failed_tickers = []

    if st.session_state.has_run and cohort_tickers:
        matrix, failed_tickers = build_benchmark_matrix(tuple(sorted(cohort_tickers)))

    tab_matrix, tab_charts, tab_glossary = st.tabs(
        [
            "Executive Cross-Sectional Matrix",
            "Advanced Performance Charts",
            "Institutional Diagnostic Glossary",
        ]
    )

    with tab_matrix:
        render_executive_tab(matrix, failed_tickers, st.session_state.has_run)

    with tab_charts:
        render_charts_tab(matrix, st.session_state.has_run)

    with tab_glossary:
        render_glossary_tab()

    st.sidebar.caption(
        "For educational and informational purposes only, not investment advice. "
        "Data sourced from Yahoo Finance via yfinance."
    )


if __name__ == "__main__":
    main()