import streamlit as st
import pandas as pd
import sqlalchemy
import plotly.express as px
from datetime import datetime, timedelta
import queries  

@st.cache_data
def convert_df_to_csv(df):
    """
    Função em cache para converter o DataFrame para CSV em memória,
    pronto para download.
    'utf-8-sig' garante que o Excel leia a acentuação (ex: 'Categoria') corretamente.
    """
    return df.to_csv(index=True, encoding='utf-8-sig').encode('utf-8-sig')

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
df_explorer = df_analysis_filt.dropna(subset=['product_id'])

st.title("Análise Detalhada (Explorer)")

if df_explorer.empty:
    st.warning("Nenhum dado de produto para analisar com os filtros atuais.")
else:
    st.header("Construa sua própria análise")
    st.write("Use esta página para análisar seus tickets médios ou para ver como estão as vendas dos produtos")

    st.subheader("Controles da Análise")
    
    col1, col2, col3 = st.columns(3)
    
    dimensao_map = {
        "Produtos": "product_name",
        "Categoria": "category_name",
        "Loja": "store_name",
        "Canal": "channel_name",
        "Dia da Semana": "dia_semana_nome",
        "Hora do Dia": "hora_dia"
    }
    
    metrica_map = {
        "Faturamento Total": "product_total_price",
        "Nº de Pedidos (únicos)": "sale_id",
        "Quantidade Vendida": "quantity",
        "Ticket Médio": "ticket_medio"
    }
    
    agg_map = {
        "Faturamento Total": "sum",
        "Nº de Pedidos (únicos)": "nunique",
        "Quantidade Vendida": "sum"
    }

    dimensao_selec = col1.selectbox("Agrupar por (Dimensão)", options=list(dimensao_map.keys()))
    metrica_selec = col2.selectbox("Calcular Métrica (Valor)", options=list(metrica_map.keys()))
    segment_selec = col3.selectbox("Segmentar por (Opcional)", options=["Nenhum"] + list(dimensao_map.keys()))

    sort_order = "Maiores Valores (Top N)"
    n_items = 10
    
    if segment_selec == "Nenhum":
        st.write("")
        col4, col5 = st.columns(2)
        sort_order = col4.radio(
            "Ordenar por",
            ["Maiores Valores", "Menores Valores"],
            horizontal=True,
            key="sort_order"
        )
        n_items = col5.number_input(
            "Número de itens no gráfico",
            min_value=5,
            max_value=100,
            value=10,
            step=5,
            key="n_items"
        )
    
    st.subheader(f"Resultado: {metrica_selec} por {dimensao_selec}" + (f" segmentado por {segment_selec}" if segment_selec != "Nenhum" else ""))

    analysis_df = pd.DataFrame() 

    try:
        dim_col = dimensao_map[dimensao_selec]
        seg_col = dimensao_map.get(segment_selec)
        
        if metrica_selec == "Ticket Médio":
            val_col = 'ticket_medio'
            group_by_cols = [dim_col]
            if seg_col and dim_col != seg_col:
                group_by_cols.append(seg_col)
            elif dim_col == seg_col:
                st.error("Por favor, selecione uma Dimensão e Segmentação diferentes.")
                st.stop()
            
            grouped = df_sales_filt.groupby(group_by_cols)
            analysis_df = grouped.agg(
                Faturamento=('total_amount', 'sum'),
                Pedidos=('sale_id', 'nunique')
            )
            analysis_df[val_col] = (analysis_df['Faturamento'] / analysis_df['Pedidos']).fillna(0)

            if seg_col:
                analysis_df = analysis_df[val_col].unstack(level=-1).fillna(0)
            else:
                
                is_ascending = (sort_order == "Menores Valores")
                analysis_df = analysis_df[[val_col]].sort_values(by=val_col, ascending=is_ascending)
        else:
            val_col = metrica_map[metrica_selec]
            agg_func = agg_map[metrica_selec]
            
            if segment_selec == "Nenhum":
                analysis_df = df_explorer.groupby(dim_col)[val_col].agg(agg_func).reset_index()
                is_ascending = (sort_order == "Menores Valores")
                analysis_df = analysis_df.sort_values(by=val_col, ascending=is_ascending)
            else:
                if dim_col == seg_col:
                    st.error("Por favor, selecione uma Dimensão e Segmentação diferentes.")
                    st.stop()
                analysis_df = df_explorer.pivot_table(
                    index=dim_col,
                    columns=seg_col,
                    values=val_col,
                    aggfunc=agg_func
                ).fillna(0)
            
        if segment_selec == "Nenhum":
            sort_title_prefix = "Top" if sort_order == "Maiores Valores" else "Piores"
            chart_title = f"{sort_title_prefix} {n_items} {dimensao_selec} por {metrica_selec}"
            plot_df = analysis_df.head(n_items)
        else:
            chart_title = f"{metrica_selec} por {dimensao_selec} e {segment_selec} (Top 20 linhas)"
            plot_df = analysis_df.head(20) 

        st.write(f"Gráfico: {chart_title}")
        
        if segment_selec == "Nenhum":
            fig = px.bar(
                plot_df, 
                x=dim_col,
                y=val_col,
                title=chart_title,
                labels={dim_col: dimensao_selec, val_col: metrica_selec}
            )
        else:
            fig = px.bar(
                plot_df,
                title=chart_title,
                labels={'value': metrica_selec, 'index': dimensao_selec}
            )
        
        st.plotly_chart(fig, width="stretch")

        st.subheader("Tabela de Dados (Completa e Ordenada)")
        st.dataframe(analysis_df)

        if not analysis_df.empty:
            st.markdown("---") 
            csv_data = convert_df_to_csv(analysis_df)
            filename = f"relatorio_explorer_{dimensao_selec}_{metrica_selec}.csv"
            
            st.download_button(
                label="Gerar Relatório (Download CSV)",
                data=csv_data,
                file_name=filename,
                mime='text/csv',
                width='stretch'
            )

    except Exception as e:
        st.error(f"Não foi possível gerar a análise. Verifique suas seleções. Erro: {e}")