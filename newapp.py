import requests
import pandas as pd
import streamlit as st

st.title("ETH & BTC ATM Call Options - Delta Exchange")

# Separate spot inputs
eth_spot = st.number_input(
    "Enter your ETH purchased spot price (optional):",
    min_value=0.0,
    step=1.0,
    format="%.2f",
    key="eth_spot"
)

btc_spot = st.number_input(
    "Enter your BTC purchased spot price (optional):",
    min_value=0.0,
    step=1.0,
    format="%.2f",
    key="btc_spot"
)

# Fetch data ONLY ONCE
@st.cache_data(show_spinner=False)
def fetch_data():
    headers = {"Accept": "application/json"}
    r = requests.get("https://api.india.delta.exchange/v2/tickers", headers=headers)
    return r.json()["result"]

def process_asset(df, asset_symbol, user_spot):
    df_asset = df[df["underlying_asset_symbol"] == asset_symbol].copy()

    df_asset = df_asset[[
        "contract_type",
        "spot_price",
        "symbol",
        "strike_price",
        "greeks.theta",
        "quotes.best_bid",
        "quotes.bid_size"
    ]]

    df_asset["spot_price"] = pd.to_numeric(df_asset["spot_price"], errors="coerce")
    df_asset["strike_price"] = pd.to_numeric(df_asset["strike_price"], errors="coerce")

    # Override spot price if user provided one
    if user_spot > 0:
        df_asset["spot_price"] = user_spot

    # Call options only
    df_calls = df_asset[df_asset["contract_type"] == "call_options"].copy()
    df_calls["expiry"] = df_calls["symbol"].apply(lambda x: x.split("-")[-1])
    df_calls = df_calls.sort_values(["expiry", "strike_price"])

    # ATM / first OTM call
    df_calls["is_atm"] = df_calls["strike_price"] >= df_calls["spot_price"]
    df_atm = df_calls[
        df_calls["is_atm"] & df_calls["quotes.best_bid"].notnull()
    ]
    df_atm = df_atm.groupby("expiry", as_index=False).first()

    # Expiry & DTE
    df_atm["expiry_date"] = pd.to_datetime(df_atm["expiry"], format="%d%m%y")
    df_atm["expiry"] = df_atm["expiry_date"].dt.strftime("%d-%m-%Y")

    today = pd.Timestamp.today().normalize()
    df_atm["DTE"] = (df_atm["expiry_date"] - today).dt.days + 1

    # Numeric conversion & ROI
    cols = ["quotes.best_bid", "spot_price", "DTE"]
    df_atm[cols] = df_atm[cols].apply(pd.to_numeric, errors="coerce")

    df_atm["best_bid"] = df_atm["quotes.best_bid"]
    df_atm["ROI"] = (df_atm["best_bid"] / df_atm["spot_price"]) * 100
    df_atm["ROI_annual"] = (
        (df_atm["best_bid"] / df_atm["spot_price"])
        * (365 / df_atm["DTE"])
        * 100
    )

    return df_atm[[
        "spot_price",
        "strike_price",
        "best_bid",
        "quotes.bid_size",
        "expiry",
        "DTE",
        "ROI_annual",
        "ROI"
    ]]

# Button
if st.button("Fetch ETH & BTC Call Options"):
    data = fetch_data()
    df = pd.json_normalize(data)

    # ETH table
    st.subheader("ETH ATM Call Options")
    df_eth = process_asset(df, "ETH", eth_spot)
    st.dataframe(df_eth, use_container_width=True)

    # BTC table
    st.subheader("BTC ATM Call Options")
    df_btc = process_asset(df, "BTC", btc_spot)
    st.dataframe(df_btc, use_container_width=True)

    st.caption(
        f"Last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
