"""
Core analysis for the Olist project. Produces the figures and the numbers quoted
in the README:

  1. Monthly revenue trend and a category breakdown chart.
  2. Monthly cohort retention, using customer_unique_id so a cohort follows the
     real person, not the per-order id.
  3. RFM segmentation (Recency, Frequency, Monetary) mapping every customer to a
     named segment.
  4. Delivery performance: does a slower or late delivery lower the review score.

Run from the project root:
    python src/analysis.py
"""

import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DB = Path("data/olist.db")
FIG = Path("reports/figures")
FIG.mkdir(parents=True, exist_ok=True)
BLUE = "#3C78D8"


def load():
    con = sqlite3.connect(DB)
    lines = pd.read_sql_query("SELECT * FROM order_lines", con, parse_dates=[
        "order_purchase_timestamp", "order_delivered_customer_date",
        "order_estimated_delivery_date"])
    reviews = pd.read_sql_query("SELECT order_id, review_score FROM reviews", con)
    con.close()
    return lines, reviews


def fig_monthly_revenue(lines):
    d = lines[lines.order_status == "delivered"]
    m = d.groupby("purchase_month")["item_revenue"].sum().reset_index()
    m = m[(m.purchase_month >= "2017-01") & (m.purchase_month <= "2018-08")]
    plt.figure(figsize=(9, 4))
    plt.plot(m.purchase_month, m.item_revenue / 1000, color=BLUE, marker="o", lw=2)
    plt.xticks(rotation=60, fontsize=7)
    plt.ylabel("Revenue (thousand R$)")
    plt.title("Monthly delivered revenue")
    plt.tight_layout()
    plt.savefig(FIG / "monthly_revenue.png", dpi=120)
    plt.close()


def fig_categories(lines):
    d = lines[lines.order_status == "delivered"]
    c = d.groupby("category")["item_revenue"].sum().sort_values(ascending=False).head(10)
    plt.figure(figsize=(9, 4))
    plt.barh(c.index[::-1], (c.values[::-1]) / 1000, color=BLUE)
    plt.xlabel("Revenue (thousand R$)")
    plt.title("Top 10 categories by revenue")
    plt.tight_layout()
    plt.savefig(FIG / "top_categories.png", dpi=120)
    plt.close()


def cohort_retention(lines):
    d = lines[lines.order_status == "delivered"].dropna(subset=["customer_unique_id"])
    orders = d.drop_duplicates("order_id")[
        ["customer_unique_id", "order_id", "order_purchase_timestamp"]].copy()
    orders["month"] = orders.order_purchase_timestamp.dt.to_period("M")
    first = orders.groupby("customer_unique_id").month.min().rename("cohort")
    orders = orders.join(first, on="customer_unique_id")
    orders["offset"] = (orders.month - orders.cohort).apply(lambda x: x.n)
    pivot = orders.pivot_table(index="cohort", columns="offset",
                               values="customer_unique_id", aggfunc="nunique")
    size = pivot[0]
    retention = pivot.divide(size, axis=0)
    # month-1 retention averaged across cohorts with enough size
    m1 = retention[1].dropna()
    plt.figure(figsize=(7, 4))
    plt.plot(range(len(m1)), m1.values * 100, color=BLUE, marker="o")
    plt.ylabel("Month-1 retention (%)")
    plt.xlabel("Cohort (chronological)")
    plt.title("Month-1 cohort retention")
    plt.tight_layout()
    plt.savefig(FIG / "cohort_retention.png", dpi=120)
    plt.close()
    return float(np.nanmean(m1.values) * 100)


def rfm(lines):
    d = lines[lines.order_status == "delivered"].dropna(subset=["customer_unique_id"])
    orders = d.drop_duplicates("order_id")[
        ["customer_unique_id", "order_id", "order_purchase_timestamp"]]
    rev = d.groupby("order_id")["item_revenue"].sum().rename("order_value")
    orders = orders.join(rev, on="order_id")
    snapshot = orders.order_purchase_timestamp.max() + pd.Timedelta(days=1)
    g = orders.groupby("customer_unique_id").agg(
        recency=("order_purchase_timestamp", lambda x: (snapshot - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("order_value", "sum"),
    ).reset_index()

    # Scores 1 to 4. Recency reversed (more recent is better).
    g["R"] = pd.qcut(g.recency, 4, labels=[4, 3, 2, 1]).astype(int)
    g["M"] = pd.qcut(g.monetary, 4, labels=[1, 2, 3, 4]).astype(int)
    # Frequency is almost all 1 in this data, so rank instead of qcut.
    g["F"] = np.where(g.frequency > 1, 4, 1)

    def segment(row):
        if row.F == 4 and row.M >= 3:
            return "Champions"
        if row.F == 4:
            return "Loyal"
        if row.R >= 3 and row.M >= 3:
            return "Promising"
        if row.R >= 3:
            return "Recent"
        if row.R == 1 and row.M >= 3:
            return "At risk (high value)"
        return "Hibernating"

    g["segment"] = g.apply(segment, axis=1)
    counts = g.segment.value_counts()
    plt.figure(figsize=(8, 4))
    plt.barh(counts.index[::-1], counts.values[::-1], color=BLUE)
    plt.xlabel("Customers")
    plt.title("RFM segments")
    plt.tight_layout()
    plt.savefig(FIG / "rfm_segments.png", dpi=120)
    plt.close()
    g.to_csv("reports/rfm_table.csv", index=False)
    return counts


def delivery_vs_reviews(lines, reviews):
    d = lines[lines.order_status == "delivered"].drop_duplicates("order_id").copy()
    d = d.merge(reviews.drop_duplicates("order_id"), on="order_id", how="inner")
    d = d.dropna(subset=["delivery_days", "review_score"])
    d = d[(d.delivery_days >= 0) & (d.delivery_days < 120)]
    d["late_bool"] = d.late == 1
    on_time = d[~d.late_bool].review_score.mean()
    late = d[d.late_bool].review_score.mean()
    # bucket delivery days
    bins = [0, 5, 10, 15, 20, 30, 120]
    labels = ["0-5", "6-10", "11-15", "16-20", "21-30", "31+"]
    d["bucket"] = pd.cut(d.delivery_days, bins=bins, labels=labels, right=True)
    by = d.groupby("bucket", observed=True).review_score.mean()
    plt.figure(figsize=(7, 4))
    plt.bar(by.index.astype(str), by.values, color=BLUE)
    plt.ylim(1, 5)
    plt.ylabel("Average review score")
    plt.xlabel("Delivery time (days)")
    plt.title("Slower delivery lowers review score")
    plt.tight_layout()
    plt.savefig(FIG / "delivery_vs_reviews.png", dpi=120)
    plt.close()
    return on_time, late, by


def main():
    lines, reviews = load()
    fig_monthly_revenue(lines)
    fig_categories(lines)
    m1 = cohort_retention(lines)
    seg = rfm(lines)
    on_time, late, by = delivery_vs_reviews(lines, reviews)

    print("Average month-1 cohort retention: %.2f%%" % m1)
    print("\nRFM segment sizes:")
    print(seg.to_string())
    print("\nAverage review score, on-time deliveries: %.2f" % on_time)
    print("Average review score, late deliveries:    %.2f" % late)
    print("\nReview score by delivery-time bucket:")
    print(by.round(2).to_string())
    print("\nFigures saved to", FIG)


if __name__ == "__main__":
    main()
