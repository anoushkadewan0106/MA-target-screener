import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="M&A Target Screener", layout="wide")

st.title("📊 Tech Hardware M&A Target Screener")
st.markdown("Automated screening pipeline for identifying undervalued acquisition targets.")

# 1. Target Universe: Mid-Cap & Large Tech Hardware / Semiconductor Tickers
DEFAULT_TICKERS = [
    "WDC", "STX", "HPQ", "NTAP", "PSTG", "CIEN", "FFIV", "SANM", 
    "JNPR", "SMCI", "SWKS", "QRVO", "CRUS", "COHR", "LITE"
]

@st.cache_data(ttl=3600)
def fetch_financial_data(tickers):
    data = []
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # Extract Key Metrics
            name = info.get("shortName", ticker)
            market_cap = info.get("marketCap", None)
            total_debt = info.get("totalDebt", 0)
            total_cash = info.get("totalCash", 0)
            ebitda = info.get("ebitda", None)
            revenue = info.get("totalRevenue", None)
            pe_ratio = info.get("trailingPE", None)
            
            if market_cap and ebitda and ebitda > 0:
                # Core IB Valuation Mechanics
                net_debt = total_debt - total_cash
                enterprise_value = market_cap + net_debt
                ev_ebitda = enterprise_value / ebitda
                leverage_ratio = net_debt / ebitda
                ebitda_margin = (ebitda / revenue) * 100 if revenue else None
                
                data.append({
                    "Ticker": ticker,
                    "Company": name,
                    "Market Cap ($B)": round(market_cap / 1e9, 2),
                    "Enterprise Value ($B)": round(enterprise_value / 1e9, 2),
                    "EBITDA ($M)": round(ebitda / 1e6, 2),
                    "EV / EBITDA": round(ev_ebitda, 2),
                    "Net Debt / EBITDA": round(leverage_ratio, 2),
                    "EBITDA Margin (%)": round(ebitda_margin, 2) if ebitda_margin else None,
                    "P/E Ratio": round(pe_ratio, 2) if pe_ratio else None
                })
        except Exception as e:
            continue
            
    return pd.DataFrame(data)

# Load Data
with st.spinner("Fetching live financial data via Yahoo Finance API..."):
    df = fetch_financial_data(DEFAULT_TICKERS)

if not df.empty:
    # 2. Sidebar Filters
    st.sidebar.header("Screening Criteria")
    max_ev_ebitda = st.sidebar.slider("Max EV / EBITDA Multiple", 5.0, 25.0, 12.0, 0.5)
    max_leverage = st.sidebar.slider("Max Net Debt / EBITDA", -2.0, 5.0, 1.5, 0.5)
    min_margin = st.sidebar.slider("Min EBITDA Margin (%)", 0.0, 40.0, 12.0, 1.0)

    # 3. Apply M&A Target Logic
    filtered_df = df[
        (df["EV / EBITDA"] <= max_ev_ebitda) &
        (df["Net Debt / EBITDA"] <= max_leverage) &
        (df["EBITDA Margin (%)"] >= min_margin)
    ].sort_values(by="EV / EBITDA", ascending=True)

    # Top Metrics Summary
    col1, col2, col3 = st.columns(3)
    col1.metric("Companies Analyzed", len(df))
    col2.metric("Targets Flagged", len(filtered_df))
    col3.metric("Peer Avg EV/EBITDA", f"{df['EV / EBITDA'].mean():.2f}x")

    st.markdown("---")

    # 4. Target Highlights (Top 3)
    st.subheader("🎯 Primary Acquisition Candidates")
    top_3 = filtered_df.head(3)
    
    if len(top_3) > 0:
        cols = st.columns(len(top_3))
        for idx, (_, row) in enumerate(top_3.iterrows()):
            with cols[idx]:
                st.info(f"**{row['Ticker']}** - {row['Company']}")
                st.write(f"• **EV / EBITDA:** {row['EV / EBITDA']}x")
                st.write(f"• **Net Debt / EBITDA:** {row['Net Debt / EBITDA']}x")
                st.write(f"• **EBITDA Margin:** {row['EBITDA Margin (%)']}%")
                st.write(f"• **Market Cap:** ${row['Market Cap ($B)']}B")
    else:
        st.warning("No targets match the current criteria. Try loosening the filters.")

    # 5. Visual Valuation Matrix
    st.subheader("📈 Valuation vs Profitability Matrix")
    fig = px.scatter(
        df,
        x="EV / EBITDA",
        y="EBITDA Margin (%)",
        size="Market Cap ($B)",
        color="Ticker",
        hover_name="Company",
        title="EV/EBITDA vs EBITDA Margin (Bottom-Right = Undervalued & Highly Profitability)",
        labels={"EV / EBITDA": "EV / EBITDA (Lower = Cheaper)", "EBITDA Margin (%)": "EBITDA Margin % (Higher = Better)"}
    )
    st.plotly_chart(fig, use_container_width=True)

    # 6. Complete Data Table
    st.subheader("📋 Full Universe Peer Dataset")
    st.dataframe(df, use_container_width=True)

else:
    st.error("Could not load financial data.")
