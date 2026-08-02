-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Initialize the orders table for TechNova chatbot
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer TEXT NOT NULL,
    product TEXT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status TEXT NOT NULL,
    order_date DATE NOT NULL
);

-- Seed data from orders.csv
INSERT INTO orders (order_id, customer, product, amount, status, order_date) VALUES
(1001, 'Alice Johnson', 'SmartHub Pro', 199.00, 'delivered', '2026-04-10'),
(1002, 'Bob Smith', 'SmartHub Lite', 99.00, 'delivered', '2026-04-12'),
(1003, 'Carol White', 'SmartHub Enterprise', 499.00, 'delivered', '2026-04-15'),
(1004, 'David Brown', 'SmartHub Pro', 199.00, 'cancelled', '2026-04-18'),
(1005, 'Eve Davis', 'SmartHub Lite', 99.00, 'delivered', '2026-04-20'),
(1006, 'Frank Miller', 'SmartHub Pro', 199.00, 'pending', '2026-04-22'),
(1007, 'Grace Lee', 'SmartHub Enterprise', 499.00, 'delivered', '2026-04-25'),
(1008, 'Henry Wilson', 'SmartHub Lite', 99.00, 'shipped', '2026-04-28'),
(1009, 'Ivy Martinez', 'SmartHub Pro', 199.00, 'delivered', '2026-05-01'),
(1010, 'Jack Anderson', 'SmartHub Lite', 99.00, 'delivered', '2026-05-03'),
(1011, 'Karen Thomas', 'SmartHub Pro', 199.00, 'delivered', '2026-05-05'),
(1012, 'Leo Jackson', 'SmartHub Enterprise', 499.00, 'pending', '2026-05-07'),
(1013, 'Mia Harris', 'SmartHub Lite', 99.00, 'delivered', '2026-05-09'),
(1014, 'Noah Clark', 'SmartHub Pro', 199.00, 'shipped', '2026-05-11'),
(1015, 'Olivia Lewis', 'SmartHub Lite', 99.00, 'cancelled', '2026-05-13'),
(1016, 'Peter Robinson', 'SmartHub Pro', 199.00, 'delivered', '2026-05-15'),
(1017, 'Quinn Walker', 'SmartHub Enterprise', 499.00, 'delivered', '2026-05-17'),
(1018, 'Rachel Hall', 'SmartHub Lite', 99.00, 'delivered', '2026-05-19'),
(1019, 'Sam Young', 'SmartHub Pro', 199.00, 'pending', '2026-05-20'),
(1020, 'Tina King', 'SmartHub Lite', 99.00, 'delivered', '2026-05-21'),
(1021, 'Uma Wright', 'SmartHub Pro', 199.00, 'delivered', '2026-05-22'),
(1022, 'Victor Lopez', 'SmartHub Enterprise', 499.00, 'shipped', '2026-05-23'),
(1023, 'Wendy Hill', 'SmartHub Lite', 99.00, 'delivered', '2026-05-24'),
(1024, 'Xavier Scott', 'SmartHub Pro', 199.00, 'delivered', '2026-05-25'),
(1025, 'Yara Green', 'SmartHub Lite', 99.00, 'pending', '2026-05-26'),
(1026, 'Zach Adams', 'SmartHub Pro', 199.00, 'delivered', '2026-05-27'),
(1027, 'Alice Johnson', 'SmartHub Lite', 99.00, 'delivered', '2026-05-28'),
(1028, 'Bob Smith', 'SmartHub Enterprise', 499.00, 'delivered', '2026-05-29'),
(1029, 'Carol White', 'SmartHub Pro', 199.00, 'cancelled', '2026-05-30'),
(1030, 'David Brown', 'SmartHub Lite', 99.00, 'delivered', '2026-05-31'),
(1031, 'Eve Davis', 'SmartHub Pro', 199.00, 'delivered', '2026-06-01'),
(1032, 'Frank Miller', 'SmartHub Enterprise', 499.00, 'pending', '2026-06-02'),
(1033, 'Grace Lee', 'SmartHub Lite', 99.00, 'delivered', '2026-06-03'),
(1034, 'Henry Wilson', 'SmartHub Pro', 199.00, 'shipped', '2026-06-04'),
(1035, 'Ivy Martinez', 'SmartHub Lite', 99.00, 'delivered', '2026-06-05'),
(1036, 'Jack Anderson', 'SmartHub Pro', 199.00, 'delivered', '2026-06-06'),
(1037, 'Karen Thomas', 'SmartHub Enterprise', 499.00, 'delivered', '2026-06-07'),
(1038, 'Leo Jackson', 'SmartHub Lite', 99.00, 'cancelled', '2026-06-08'),
(1039, 'Mia Harris', 'SmartHub Pro', 199.00, 'delivered', '2026-06-09'),
(1040, 'Noah Clark', 'SmartHub Lite', 99.00, 'pending', '2026-06-10'),
(1041, 'Olivia Lewis', 'SmartHub Pro', 199.00, 'delivered', '2026-06-11'),
(1042, 'Peter Robinson', 'SmartHub Enterprise', 499.00, 'delivered', '2026-06-12'),
(1043, 'Quinn Walker', 'SmartHub Lite', 99.00, 'shipped', '2026-06-13'),
(1044, 'Rachel Hall', 'SmartHub Pro', 199.00, 'delivered', '2026-06-14'),
(1045, 'Sam Young', 'SmartHub Lite', 99.00, 'delivered', '2026-06-15')
ON CONFLICT (order_id) DO NOTHING;

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product);
