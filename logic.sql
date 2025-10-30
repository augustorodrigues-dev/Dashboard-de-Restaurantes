DROP VIEW IF EXISTS v_analysis_explorer;
DROP FUNCTION IF EXISTS get_rfm_analysis(date);

CREATE VIEW v_analysis_explorer AS
SELECT
    s.id AS sale_id,
    s.created_at,
    s.total_amount,
    s.production_seconds,
    s.delivery_seconds,
    s.customer_id,
   
   	s.total_amount_items,
    s.total_discount,
    s.delivery_fee,
    s.service_tax_fee,
   
   	st.id AS store_id,
    st.name AS store_name,
    ch.id AS channel_id,
    ch.name AS channel_name,
    
    p.id AS product_id,
    p.name AS product_name,
    c.id AS category_id,
    c.name AS category_name,
    
    ps.quantity,
    ps.total_price AS product_total_price,
    
    EXTRACT(ISODOW FROM s.created_at) AS dia_semana_num,
    CASE EXTRACT(ISODOW FROM s.created_at)
        WHEN 1 THEN '1. Seg'
        WHEN 2 THEN '2. Ter'
        WHEN 3 THEN '3. Qua'
        WHEN 4 THEN '4. Qui'
        WHEN 5 THEN '5. Sex'
        WHEN 6 THEN '6. Sab'
        WHEN 7 THEN '7. Dom'
    END AS dia_semana_nome,
    EXTRACT(HOUR FROM s.created_at) AS hora_dia
    
FROM sales s
JOIN stores st ON s.store_id = st.id
JOIN channels ch ON s.channel_id = ch.id
LEFT JOIN product_sales ps ON s.id = ps.sale_id
LEFT JOIN products p ON ps.product_id = p.id
LEFT JOIN categories c ON p.category_id = c.id;

CREATE OR REPLACE FUNCTION get_rfm_analysis(data_ref date)
RETURNS TABLE (
    id integer,
    customer_name varchar,
    phone_number varchar,
    email varchar,
    frequencia bigint,
    valor_total decimal(10,2),
    ultima_compra timestamp,
    dias_sem_comprar integer
)
LANGUAGE sql
AS $$
    WITH rfm AS (
        SELECT
            customer_id,
            COUNT(id) AS frequencia_calc,
            SUM(total_amount) AS valor_total_calc,
            MAX(created_at) AS ultima_compra_calc,
            (data_ref - MAX(created_at)::date) AS dias_sem_comprar_calc
        FROM sales
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
    )
    SELECT
        c.id,
        COALESCE(c.customer_name, 'Cliente Desconhecido') AS customer_name,
        c.phone_number,
        c.email,
        r.frequencia_calc,
        r.valor_total_calc,
        r.ultima_compra_calc,
        r.dias_sem_comprar_calc
    FROM rfm r
    LEFT JOIN customers c ON r.customer_id = c.id
    ORDER BY r.frequencia_calc DESC;
$$;