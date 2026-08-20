"""
Interactive dashboard for the Olist e-commerce project.

Run from the project root after building the database:
    streamlit run dashboard/app.py

Tabs:
  Overview   headline KPIs and the monthly revenue trend
  Categories revenue by product category and by state
  Customers  RFM segment sizes
  Delivery   review score against delivery time
"""

import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

DB = Path("data/olist.db")
BLUE = "#3C78D8"

st.set_page_config(page_title="Olist E-commerce Analytics", layout="wide")


@st.cache_data
def load():
    con = sqlite3.connect(DB)
    lines = pd.read_sql_query(
        "SELECT * FROM order_lines WHERE order_status = 'delivered'", con,
        parse_dates=["order_purchase_timestamp", "order_delivered_customer_date"])
    reviews = pd.read_sql_query("SELECT order_id, review_score FROM reviews", con)
    con.close()
    return lines, reviews


lines, reviews = load()

# Sidebar filters
st.sidebar.header("Filters")
states = sorted(lines.customer_state.dropna().unique())
cats = sorted(lines.category.dropna().unique())
sel_states = st.sidebar.multiselect("State", states, default=[])
sel_cats = st.sidebar.multiselect("Category", cats, default=[])

df = lines.copy()
if sel_states:
    df = df[df.customer_state.isin(sel_states)]
if sel_cats:
    df = df[df.category.isin(sel_cats)]

st.title("Olist E-commerce Marketplace Analytics")
st.caption("Real Brazilian marketplace data (Olist, 2016 to 2018). Revenue = item price plus freight on delivered orders.")

orders = df.order_id.nunique()
revenue = df.item_revenue.sum()
aov = revenue / orders if orders else 0

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Categories", "Customers", "Delivery"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Delivered orders", f"{orders:,}")
    c2.metric("Revenue", f"R$ {revenue:,.0f}")
    c3.metric("Average order value", f"R$ {aov:,.2f}")
    m = (df.assign(month=df.order_purchase_timestamp.dt.to_period("M").astype(str))
           .groupby("month").item_revenue.sum().reset_index())
    m = m[(m.month >= "2017-01") & (m.month <= "2018-08")]
    fig = px.line(m, x="month", y="item_revenue", markers=True,
                  labels={"item_revenue": "Revenue (R$)", "month": "Month"})
    fig.update_traces(line_color=BLUE)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    c = (df.groupby("category").item_revenue.sum()
           .sort_values(ascending=False).head(12).reset_index())
    fig = px.bar(c, x="item_revenue", y="category", orientation="h",
                 labels={"item_revenue": "Revenue (R$)", "category": ""})
    fig.update_traces(marker_color=BLUE)
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
    s = (df.groupby("customer_state").item_revenue.sum()
           .sort_values(ascending=False).head(12).reset_index())
    fig2 = px.bar(s, x="customer_state", y="item_revenue",
                  labels={"item_revenue": "Revenue (R$)", "customer_state": "State"})
    fig2.update_traces(marker_color=BLUE)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    rfm_path = Path("reports/rfm_table.csv")
    if rfm_path.exists():
        g = pd.read_csv(rfm_path)
        counts = g.segment.value_counts().reset_index()
        counts.columns = ["segment", "customers"]
        fig = px.bar(counts, x="customers", y="segment", orientation="h")
        fig.update_traces(marker_color=BLUE)
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
        st.caption("RFM segments are computed on the full dataset. Run src/analysis.py to refresh.")
    else:
        st.info("Run python src/analysis.py to generate the RFM table.")

with tab4:
    d = df.drop_duplicates("order_id").merge(
        reviews.drop_duplicates("order_id"), on="order_id", how="inner")
    d = d.dropna(subset=["delivery_days", "review_score"])
    d = d[(d.delivery_days >= 0) & (d.delivery_days < 120)]
    bins = [0, 5, 10, 15, 20, 30, 120]
    labels = ["0-5", "6-10", "11-15", "16-20", "21-30", "31+"]
    d["bucket"] = pd.cut(d.delivery_days, bins=bins, labels=labels)
    by = d.groupby("bucket", observed=True).review_score.mean().reset_index()
    fig = px.bar(by, x="bucket", y="review_score",
                 labels={"review_score": "Average review score", "bucket": "Delivery time (days)"})
    fig.update_traces(marker_color=BLUE)
    fig.update_yaxes(range=[1, 5])
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Slower and late deliveries are linked to sharply lower review scores.")
