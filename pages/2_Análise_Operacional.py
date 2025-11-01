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

        sql_payments_query = f"SELECT sale_id, payment_type_id, value FROM payments WHERE sale_id IN {sales_ids}"
        df_payments = pd.read_sql(sql_payments_query, conn)
    
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
st.title("Análise Operacional")

if df_sales_filt.empty:
    st.warning("Nenhum dado operacional para exibir com os filtros atuais.")
else:
    st.header("Análise de Tempos (Preparo e Entrega)")
    st.write("Use esta página para entender como estão seus pedidos em determinados horários/dias*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Tempo Médio de Preparo por Dia")
        df_time_prod = df_sales_filt.groupby('created_at_date')['production_seconds'].mean().reset_index()
        df_time_prod['tempo_min'] = df_time_prod['production_seconds'] / 60
        fig_prod = px.line(
            df_time_prod, x='created_at_date', y='tempo_min',
            title="Tempo Médio de Preparo (min)",
            labels={'created_at_date': 'Data', 'tempo_min': 'Minutos'}
        )
        st.plotly_chart(fig_prod, width="stretch")

    with col2:
        st.subheader("Tempo Médio de Entrega por Dia")
        df_time_del = df_sales_filt.groupby('created_at_date')['delivery_seconds'].mean().reset_index()
        df_time_del['tempo_min'] = df_time_del['delivery_seconds'] / 60
        fig_del = px.line(
            df_time_del, x='created_at_date', y='tempo_min',
            title="Tempo Médio de Entrega (min)",
            labels={'created_at_date': 'Data', 'tempo_min': 'Minutos'},
            color_discrete_sequence=['red']
        )
        st.plotly_chart(fig_del, width="stretch")

    st.markdown("---")
    st.header("Mapa de Calor: Gargalos Operacionais")
    st.write("Encontre os piores horários e dias da semana.")
    
    metric_map = st.selectbox(
        "Selecione a Métrica para o Mapa de Calor",
        ["Tempo de Preparo (seg)", "Tempo de Entrega (seg)", "Nº de Pedidos"]
    )
    
    if metric_map == "Tempo de Preparo (seg)":
        value_col = 'production_seconds'
        agg_func = 'mean'
    elif metric_map == "Tempo de Entrega (seg)":
        value_col = 'delivery_seconds'
        agg_func = 'mean'
    else:
        value_col = 'sale_id'
        agg_func = 'nunique'

    heatmap_data = df_sales_filt.pivot_table(
        index='dia_semana_nome',
        columns='hora_dia',
        values=value_col,
        aggfunc=agg_func
    ).fillna(0)
    
    if not heatmap_data.empty:
        heatmap_data = heatmap_data.reindex(index=['1. Seg', '2. Ter', '3. Qua', '4. Qui', '5. Sex', '6. Sab', '7. Dom'])
        fig_heatmap = px.imshow(
            heatmap_data,
            title=f"Mapa de Calor: {metric_map} por Dia da Semana e Hora do Dia",
            labels={'x': 'Hora do Dia', 'y': 'Dia da Semana', 'color': 'Valor'},
            aspect="auto" 
        )
        st.plotly_chart(fig_heatmap, width="stretch")
    else:
        st.info("Nenhum dado para o Mapa de Calor.")