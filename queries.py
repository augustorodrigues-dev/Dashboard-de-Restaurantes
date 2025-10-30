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
SELECT_ANALYSIS_DATA = """
    SELECT * FROM v_analysis_explorer
    WHERE created_at >= %(start)s AND created_at < %(end)s
"""

SELECT_DATE_LIMITS = """
    SELECT MIN(created_at)::date as min_date, MAX(created_at)::date as max_date 
    FROM sales
"""

SELECT_PAYMENTS = """
    SELECT sale_id, payment_type_id, value 
    FROM payments 
    WHERE sale_id IN %(sales_ids)s
"""
SELECT_RFM = """
    SELECT * FROM get_rfm_analysis(%(data_ref)s)
"""
