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
    query_params = (start_date, end_date_sql)
    
    with engine.connect() as conn:
        df_analysis_data = pd.read_sql(queries.SELECT_ANALYSIS_DATA, conn, params=query_params)

        if df_analysis_data.empty:
            return pd.DataFrame(), pd.DataFrame()

        sales_ids_list = df_analysis_data['sale_id'].unique().tolist()
        sales_ids = tuple(sales_ids_list) 
        if not sales_ids:
            return df_analysis_data, pd.DataFrame()
        query_params_ids = (sales_ids,)
        df_payments = pd.read_sql(queries.SELECT_PAYMENTS, conn, params=query_params_ids)

    return df_analysis_data, df_payments

@st.cache_data(ttl=600, show_spinner="Analisando comportamento dos clientes...")
def carregar_dados_rfm(data_referencia):
    query_params = (data_referencia,)
    
    with engine.connect() as conn:
        df = pd.read_sql(queries.SELECT_RFM, conn, params=query_params)
    return df


min_date, max_date = carregar_limites_de_data()
df_stores, df_channels, df_payment_types = carregar_tabelas_dimensao()

st.sidebar.header("Filtros Globais")
st.sidebar.write("Estes filtros afetam **todas** as páginas.")

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



st.title("📉 Análise de Descontos e Taxas")
st.write("Entenda para onde está indo seu faturamento e quais canais custam mais caro.")

if df_sales_filt.empty:
    st.warning("Nenhum dado de venda para exibir com os filtros atuais.")
else:
    
    total_bruto = df_sales_filt['total_amount_items'].sum()
    total_descontos = df_sales_filt['total_discount'].sum()
    total_taxas_delivery = df_sales_filt['delivery_fee'].sum()
    total_taxas_servico = df_sales_filt['service_tax_fee'].sum()
    total_taxas = total_taxas_delivery + total_taxas_servico
    total_liquido = total_bruto - total_descontos - total_taxas

    
    perc_desconto = (total_descontos / total_bruto * 100) if total_bruto > 0 else 0
    perc_taxa = (total_taxas / total_bruto * 100) if total_bruto > 0 else 0

    st.header("Visão Geral Financeira (Líquida)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Faturamento Bruto (Itens)", f"R$ {total_bruto:,.2f}")
    col2.metric("Total de Descontos", f"R$ {total_descontos:,.2f}", 
                help=f"{perc_desconto:.1f}% do Bruto")
    col3.metric("Total de Taxas (Serviço/Entrega)", f"R$ {total_taxas:,.2f}",
                help=f"{perc_taxa:.1f}% do Bruto")
    
    st.subheader(f"Faturamento Líquido Estimado: R$ {total_liquido:,.2f}")
    st.progress((total_liquido / total_bruto) if total_bruto > 0 else 0)

    st.markdown("---")
    st.header("Análise Detalhada por Canal")
    st.write("Veja quais canais mais aplicam descontos ou cobram taxas.")

    
    df_canal = df_sales_filt.groupby('channel_name').agg(
        Faturamento_Bruto=('total_amount_items', 'sum'),
        Descontos=('total_discount', 'sum'),
        Taxas=('delivery_fee', 'sum'), 
        Pedidos=('sale_id', 'nunique')
    )
    df_canal['Desconto_por_Pedido'] = (df_canal['Descontos'] / df_canal['Pedidos']).fillna(0)
    
    
    fig_canal = px.bar(
        df_canal.sort_values(by='Descontos', ascending=False),
        y=['Faturamento_Bruto', 'Descontos', 'Taxas'],
        barmode='group',
        title="Faturamento Bruto vs. Descontos e Taxas por Canal",
        labels={'value': 'Valor (R$)', 'channel_name': 'Canal'}
    )
    st.plotly_chart(fig_canal, width="stretch")

    st.subheader("Desconto Médio por Pedido (por Canal)")
    df_canal_display = df_canal[['Desconto_por_Pedido', 'Pedidos']].sort_values(by='Desconto_por_Pedido', ascending=False)
    df_canal_display['Desconto_por_Pedido'] = df_canal_display['Desconto_por_Pedido'].map('R$ {:,.2f}'.format)
    st.dataframe(df_canal_display, use_container_width=True)