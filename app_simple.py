import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sales Dashboard", layout="wide")
st.title("Electronics Store Sales Dashboard, 2019")

BLUE = "#2a6fdb"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# ---------------------------------------------------------------
# 1. Load the data
# ---------------------------------------------------------------
uploaded = st.sidebar.file_uploader("Upload Sales Data.csv (optional)", type="csv")

try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
    else:
        raw = pd.read_csv("Sales Data.csv")
except FileNotFoundError:
    st.error("Put Sales Data.csv in the same folder as this file, or upload it in the sidebar.")
    st.stop()

# ---------------------------------------------------------------
# 2. Clean the data
# ---------------------------------------------------------------
df = raw.drop(columns="Unnamed: 0", errors="ignore")
rows_in_file = len(df)

# empty rows
df = df.dropna()
empty_removed = rows_in_file - len(df)

# date column
df["Order Date"] = pd.to_datetime(df["Order Date"])

# duplicate rows
rows_before = len(df)
df = df.drop_duplicates()
duplicates_removed = rows_before - len(df)

# rows outside 2019
rows_before = len(df)
df = df[df["Order Date"].dt.year == 2019].copy()
outside_2019_removed = rows_before - len(df)

# new columns
df["Sales"] = df["Quantity Ordered"] * df["Price Each"]
df["Month"] = df["Order Date"].dt.month_name()
df["Hour"] = df["Order Date"].dt.hour

parts = df["Purchase Address"].str.split(",")
df["City"] = parts.str[1].str.strip() + " (" + parts.str[2].str.strip().str[:2] + ")"

# ---------------------------------------------------------------
# 3. Filters in the sidebar
# ---------------------------------------------------------------
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

# one row per order
orders = filtered.groupby("Order ID")["Sales"].sum().reset_index()

# ---------------------------------------------------------------
# 4. Page layout: two tabs
# ---------------------------------------------------------------
tab_dashboard, tab_cleaning = st.tabs(["Dashboard", "Data cleaning"])

with tab_dashboard:

    # number tiles
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total sales", "$" + format(filtered["Sales"].sum(), ",.0f"))
    c2.metric("Orders", format(filtered["Order ID"].nunique(), ","))
    c3.metric("Items sold", format(filtered["Quantity Ordered"].sum(), ","))
    c4.metric("Average order", "$" + format(orders["Sales"].mean(), ",.2f"))

    left, right = st.columns(2)

    # Q1: best month
    with left:
        st.subheader("Q1. Which month had the best sales?")
        months_in_order = [m for m in MONTHS if m in months]
        monthly = filtered.groupby("Month")["Sales"].sum().reindex(months_in_order).reset_index()
        fig = px.bar(monthly, x="Month", y="Sales", color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
        best = monthly.loc[monthly["Sales"].idxmax()]
        st.caption("Best month: " + best["Month"] + " (USD " + format(best["Sales"], ",.0f") + ")")

    # Q2: best city
    with right:
        st.subheader("Q2. Which city sells the most?")
        city_sales = filtered.groupby("City")["Sales"].sum().sort_values().reset_index()
        fig = px.bar(city_sales, x="Sales", y="City", orientation="h", color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
        best = city_sales.iloc[-1]
        st.caption("Best city: " + best["City"] + " (USD " + format(best["Sales"], ",.0f") + ")")

    left, right = st.columns(2)

    # Q3: best hour
    with left:
        st.subheader("Q3. At what time do customers buy?")
        hourly = filtered.groupby("Hour")["Sales"].sum().reset_index()
        fig = px.line(hourly, x="Hour", y="Sales", markers=True, color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
        best = hourly.loc[hourly["Sales"].idxmax()]
        st.caption("Busiest hour: " + str(int(best["Hour"])) + ":00")

    # Q4: best products
    with right:
        st.subheader("Q4. Which products make the most money?")
        product_sales = filtered.groupby("Product")["Sales"].sum().sort_values().reset_index()
        fig = px.bar(product_sales, x="Sales", y="Product", orientation="h", height=450,
                     color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
        best = product_sales.iloc[-1]
        st.caption("Top product: " + best["Product"] + " (USD " + format(best["Sales"], ",.0f") + ")")

    left, right = st.columns(2)

    # Q5: spend per order
    with left:
        st.subheader("Q5. How much does a customer spend in one order?")
        fig = px.histogram(orders, x="Sales", nbins=50, color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Typical order (median): USD " + format(orders["Sales"].median(), ",.2f")
                   + " | Average order (mean): USD " + format(orders["Sales"].mean(), ",.2f"))

    # most sold products
    with right:
        st.subheader("Most sold products (pieces)")
        sold = filtered.groupby("Product")["Quantity Ordered"].sum().sort_values(ascending=False).reset_index()
        st.dataframe(sold, hide_index=True)
        st.caption("Compare with Q4: the most sold products are cheap, the most profitable are expensive.")

with tab_cleaning:
    st.subheader("What we did to the data")
    steps = pd.DataFrame({
        "Step": ["Rows in the file", "Empty rows removed", "Duplicate rows removed",
                 "Rows outside 2019 removed", "Rows used in the dashboard"],
        "Rows": [rows_in_file, empty_removed, duplicates_removed, outside_2019_removed, len(df)],
    })
    st.table(steps.set_index("Step"))

    st.subheader("Outliers")
    left, right = st.columns(2)
    with left:
        fig = px.box(df, y="Sales", title="Sales per row", color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.histogram(df, x="Quantity Ordered", title="Quantity ordered in one row",
                           color_discrete_sequence=[BLUE])
        st.plotly_chart(fig, use_container_width=True)
    st.write("The dots above the box are laptops, phones and monitors. They are real, because expensive "
             "products cost more, so we keep them. Large quantities (7 to 9) are only cheap batteries, "
             "so we keep those too.")

    st.subheader("Cleaned data (first 100 rows)")
    st.dataframe(df.head(100), hide_index=True)
