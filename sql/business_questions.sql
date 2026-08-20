-- Business questions answered against the Olist SQLite database.
-- Each query is named with a -- @name tag so the runner can execute them one by one.
-- Revenue here means item price plus freight, summed from order_lines.
-- Only delivered orders are counted as realised revenue.

-- @name total_kpis
SELECT
  COUNT(DISTINCT order_id)                         AS orders,
  ROUND(SUM(item_revenue), 2)                      AS revenue,
  ROUND(SUM(item_revenue) * 1.0 / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM order_lines
WHERE order_status = 'delivered';

-- @name revenue_by_category
SELECT category,
       ROUND(SUM(item_revenue), 2) AS revenue,
       COUNT(*)                    AS items
FROM order_lines
WHERE order_status = 'delivered'
GROUP BY category
ORDER BY revenue DESC
LIMIT 10;

-- @name revenue_by_state
SELECT customer_state AS state,
       ROUND(SUM(item_revenue), 2) AS revenue,
       COUNT(DISTINCT order_id)    AS orders
FROM order_lines
WHERE order_status = 'delivered'
GROUP BY customer_state
ORDER BY revenue DESC
LIMIT 10;

-- @name monthly_revenue
SELECT purchase_month AS month,
       ROUND(SUM(item_revenue), 2) AS revenue,
       COUNT(DISTINCT order_id)    AS orders
FROM order_lines
WHERE order_status = 'delivered'
GROUP BY purchase_month
ORDER BY purchase_month;

-- @name repeat_purchase_rate
-- Share of real customers (customer_unique_id) with more than one delivered order.
WITH per_customer AS (
  SELECT c.customer_unique_id AS uid,
         COUNT(DISTINCT o.order_id) AS n_orders
  FROM orders o
  JOIN customers c ON c.customer_id = o.customer_id
  WHERE o.order_status = 'delivered'
  GROUP BY c.customer_unique_id
)
SELECT COUNT(*)                                             AS customers,
       SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END)        AS repeat_customers,
       ROUND(100.0 * SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                            AS repeat_rate_pct
FROM per_customer;

-- @name top_sellers
SELECT seller_id,
       ROUND(SUM(item_revenue), 2) AS revenue,
       COUNT(DISTINCT order_id)    AS orders
FROM order_lines
WHERE order_status = 'delivered'
GROUP BY seller_id
ORDER BY revenue DESC
LIMIT 10;

-- @name payment_mix
SELECT payment_type,
       COUNT(*)                        AS payments,
       ROUND(SUM(payment_value), 2)    AS value,
       ROUND(AVG(payment_installments), 2) AS avg_installments
FROM payments
GROUP BY payment_type
ORDER BY value DESC;
