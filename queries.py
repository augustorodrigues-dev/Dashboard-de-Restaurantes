"""
Este arquivo centraliza todas as consultas SQL usadas no dashboard.
VERSÃO SEM DEPENDÊNCIA: Compatível com psycopg (v3).
"""
SELECT_STORES = """
    SELECT id as store_id, name as store_name 
    FROM stores 
    WHERE is_active = true
"""

SELECT_CHANNELS = """
    SELECT id as channel_id, name as channel_name 
    FROM channels
"""

SELECT_PAYMENT_TYPES = """
    SELECT id as payment_type_id, description as payment_description 
    FROM payment_types
"""


SELECT_DATE_LIMITS = """
    SELECT MIN(created_at)::date as min_date, MAX(created_at)::date as max_date 
    FROM sales
"""


SELECT_ANALYSIS_DATA = """
SELECT
    s.id AS sale_id, s.created_at, s.total_amount, s.production_seconds,
    s.delivery_seconds, s.customer_id, s.total_amount_items, s.total_discount,
    s.delivery_fee, s.service_tax_fee, st.id AS store_id, st.name AS store_name,
    ch.id AS channel_id, ch.name AS channel_name, p.id AS product_id,
    p.name AS product_name, c.id AS category_id, c.name AS category_name,
    ps.quantity, ps.total_price AS product_total_price,
    EXTRACT(ISODOW FROM s.created_at) AS dia_semana_num,
    CASE EXTRACT(ISODOW FROM s.created_at)
        WHEN 1 THEN '1. Seg' WHEN 2 THEN '2. Ter' WHEN 3 THEN '3. Qua'
        WHEN 4 THEN '4. Qui' WHEN 5 THEN '5. Sex' WHEN 6 THEN '6. Sab'
        WHEN 7 THEN '7. Dom'
    END AS dia_semana_nome,
    EXTRACT(HOUR FROM s.created_at) AS hora_dia
FROM sales s
JOIN stores st ON s.store_id = st.id
JOIN channels ch ON s.channel_id = ch.id
LEFT JOIN product_sales ps ON s.id = ps.sale_id
LEFT JOIN products p ON ps.product_id = p.id
LEFT JOIN categories c ON p.category_id = c.id
WHERE s.created_at >= %(start)s AND s.created_at < %(end)s
"""


SELECT_PAYMENTS = """
    SELECT sale_id, payment_type_id, value 
    FROM payments 
    WHERE sale_id IN %(sales_ids)s
"""


SELECT_RFM = """
WITH rfm AS (
    SELECT
        customer_id, COUNT(id) AS frequencia, SUM(total_amount) AS valor_total,
        MAX(created_at) AS ultima_compra,
        (%(data_ref)s::date - MAX(created_at)::date) AS dias_sem_comprar
    FROM sales
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
)
SELECT
    c.id, COALESCE(c.customer_name, 'Cliente Desconhecido') AS customer_name,
    c.phone_number, c.email, r.frequencia, r.valor_total,
    r.ultima_compra, r.dias_sem_comprar
FROM rfm r
LEFT JOIN customers c ON r.customer_id = c.id
ORDER BY r.frequencia DESC
"""