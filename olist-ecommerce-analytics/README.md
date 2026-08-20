# Olist E-commerce Marketplace Analytics

An end to end analytics project on the Olist Brazilian e-commerce dataset, a real
marketplace with multiple sellers, close to 100,000 orders, and full data on
products, payments, deliveries and customer reviews. The project takes the raw
data through cleaning, SQL business analysis, customer segmentation and an
interactive dashboard, and ends with a clear commercial insight about delivery
performance.

I built this to work with real marketplace data rather than a clean synthetic
set, so the questions and the findings are genuine.

## The data

The dataset is the public Olist Store dataset. It covers orders placed between
September 2016 and October 2018 and is spread across nine tables:

| Table | Rows | What it holds |
|---|---|---|
| orders | 99,441 | one row per order, with status and timestamps |
| order_items | 112,650 | one row per product line, with price and freight |
| customers | 99,441 | links each order to a real person via customer_unique_id |
| order_payments | 103,886 | payment type, value and installments |
| order_reviews | 104,719 | review score from 1 to 5 |
| products | 32,951 | product attributes and category |
| sellers | 3,095 | seller location |
| geolocation | 1,000,163 | zip code coordinates |
| category translation | 71 | Portuguese to English category names |

One detail that matters: `customer_id` is unique per order, not per person. The
real customer is `customer_unique_id`. Every question about repeat buyers or
customer value uses `customer_unique_id`, which is easy to get wrong.

The raw CSV files are not committed to this repository because they are large and
belong to Olist. Download them from Kaggle (search "Brazilian E-Commerce Public
Dataset by Olist") and place the nine CSV files in `data/raw/`.

## How to run

```bash
pip install -r requirements.txt
python src/build_db.py       # load and clean into data/olist.db
python sql/run_sql.py        # print the business question results
python src/analysis.py       # cohorts, RFM, delivery, and the figures
streamlit run dashboard/app.py
```

## What I found

All numbers below come straight from the scripts on the real data.

**Headline.** Across delivered orders the marketplace took R$ 15.4 million on
about 96,500 orders, an average order value of R$ 159.83.

**Where the money is.** Revenue is concentrated. Sao Paulo state alone accounts
for R$ 5.77 million, more than a third of the total. The top categories are
health and beauty, watches and gifts, bed bath and table, and sports and
leisure. Volume grew strongly through 2017 and 2018, with a clear spike in
November 2017 around Black Friday.

**Customers buy once.** Only 3.0 percent of customers ever place a second order,
and monthly cohort retention sits in the low single digits. For a marketplace
like this the growth story is about acquisition, and the biggest retention lever
is the experience on the first order.

**Delivery drives satisfaction.** This is the clearest commercial finding.
On time deliveries average a 4.29 review score. Late deliveries drop to 2.56.
Broken down by delivery time, orders arriving within five days average 4.45
stars, while orders taking more than 30 days average 2.25. Since almost all
customers buy only once, a poor first delivery is very hard to recover from, so
delivery speed and reliability are worth protecting.

**Payments.** Credit card is dominant at about 81 percent of payment value, with
an average of 3.5 installments, which says something about how price sensitive
and installment driven this market is.

## Customer segmentation

I scored every customer on Recency, Frequency and Monetary value and mapped them
to segments. Because repeat buying is rare, frequency barely separates people, so
the useful split is between recent higher value buyers worth nurturing and the
large hibernating group. Segment sizes are in `reports/rfm_table.csv` and the
chart is in `reports/figures/rfm_segments.png`.

## Project layout

```
data/raw/        the nine Olist CSVs (not committed, download from Kaggle)
src/build_db.py  load and clean into SQLite
src/analysis.py  cohorts, RFM, delivery analysis, figures
sql/             business questions and a runner
dashboard/app.py Streamlit dashboard
reports/figures  generated charts
```

## Tools

Python (pandas, numpy, matplotlib, plotly), SQL (SQLite), and Streamlit.
