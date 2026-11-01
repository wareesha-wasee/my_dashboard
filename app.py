import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sales Dashboard", layout="wide")

BLUE = "#2a6fdb"


if int(st.__version__.split(".")[1]) >= 50:
    FULL_WIDTH = {"width": "stretch"}
else:
    FULL_WIDTH = {"use_container_width": True}


def show(fig):
    st.plotly_chart(fig, **FULL_WIDTH)
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


@st.cache_data
def read_default_file():
    return pd.read_csv("Sales Data.csv")


@st.cache_data
def clean_data(raw):
    report = {}
    df = raw.drop(columns="Unnamed: 0", errors="ignore")
    report["Rows in the file"] = len(df)

    before = len(df)
    df = df.dropna()
    report["Empty rows removed"] = before - len(df)

    df["Order Date"] = pd.to_datetime(df["Order Date"])

    before = len(df)
    df = df.drop_duplicates()
    report["Duplicate rows removed"] = before - len(df)

    before = len(df)
    df = df[df["Order Date"].dt.year == 2019].copy()
    report["Rows outside 2019 removed"] = before - len(df)
    report["Rows used in the dashboard"] = len(df)

    df["Sales"] = df["Quantity Ordered"] * df["Price Each"]
    df["Month"] = df["Order Date"].dt.month_name()
    df["Hour"] = df["Order Date"].dt.hour
    parts = df["Purchase Address"].str.split(",")
    df["City"] = parts.str[1].str.strip() + " (" + parts.str[2].str.strip().str[:2] + ")"
    return df, report


# ---------- load the data ----------
st.title("Electronics Store Sales Dashboard, 2019")

uploaded = st.sidebar.file_uploader("Upload Sales Data.csv (optional)", type="csv")
try:
    raw = pd.read_csv(uploaded) if uploaded is not None else read_default_file()
except FileNotFoundError:
    st.error("Put `Sales Data.csv` in the same folder as app.py, or upload it in the sidebar.")
    st.stop()

df, report = clean_data(raw)

# ---------- filters ----------
st.sidebar.header("Filters")
all_cities = sorted(df["City"].unique())
all_products = sorted(df["Product"].unique())

months = st.sidebar.multiselect("Month", MONTHS, default=MONTHS)
cities = st.sidebar.multiselect("City", all_cities, default=all_cities)
products = st.sidebar.multiselect("Product", all_products, default=all_products)

filtered = df[df["Month"].isin(months) & df["City"].isin(cities) & df["Product"].isin(products)]
if filtered.empty:
    st.warning("No data for these filters. Select at least one month, city and product.")
    st.stop()

orders = filtered.groupby("Order ID")["Sales"].sum().reset_index()

tab_dashboard, tab_cleaning = st.tabs(["Dashboard", "Data cleaning"])

# ---------- dashboard tab ----------
with tab_dashboard:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total sales", f"${filtered['Sales'].sum():,.0f}")
    c2.metric("Orders", f"{filtered['Order ID'].nunique():,}")
    c3.metric("Items sold", f"{filtered['Quantity Ordered'].sum():,}")
    c4.metric("Average order", f"${orders['Sales'].mean():,.2f}")

    left, right = st.columns(2)

    with left:
        st.subheader("Q1. Which month had the best sales?")
        ordered_months = [m for m in MONTHS if m in months]
        monthly = filtered.groupby("Month")["Sales"].sum().reindex(ordered_months).reset_index()
        show(px.bar(monthly, x="Month", y="Sales", color_discrete_sequence=[BLUE]))
        best = monthly.loc[monthly["Sales"].idxmax()]
        st.caption(f"Best month: **{best['Month']}** (\\${best['Sales']:,.0f})")

    with right:
        st.subheader("Q2. Which city sells the most?")
        city_sales = filtered.groupby("City")["Sales"].sum().sort_values().reset_index()
        show(px.bar(city_sales, x="Sales", y="City", orientation="h", color_discrete_sequence=[BLUE]))
        best = city_sales.iloc[-1]
        st.caption(f"Best city: **{best['City']}** (\\${best['Sales']:,.0f})")

    left, right = st.columns(2)

    with left:
        st.subheader("Q3. At what time do customers buy?")
        hourly = filtered.groupby("Hour")["Sales"].sum().reset_index()
        show(px.line(hourly, x="Hour", y="Sales", markers=True, color_discrete_sequence=[BLUE]))
        best = hourly.loc[hourly["Sales"].idxmax()]
        st.caption(f"Busiest hour: **{int(best['Hour'])}:00**")

    with right:
        st.subheader("Q4. Which products make the most money?")
        product_sales = filtered.groupby("Product")["Sales"].sum().sort_values().reset_index()
        show(px.bar(product_sales, x="Sales", y="Product", orientation="h",
                               height=450, color_discrete_sequence=[BLUE]))
        best = product_sales.iloc[-1]
        st.caption(f"Top product: **{best['Product']}** (\\${best['Sales']:,.0f})")

    left, right = st.columns(2)

    with left:
        st.subheader("Q5. How much does a customer spend in one order?")
        show(px.histogram(orders, x="Sales", nbins=50, color_discrete_sequence=[BLUE]))
        st.caption(f"Typical order (median): **\\${orders['Sales'].median():,.2f}** | "
                   f"Average order (mean): **\\${orders['Sales'].mean():,.2f}**")

    with right:
        st.subheader("Most sold products (pieces)")
        sold = filtered.groupby("Product")["Quantity Ordered"].sum().sort_values(ascending=False).reset_index()
        st.dataframe(sold, hide_index=True)
        st.caption("Compare with Q4: the most sold products are cheap, the most profitable are expensive.")

# ---------- cleaning tab ----------
with tab_cleaning:
    st.subheader("What we did to the data")
    st.table(pd.DataFrame(list(report.items()), columns=["Step", "Rows"]).set_index("Step"))
    st.write("We dropped the extra `Unnamed: 0` column, empty rows, exact duplicate rows "
             "and orders from outside 2019. Then we made the columns `Sales`, `Month`, `Hour` and `City`.")

    st.subheader("Outliers")
    left, right = st.columns(2)
    with left:
        show(px.box(df, y="Sales", title="Sales per row", color_discrete_sequence=[BLUE]))
    with right:
        show(px.histogram(df, x="Quantity Ordered", title="Quantity ordered in one row",
                                     color_discrete_sequence=[BLUE]))
    st.write("The dots above the box are laptops, phones and monitors. They are real, because expensive "
             "products cost more, so we keep them. Large quantities (7 to 9) are only cheap batteries, "
             "so we keep those too.")

    st.subheader("Cleaned data (first 100 rows)")
    st.dataframe(df.head(100), hide_index=True)
