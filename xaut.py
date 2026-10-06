import requests
import pandas as pd
import streamlit as st


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="XAUT Put Analyzer",
    layout="wide"
)

st.title("XAUT Put Analyzer")
st.caption("Delta Exchange India")


# =========================================================
# FETCH DATA
# =========================================================

@st.cache_data(ttl=10)
def fetch_xaut_data():

    url = "https://api.india.delta.exchange/v2/tickers"

    headers = {
        "Accept": "application/json"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()["result"]

    return pd.json_normalize(data)


# =========================================================
# INPUTS
# =========================================================

col1, col2 = st.columns(2)

with col1:

    entry_price = st.number_input(
        "Entry",
        min_value=0.0,
        value=4196.0,
        step=1.0,
        format="%.2f"
    )

with col2:

    lot_size = st.number_input(
        "Lot Size",
        min_value=0.01,
        value=0.2,
        step=0.01,
        format="%.2f"
    )


# =========================================================
# FETCH BUTTON
# =========================================================

if st.button(
    "Fetch XAUT Put Options",
    type="primary"
):

    try:

        df = fetch_xaut_data()

        # -------------------------------------------------
        # XAUT ONLY
        # -------------------------------------------------

        df = df[
            df["underlying_asset_symbol"] == "XAUT"
        ].copy()

        # -------------------------------------------------
        # GET SPOT PRICE
        # -------------------------------------------------

        df["spot_price"] = pd.to_numeric(
            df["spot_price"],
            errors="coerce"
        )

        # Get current XAUT spot
        spot_price = df["spot_price"].dropna().iloc[0]

        # -------------------------------------------------
        # DISPLAY SPOT
        # -------------------------------------------------

        st.divider()

        spot_col1, spot_col2, spot_col3 = st.columns(3)

        with spot_col1:

            st.metric(
                label="XAUT Spot Price",
                value=f"${spot_price:,.2f}"
            )

        with spot_col2:

            st.metric(
                label="Your Entry",
                value=f"${entry_price:,.2f}"
            )

        with spot_col3:

            st.metric(
                label="Lot Size",
                value=f"{lot_size:g}"
            )

        # -------------------------------------------------
        # PUT OPTIONS ONLY
        # -------------------------------------------------

        df = df[
            df["contract_type"] == "put_options"
        ].copy()

        # -------------------------------------------------
        # NUMERIC CONVERSION
        # -------------------------------------------------

        df["strike_price"] = pd.to_numeric(
            df["strike_price"],
            errors="coerce"
        )

        df["quotes.best_bid"] = pd.to_numeric(
            df["quotes.best_bid"],
            errors="coerce"
        )

        # Remove invalid rows
        df = df[
            df["strike_price"].notna()
            & df["quotes.best_bid"].notna()
        ].copy()

        # -------------------------------------------------
        # EXPIRY DATE
        # -------------------------------------------------

        df["expiry_raw"] = df["symbol"].apply(
            lambda x: x.split("-")[-1]
        )

        df["Expiry"] = pd.to_datetime(
            df["expiry_raw"],
            format="%d%m%y",
            errors="coerce"
        ).dt.strftime("%d-%m-%Y")

        # =================================================
        # ITM / OTM BASED ON SPOT
        # =================================================

        # IMPORTANT:
        #
        # PUT:
        # ITM → Strike > Spot
        # OTM → Strike < Spot
        #
        # Entry is NOT used for classification.

        itm = df[
            df["strike_price"] > spot_price
        ].copy()

        otm = df[
            df["strike_price"] < spot_price
        ].copy()

        # =================================================
        # LTP
        # =================================================

        itm["LTP"] = itm["quotes.best_bid"]
        otm["LTP"] = otm["quotes.best_bid"]

        # =================================================
        # ITM PROFIT CALCULATION
        # =================================================

        # Premium profit
        itm["Profit from Premium"] = (
            itm["LTP"] * lot_size
        )

        # Assignment profit
        itm["Profit from Assignment"] = (
            (entry_price - itm["strike_price"])
            * lot_size
        )

        # Total profit
        itm["Total Profit"] = (
            itm["Profit from Premium"]
            + itm["Profit from Assignment"]
        )

        # =================================================
        # OTM PROFIT CALCULATION
        # =================================================

        # Premium profit
        otm["Profit from Premium"] = (
            otm["LTP"] * lot_size
        )

        # Assignment profit
        otm["Profit from Assignment"] = (
            (entry_price - otm["strike_price"])
            * lot_size
        )

        # Total profit
        otm["Total Profit"] = (
            otm["Profit from Premium"]
            + otm["Profit from Assignment"]
        )

        # =================================================
        # DISPLAY COLUMNS
        # =================================================

        display_columns = [
            "Expiry",
            "strike_price",
            "LTP",
            "Profit from Premium",
            "Profit from Assignment",
            "Total Profit"
        ]

        itm = itm[
            display_columns
        ].rename(
            columns={
                "strike_price": "Strike Price"
            }
        )

        otm = otm[
            display_columns
        ].rename(
            columns={
                "strike_price": "Strike Price"
            }
        )

        # =================================================
        # SORT
        # =================================================

        itm = itm.sort_values(
            ["Expiry", "Strike Price"]
        )

        otm = otm.sort_values(
            ["Expiry", "Strike Price"],
            ascending=[True, False]
        )

        # =================================================
        # RESULTS
        # =================================================

        st.divider()

#         st.subheader("ITM Put Options")
# 
#         st.dataframe(
#             itm,
#             use_container_width=True,
#             hide_index=True
#         )

        st.subheader("OTM Put Options")

        st.dataframe(
            otm,
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # REFRESH TIME
        # =================================================

        st.caption(
            "Last refreshed: "
            + pd.Timestamp.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

    except Exception as e:

        st.error(
            f"Error fetching data: {e}"
        )