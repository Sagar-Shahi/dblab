# SQL exercises

Fifteen problems on the shop database in [`schema.sql`](schema.sql) and [`seed.sql`](seed.sql),
ordered from basic filtering to window functions. Try each one yourself before opening
[`solutions.sql`](solutions.sql).

```
customers(customer_id, name, city, signup_date)
products(product_id, title, category, price)
orders(order_id, customer_id, order_date, status)          -- status: paid | shipped | cancelled
order_items(order_id, product_id, quantity)                -- PK (order_id, product_id)
```

Run them in any SQLite shell, or let the test-suite check your work:

```bash
cd python && python -m unittest tests.test_sql_exercises -v
```

| # | Skill | Task |
|---|-------|------|
| 1 | `WHERE` | List the names of customers living in Kathmandu, sorted alphabetically. |
| 2 | `ORDER BY` | List products costing more than 20, most expensive first (title, price). |
| 3 | `GROUP BY` | Count orders per status. |
| 4 | `JOIN` + aggregate | Give the total value of each order (`price * quantity` summed), highest first. |
| 5 | `LEFT JOIN` | Find customers who have never placed an order. |
| 6 | `NOT EXISTS` | Find products that have never been ordered. |
| 7 | multi-table `JOIN` | Which customer spent the most, ignoring cancelled orders? Return name and total. |
| 8 | date functions | Revenue per month (`YYYY-MM`), ignoring cancelled orders. |
| 9 | `HAVING` | Customers with more than two orders: name and order count. |
| 10 | window `SUM() OVER` | For non-cancelled orders, show each order's value and the running total by date. |
| 11 | `RANK() OVER` | Rank products by units ordered (any status) within their category (title, category, units, rank). |
| 12 | CTE | Average order value per city, ignoring cancelled orders. |
| 13 | self-join | Which products were bought in the same order as *Python Crash Notes*? |
| 14 | subquery | Customers whose total spend is above the average spend of customers who ordered. |
| 15 | `ROW_NUMBER()` | Each customer's most recent order (customer name, order_id, order_date). |

## Stretch goals

- Add a `reviews` table and write the query that finds the best-rated product per category.
- Rewrite problem 4 so the order total includes a 10% discount on orders over 100.
- Run `EXPLAIN QUERY PLAN` on problem 5 with and without `idx_orders_customer`.
