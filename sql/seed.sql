INSERT INTO customers (customer_id, name, city, signup_date) VALUES
    (1, 'Asha Gurung',    'Kathmandu',  '2025-11-02'),
    (2, 'Bikram Thapa',   'Pokhara',    '2025-12-15'),
    (3, 'Chandra Shrestha', 'Lalitpur', '2026-01-20'),
    (4, 'Dipesh Karki',   'Kathmandu',  '2026-02-08'),
    (5, 'Esha Rai',       'Biratnagar', '2026-03-30'),
    (6, 'Faisal Ansari',  'Pokhara',    '2026-04-11');

INSERT INTO products (product_id, title, category, price) VALUES
    (1, 'Python Crash Notes',    'book',     12.50),
    (2, 'Java Handbook',         'book',     18.00),
    (3, 'C++ Primer Lite',       'book',     20.00),
    (4, 'SQL Cookbook',          'book',     15.00),
    (5, 'Mechanical Keyboard',   'hardware', 65.00),
    (6, 'USB-C Hub',             'hardware', 30.00),
    (7, 'Laptop Stand',          'hardware', 25.00),
    (8, 'Rubber Duck',           'gadget',    5.00);

INSERT INTO orders (order_id, customer_id, order_date, status) VALUES
    (1,  1, '2026-01-05', 'paid'),
    (2,  1, '2026-02-11', 'shipped'),
    (3,  2, '2026-02-14', 'paid'),
    (4,  3, '2026-03-02', 'cancelled'),
    (5,  3, '2026-03-09', 'shipped'),
    (6,  4, '2026-03-15', 'paid'),
    (7,  2, '2026-04-01', 'shipped'),
    (8,  5, '2026-04-20', 'paid'),
    (9,  1, '2026-05-03', 'paid'),
    (10, 4, '2026-05-18', 'shipped');

INSERT INTO order_items (order_id, product_id, quantity) VALUES
    (1, 1, 2), (1, 4, 1),
    (2, 5, 1),
    (3, 2, 1), (3, 6, 2),
    (4, 3, 1),
    (5, 1, 1), (5, 7, 1),
    (6, 5, 1), (6, 6, 1),
    (7, 4, 3),
    (8, 2, 2), (8, 3, 1),
    (9, 7, 2), (9, 6, 1),
    (10, 1, 1), (10, 2, 1), (10, 4, 1);
