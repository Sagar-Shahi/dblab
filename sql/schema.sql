-- DBLab practice database: a small online shop selling developer books and gear.
-- Runs on SQLite 3.25+, and is written in standard SQL so it ports to PostgreSQL / MySQL 8.

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    signup_date TEXT NOT NULL            -- ISO date, YYYY-MM-DD
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    category   TEXT NOT NULL,            -- 'book', 'hardware' or 'gadget'
    price      REAL NOT NULL CHECK (price >= 0)
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
    order_date  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('paid', 'shipped', 'cancelled'))
);

CREATE TABLE order_items (
    order_id   INTEGER NOT NULL REFERENCES orders (order_id),
    product_id INTEGER NOT NULL REFERENCES products (product_id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, product_id)   -- composite key: one line per product per order
);

CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_items_product   ON order_items (product_id);
