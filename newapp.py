import requests
import pandas as pd
import streamlit as st
import json

st.title("ETH ATM Call Options - Delta Exchange")

# Optional input for custom spot price
user_spot = st.number_input(
    "Enter your purchased spot price (optional):", 
    min_value=0.0, 
    step=1.0, 
    format="%.2f"
)

# Function to fetch data
def fetch_data():
    headers = {'Accept': 'application/json'}
    r = requests.get('https://api.india.delta.exchange/v2/tickers', headers=headers)
    # with open("data.json", "w") as f:
    #     json.dump(r.json(), f)
    return r.json()["result"]

# Button to fetch data
if st.button("Fetch ETH Call Options"):
    data = fetch_data()
    df = pd.json_normalize(data)
    df = df[df["underlying_asset_symbol"] == "ETH"]
    df = df[[
        'contract_type', 'spot_price', 'symbol', 'strike_price',
        'greeks.theta', 'quotes.best_bid',  'quotes.bid_size'
    ]]

    df['spot_price'] = pd.to_numeric(df['spot_price'], errors='coerce')
    df['strike_price'] = pd.to_numeric(df['strike_price'], errors='coerce')

    # Override spot price if user provided one
    if user_spot > 0:
        df['spot_price'] = user_spot

    # Filter call options
    df_calls = df[df['contract_type'] == 'call_options'].copy()
    df_calls['expiry'] = df_calls['symbol'].apply(lambda x: x.split('-')[-1])
    df_calls = df_calls.sort_values(['expiry', 'strike_price'])

    # First ATM/OTM call
    df_calls['is_atm'] = df_calls['strike_price'] >= df_calls['spot_price']
    df_atm_calls = df_calls[df_calls['is_atm'] & df_calls['quotes.best_bid'].notnull()]
    df_atm_calls = df_atm_calls.groupby('expiry', as_index=False).first()

    # Expiry date and DTE
    df_atm_calls['expiry_date'] = pd.to_datetime(df_atm_calls['expiry'], format='%d%m%y')
    df_atm_calls['expiry'] = df_atm_calls['expiry_date'].dt.strftime('%d-%m-%Y')
    # df_atm_calls['expiry_date'] = df_atm_calls['expiry_date'].dt.date

    today = pd.Timestamp.today().normalize()
    df_atm_calls['DTE'] = (df_atm_calls['expiry_date'] - today).dt.days
    df_atm_calls['DTE'] = df_atm_calls['DTE'] + 1

    # Numeric conversion & ROI
    # cols_to_numeric = ['quotes.best_bid', 'quotes.best_bid_mm', 'spot_price', 'DTE']
    cols_to_numeric = ['quotes.best_bid', 'spot_price', 'DTE']
    df_atm_calls[cols_to_numeric] = df_atm_calls[cols_to_numeric].apply(pd.to_numeric, errors='coerce')
    # df_atm_calls['best_bid'] = df_atm_calls[['quotes.best_bid', 'quotes.best_bid_mm']].min(axis=1)
    df_atm_calls['best_bid'] = df_atm_calls['quotes.best_bid']

    df_atm_calls['ROI'] = (df_atm_calls['best_bid'] / df_atm_calls['spot_price']) * 100
    df_atm_calls['ROI_annual'] = (df_atm_calls['best_bid'] / df_atm_calls['spot_price']) * (365 / df_atm_calls['DTE']) * 100

    df_atm_calls = df_atm_calls[[
        'spot_price', 'strike_price','best_bid',  'quotes.bid_size',
        # 'expiry_date', 'DTE','ROI_annual', 'ROI'
        'expiry', 'DTE','ROI_annual', 'ROI'
    ]]

    # Display table directly
    st.write(f"Last refreshed: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.dataframe(df_atm_calls, use_container_width=True)
