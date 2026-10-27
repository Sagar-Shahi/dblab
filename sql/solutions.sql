-- Reference solutions. Each block starts with a "-- Q<number>" marker, which the test-suite reads.

-- Q1
SELECT name
FROM customers
WHERE city = 'Kathmandu'
ORDER BY name;

-- Q2
SELECT title, price
FROM products
WHERE price > 20
ORDER BY price DESC;

-- Q3
SELECT status, COUNT(*) AS orders
FROM orders
GROUP BY status
ORDER BY status;

-- Q4
SELECT oi.order_id, SUM(p.price * oi.quantity) AS total
FROM order_items AS oi
JOIN products AS p ON p.product_id = oi.product_id
GROUP BY oi.order_id
ORDER BY total DESC, oi.order_id;

-- Q5
SELECT c.name
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL;

-- Q6
SELECT p.title
FROM products AS p
WHERE NOT EXISTS (SELECT 1 FROM order_items AS oi WHERE oi.product_id = p.product_id);

-- Q7
SELECT c.name, SUM(p.price * oi.quantity) AS spent
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.status <> 'cancelled'
GROUP BY c.customer_id, c.name
ORDER BY spent DESC
LIMIT 1;

-- Q8
SELECT substr(o.order_date, 1, 7) AS month, SUM(p.price * oi.quantity) AS revenue
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.status <> 'cancelled'
GROUP BY month
ORDER BY month;

-- Q9
SELECT c.name, COUNT(*) AS orders
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(*) > 2;

-- Q10
WITH order_value AS (
    SELECT o.order_id, o.order_date, SUM(p.price * oi.quantity) AS value
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    JOIN products AS p ON p.product_id = oi.product_id
    WHERE o.status <> 'cancelled'
    GROUP BY o.order_id, o.order_date
)
SELECT order_id, order_date, value,
       SUM(value) OVER (ORDER BY order_date, order_id) AS running_total
FROM order_value
ORDER BY order_date, order_id;

-- Q11
WITH units AS (
    SELECT p.title, p.category, COALESCE(SUM(oi.quantity), 0) AS units
    FROM products AS p
    LEFT JOIN order_items AS oi ON oi.product_id = p.product_id
    GROUP BY p.product_id, p.title, p.category
)
SELECT title, category, units,
       RANK() OVER (PARTITION BY category ORDER BY units DESC) AS rank_in_category
FROM units
ORDER BY category, rank_in_category, title;

-- Q12
WITH order_value AS (
    SELECT o.order_id, o.customer_id, SUM(p.price * oi.quantity) AS value
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    JOIN products AS p ON p.product_id = oi.product_id
    WHERE o.status <> 'cancelled'
    GROUP BY o.order_id, o.customer_id
)
SELECT c.city, ROUND(AVG(ov.value), 2) AS avg_order_value
FROM order_value AS ov
JOIN customers AS c ON c.customer_id = ov.customer_id
GROUP BY c.city
ORDER BY c.city;

-- Q13
SELECT DISTINCT p.title
FROM order_items AS base
JOIN products AS target ON target.product_id = base.product_id AND target.title = 'Python Crash Notes'
JOIN order_items AS other ON other.order_id = base.order_id AND other.product_id <> base.product_id
JOIN products AS p ON p.product_id = other.product_id
ORDER BY p.title;

-- Q14
WITH spend AS (
    SELECT o.customer_id, SUM(p.price * oi.quantity) AS total
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    JOIN products AS p ON p.product_id = oi.product_id
    WHERE o.status <> 'cancelled'
    GROUP BY o.customer_id
)
SELECT c.name, s.total
FROM spend AS s
JOIN customers AS c ON c.customer_id = s.customer_id
WHERE s.total > (SELECT AVG(total) FROM spend)
ORDER BY s.total DESC;

-- Q15
SELECT name, order_id, order_date
FROM (
    SELECT c.name, o.order_id, o.order_date,
           ROW_NUMBER() OVER (PARTITION BY c.customer_id ORDER BY o.order_date DESC, o.order_id DESC) AS rn
    FROM customers AS c
    JOIN orders AS o ON o.customer_id = c.customer_id
)
WHERE rn = 1
ORDER BY name;
