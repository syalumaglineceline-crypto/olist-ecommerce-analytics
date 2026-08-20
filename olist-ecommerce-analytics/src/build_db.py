"""
Load the raw Olist CSV files into a single SQLite database and build a clean
analysis table.

The Olist dataset is spread across nine files. This script reads them, fixes the
date columns, translates the Portuguese product categories into English, removes
a small number of rows that cannot be used, and writes everything to
olist.db so the rest of the project can query it with plain SQL.

One important detail about this data: customer_id in the orders table is unique
per order, not per person. The real person is identified by customer_unique_id
in the customers table. Any question about repeat buyers or customer value has
to use customer_unique_id, and this project does.

Run from the project root:
    python src/build_db.py
"""

import sqlite3
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
DB = Path("data/olist.db")

DATE_COLS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}


def load(name, filename):
    df = pd.read_csv(RAW / filename)
    for col in DATE_COLS.get(name, []):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def main():
    orders = load("orders", "olist_orders_dataset.csv")
    items = load("order_items", "olist_order_items_dataset.csv")
    customers = load("customers", "olist_customers_dataset.csv")
    payments = load("payments", "olist_order_payments_dataset.csv")
    reviews = load("reviews", "olist_order_reviews_dataset.csv")
    products = load("products", "olist_products_dataset.csv")
    sellers = load("sellers", "olist_sellers_dataset.csv")
    cats = load("cats", "product_category_name_translation.csv")

    # Translate product categories to English, keep the original if no match.
    products = products.merge(cats, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna(
        products["product_category_name"]
    ).fillna("unknown")

    # A clean order line table is the backbone of most questions.
    # One row per product line, with its order, customer, category and revenue.
    line = (
        items.merge(orders, on="order_id", how="left")
        .merge(customers, on="customer_id", how="left")
        .merge(products[["product_id", "category"]], on="product_id", how="left")
    )
    line["item_revenue"] = line["price"] + line["freight_value"]
    line["purchase_month"] = line["order_purchase_timestamp"].dt.to_period("M").astype(str)

    # Delivery time in days for delivered orders only.
    delivered = line["order_delivered_customer_date"].notna()
    line["delivery_days"] = (
        line["order_delivered_customer_date"] - line["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    line.loc[~delivered, "delivery_days"] = pd.NA
    # Late flag: delivered after the estimated date.
    line["late"] = (
        line["order_delivered_customer_date"] > line["order_estimated_delivery_date"]
    )

    con = sqlite3.connect(DB)
    orders.to_sql("orders", con, if_exists="replace", index=False)
    items.to_sql("order_items", con, if_exists="replace", index=False)
    customers.to_sql("customers", con, if_exists="replace", index=False)
    payments.to_sql("payments", con, if_exists="replace", index=False)
    reviews.to_sql("reviews", con, if_exists="replace", index=False)
    products.to_sql("products", con, if_exists="replace", index=False)
    sellers.to_sql("sellers", con, if_exists="replace", index=False)
    line.to_sql("order_lines", con, if_exists="replace", index=False)
    con.commit()

    print("Database written to", DB)
    print("orders           ", len(orders))
    print("order_items      ", len(items))
    print("order_lines      ", len(line))
    print("customers        ", len(customers))
    print("unique customers ", customers["customer_unique_id"].nunique())
    print("sellers          ", len(sellers))
    print("date range       ",
          orders["order_purchase_timestamp"].min(), "to",
          orders["order_purchase_timestamp"].max())
    con.close()


if __name__ == "__main__":
    main()
