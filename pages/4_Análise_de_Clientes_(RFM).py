import streamlit as st
import pandas as pd
import sqlalchemy
import plotly.express as px
from datetime import datetime, timedelta
import queries  

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

        query_params_ids = {"sales_ids": sales_ids}
        df_payments = pd.read_sql(queries.SELECT_PAYMENTS, conn, params=query_params_ids)

    return df_analysis_data, df_payments

@st.cache_data(ttl=600, show_spinner="Analisando comportamento dos clientes...")
def carregar_dados_rfm(data_referencia):
    query_params = {"data_ref": data_referencia}
    with engine.connect() as conn:
        df = pd.read_sql(queries.SELECT_RFM, conn, params=query_params)
    return df

df_stores, df_channels, df_payment_types = carregar_tabelas_dimensao()

st.sidebar.header("Filtros Globais")
st.sidebar.write("Estes filtros afetam **todas** as páginas.")

default_start = datetime.now().date() - timedelta(days=30)
default_end = datetime.now().date()
date_range = st.sidebar.date_input(
    "Selecione o Período",
    (default_start, default_end),
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

st.title("🫂 Análise de Clientes (RFM)")
st.write("Responde à dor: *'Quais clientes compraram 3+ vezes mas não voltam há 30 dias?'*")
st.info(f"A análise usa **{end_date.strftime('%d/%m/%Y')}** (data final do filtro) como referência para calcular os 'dias sem comprar'.")


df_rfm = carregar_dados_rfm(end_date)

if df_rfm.empty:
    st.warning("Nenhum dado de cliente encontrado.")
else:
    st.header("Filtros da Análise RFM")
    col1, col2 = st.columns(2)
    
    
    min_freq = col1.number_input(
        "Mínimo de Pedidos (Frequência)", 
        min_value=1, 
        value=3
    )
    min_rec = col2.number_input(
        "Mínimo de Dias Sem Comprar (Recência)", 
        min_value=0, 
        value=30
    )

    
    df_rfm_filtrado = df_rfm[
        (df_rfm['frequencia'] >= min_freq) &
        (df_rfm['dias_sem_comprar'] >= min_rec)
    ]

    st.header(f"Resultados: Clientes Encontrados")
    st.metric(
        f"Clientes com {min_freq}+ pedidos que não compram há {min_rec}+ dias",
        f"{len(df_rfm_filtrado)} clientes"
    )
    
    st.dataframe(df_rfm_filtrado)