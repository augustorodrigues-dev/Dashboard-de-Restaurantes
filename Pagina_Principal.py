import streamlit as st
import pandas as pd
import sqlalchemy
import plotly.express as px
from datetime import datetime, timedelta
import queries  # Importa o novo arquivo de queries

st.set_page_config(
    page_title="Visão Geral | Dashboard Restaurante",
    page_icon="🍽️",
    layout="wide"
)


@st.cache_resource
def get_engine():
    try:
        conn_string = st.secrets["connections"]["neon_db"]
        engine = sqlalchemy.create_engine(conn_string)
        return engine
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        st.stop()

engine = get_engine()


@st.cache_data(ttl=3600)
def carregar_limites_de_data():
    with engine.connect() as conn:
        result = conn.execute(sqlalchemy.text(queries.SELECT_DATE_LIMITS)).fetchone()
    if result and result.min_date and result.max_date:
        return result.min_date, result.max_date
    fallback_start = datetime.now().date() - timedelta(days=30)
    fallback_end = datetime.now().date()
    return (fallback_start, fallback_end)

@st.cache_data(ttl=600, show_spinner="Carregando dimensões...")
def carregar_tabelas_dimensao():
    with engine.connect() as conn:
        df_stores = pd.read_sql(queries.SELECT_STORES, conn)
        df_channels = pd.read_sql(queries.SELECT_CHANNELS, conn)
        df_payment_types = pd.read_sql(queries.SELECT_PAYMENT_TYPES, conn)
    return df_stores, df_channels, df_payment_types

@st.cache_data(ttl=600, show_spinner="Carregando dados de vendas...")
def carregar_dados_fato_e_explorer(start_date, end_date):
    end_date_sql = end_date + timedelta(days=1)
    
    query_params = {"start": start_date, "end": end_date_sql}
    
    with engine.connect() as conn:
        
        df_analysis_data = pd.read_sql(queries.SELECT_ANALYSIS_DATA, conn, params=query_params)

        if df_analysis_data.empty:
            return pd.DataFrame(), pd.DataFrame()

        sales_ids_list = df_analysis_data['sale_id'].unique().tolist()
        sales_ids = tuple(sales_ids_list) 
        if not sales_ids:
            return df_analysis_data, pd.DataFrame()

        
        sql_payments_query = f"SELECT sale_id, payment_type_id, value FROM payments WHERE sale_id IN {sales_ids}"
        
        
        df_payments = pd.read_sql(sql_payments_query, conn)

    return df_analysis_data, df_payments

@st.cache_data(ttl=600, show_spinner="Analisando comportamento dos clientes...")
def carregar_dados_rfm(data_referencia):
    
    query_params = {"data_ref": data_referencia}
    
    with engine.connect() as conn:
        
        df = pd.read_sql(queries.SELECT_RFM, conn, params=query_params)
    return df


min_date, max_date = carregar_limites_de_data()
df_stores, df_channels, df_payment_types = carregar_tabelas_dimensao()

st.sidebar.header("Filtros Globais")
st.sidebar.write("Estes filtros afetam **todas** as páginas do dashboard.")

default_start = max(min_date, max_date - timedelta(days=30))
default_end = max_date

date_range = st.sidebar.date_input(
    "Selecione o Período",
    (default_start, default_end),
    min_value=min_date,
    max_value=max_date,
    format="DD/MM/YYYY"
)
if len(date_range) != 2:
    st.sidebar.error("Por favor, selecione um período de início e fim.")
    st.stop()
start_date, end_date = date_range

store_options = ["Todas as Lojas"] + df_stores['store_name'].tolist()
selected_store_names = st.sidebar.multiselect(
    "Selecione as Lojas",
    options=store_options,
    default=["Todas as Lojas"]
)

channel_options = ["Todos os Canais"] + df_channels['channel_name'].tolist()
selected_channel_names = st.sidebar.multiselect(
    "Selecione os Canais",
    options=channel_options,
    default=["Todos os Canais"]
)

df_analysis_data, df_payments = carregar_dados_fato_e_explorer(start_date, end_date)

if not df_analysis_data.empty:
    df_analysis_data['created_at_date'] = pd.to_datetime(df_analysis_data['created_at']).dt.date
else:
    st.info("Nenhum dado de venda encontrado para o período selecionado.")

df_analysis_filt = df_analysis_data.copy()
if "Todas as Lojas" not in selected_store_names:
    df_analysis_filt = df_analysis_filt[df_analysis_filt['store_name'].isin(selected_store_names)]
if "Todos os Canais" not in selected_channel_names:
    df_analysis_filt = df_analysis_filt[df_analysis_filt['channel_name'].isin(selected_channel_names)]

if df_analysis_filt.empty and not df_analysis_data.empty:
    st.warning("Nenhum dado encontrado para os filtros globais aplicados.")

df_sales_filt = df_analysis_filt.drop_duplicates(subset=['sale_id'])
df_explorer = df_analysis_filt.dropna(subset=['product_id'])
sales_ids_filt = df_sales_filt['sale_id'].tolist()
df_payments_filt = df_payments[df_payments['sale_id'].isin(sales_ids_filt)]

st.title("Seja bem-vinda, Maria")

if df_sales_filt.empty:
    st.warning("Nenhum dado de venda para exibir na Visão Geral com os filtros atuais.")
else:
    st.header("Visão Geral")
    total_revenue = df_sales_filt['total_amount'].sum()
    total_sales = df_sales_filt['sale_id'].nunique()
    avg_ticket = total_revenue / total_sales if total_sales > 0 else 0
    total_customers = df_sales_filt['customer_id'].nunique()
    avg_prod_sec = df_sales_filt['production_seconds'].mean()
    avg_del_sec = df_sales_filt['delivery_seconds'].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Faturamento Total", f"R$ {total_revenue:,.2f}")
    col2.metric("Total de Pedidos", f"{total_sales}")
    col3.metric("Ticket Médio", f"R$ {avg_ticket:,.2f}")
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Clientes Únicos", f"{total_customers}")
    col5.metric("Tempo Médio Preparo", f"{avg_prod_sec/60:,.1f} min" if avg_prod_sec else "N/A")
    col6.metric("Tempo Médio Entrega", f"{avg_del_sec/60:,.1f} min" if avg_del_sec else "N/A")

    st.markdown("---")
    st.header("Análises Detalhadas")
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.subheader("Vendas por Dia")
        df_sales_time = df_sales_filt.groupby('created_at_date')['total_amount'].sum().reset_index()
        fig_time = px.line(
            df_sales_time, x='created_at_date', y='total_amount',
            title="Faturamento ao Longo do Tempo",
            labels={'created_at_date': 'Data', 'total_amount': 'Faturamento'}
        )
        st.plotly_chart(fig_time, width="stretch")

    with col_graf2:
        st.subheader("Faturamento por Forma de Pagamento")
        df_pay_merged = df_payments_filt.merge(df_payment_types, on='payment_type_id')
        df_sales_by_payment = df_pay_merged.groupby('payment_description')['value'].sum().reset_index()
        fig_payments = px.pie(
            df_sales_by_payment, names='payment_description', values='value',
            title="Distribuição por Forma de Pagamento"
        )
        st.plotly_chart(fig_payments, width="stretch")

    
    st.markdown("---")
    st.header("Análise de Produtos")
    col_prod_1, col_prod_2 = st.columns(2)

    
    df_produtos_agrupados = df_explorer.groupby('product_name')['product_total_price'].sum()

    with col_prod_1:
        st.subheader("Top 10 Produtos (Maior Faturamento)")
        df_top_products = df_produtos_agrupados.nlargest(10).reset_index()
        
        fig_top_prods = px.bar(
            df_top_products.sort_values(by='product_total_price', ascending=True),
            x='product_total_price', y='product_name', orientation='h', title="Top 10 Produtos (Maior Faturamento)",
            labels={'product_name': 'Produto', 'product_total_price': 'Faturamento Total'}
        )
        st.plotly_chart(fig_top_prods, width="stretch")

    with col_prod_2:
        st.subheader("Top 10 Produtos (Menor Faturamento)")
        
        
        df_bottom_products = df_produtos_agrupados[df_produtos_agrupados > 0].nsmallest(10).reset_index()
        
        fig_bottom_prods = px.bar(
            df_bottom_products.sort_values(by='product_total_price', ascending=False), 
            x='product_total_price', y='product_name', orientation='h', title="Top 10 Produtos (Menor Faturamento)",
            labels={'product_name': 'Produto', 'product_total_price': 'Faturamento Total'},
            color_discrete_sequence=['#FF6347']
        )
        st.plotly_chart(fig_bottom_prods, width="stretch")