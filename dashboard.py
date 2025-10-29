import streamlit as st
import pandas as pd
import sqlalchemy
import plotly.express as px
from datetime import datetime, timedelta


st.set_page_config(
    page_title="Dashboard Restaurante",
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

@st.cache_data(ttl=600, show_spinner="Carregando tabelas principais...")
def carregar_tabelas_dimensao():
    with engine.connect() as conn:
        df_stores = pd.read_sql("SELECT id, name FROM stores WHERE is_active = true", conn)
        df_channels = pd.read_sql("SELECT id, name FROM channels", conn)
        df_products = pd.read_sql("SELECT id, name, category_id FROM products", conn)
        df_categories = pd.read_sql("SELECT id, name FROM categories", conn)
        df_payment_types = pd.read_sql("SELECT id, description FROM payment_types", conn)
    
    
    df_stores.columns = ['store_id', 'store_name']
    df_channels.columns = ['channel_id', 'channel_name']
    df_products.columns = ['product_id', 'product_name', 'category_id']
    df_categories.columns = ['category_id', 'category_name']
    df_payment_types.columns = ['payment_type_id', 'payment_description']
    
    return df_stores, df_channels, df_products, df_categories, df_payment_types

@st.cache_data(ttl=600, show_spinner="Carregando dados de vendas...")
def carregar_dados_fato(start_date, end_date):
    """Carrega as tabelas de fatos (grandes) filtradas por data."""
    end_date_sql = end_date + timedelta(days=1)
    query_params = {"start": start_date, "end": end_date_sql}
    
    with engine.connect() as conn:
        
        sql_sales = """
        SELECT 
            id, store_id, channel_id, customer_id, created_at, 
            total_amount, total_discount, production_seconds, delivery_seconds,
            EXTRACT(ISODOW FROM created_at) AS dia_semana_num,
            EXTRACT(HOUR FROM created_at) AS hora_dia
        FROM sales 
        WHERE created_at >= %(start)s AND created_at < %(end)s
        """
        df_sales = pd.read_sql(sql_sales, conn, params=query_params)
        
        if df_sales.empty:
            return df_sales, pd.DataFrame(), pd.DataFrame(), pd.DataFrame() 
        
        sales_ids = tuple(df_sales['id'].tolist())
        if len(sales_ids) == 1:
            sales_ids = f"({sales_ids[0]})" 

        query_params_ids = {"sales_ids": sales_ids}

        sql_prod_sales = "SELECT sale_id, product_id, quantity, total_price FROM product_sales WHERE sale_id IN %(sales_ids)s"
        sql_payments = "SELECT sale_id, payment_type_id, value FROM payments WHERE sale_id IN %(sales_ids)s"
        
        df_product_sales = pd.read_sql(sql_prod_sales, conn, params=query_params_ids)
        df_payments = pd.read_sql(sql_payments, conn, params=query_params_ids)
        
        
        dias_semana_map = {
            1: '1. Seg', 2: '2. Ter', 3: '3. Qua', 4: '4. Qui', 
            5: '5. Sex', 6: '6. Sab', 7: '7. Dom'
        }
        df_sales['dia_semana_nome'] = df_sales['dia_semana_num'].map(dias_semana_map)
        
    return df_sales, df_product_sales, df_payments


df_stores, df_channels, df_products, df_categories, df_payment_types = carregar_tabelas_dimensao()



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


st.sidebar.markdown("---")
st.sidebar.header("Navegação")
pagina_selecionada = st.sidebar.radio(
    "Selecione a Análise",
    ["Visão Geral", "Análise Operacional", "Análise Detalhada (Explorer)"]
)
st.sidebar.markdown("---")


df_sales, df_product_sales, df_payments = carregar_dados_fato(start_date, end_date)

if df_sales.empty:
    st.warning("Nenhum dado de venda encontrado para o período selecionado.")
    st.stop()


df_sales_merged = df_sales.merge(df_stores, on='store_id')
df_sales_merged = df_sales_merged.merge(df_channels, on='channel_id')
df_sales_merged['created_at_date'] = pd.to_datetime(df_sales_merged['created_at']).dt.date

if "Todas as Lojas" not in selected_store_names:
    df_sales_merged = df_sales_merged[df_sales_merged['store_name'].isin(selected_store_names)]
if "Todos os Canais" not in selected_channel_names:
    df_sales_merged = df_sales_merged[df_sales_merged['channel_name'].isin(selected_channel_names)]

df_sales_filt = df_sales_merged
if df_sales_filt.empty:
    st.warning("Nenhum dado encontrado para os filtros globais aplicados.")
    st.stop()


sales_ids_filt = df_sales_filt['id'].tolist()
df_product_sales_filt = df_product_sales[df_product_sales['sale_id'].isin(sales_ids_filt)]
df_payments_filt = df_payments[df_payments['sale_id'].isin(sales_ids_filt)]


if pagina_selecionada == "Visão Geral":
    st.title("Dashboard de Vendas (Visão Geral)")
    st.header("Visão Geral")

    total_revenue = df_sales_filt['total_amount'].sum()
    total_sales = df_sales_filt['id'].nunique()
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
        st.plotly_chart(fig_time, use_container_width=True)

    with col_graf2:
        st.subheader("Vendas por Canal")
        df_sales_by_channel = df_sales_filt.groupby('channel_name')['total_amount'].sum().reset_index()
        fig_channel = px.pie(
            df_sales_by_channel, names='channel_name', values='total_amount',
            title="Distribuição do Faturamento por Canal"
        )
        st.plotly_chart(fig_channel, use_container_width=True)

    col_graf3, col_graf4 = st.columns(2)

    with col_graf3:
        st.subheader("Top 10 Produtos (por Faturamento)")
        df_prods_merged = df_product_sales_filt.merge(df_products, on='product_id')
        df_top_products = df_prods_merged.groupby('product_name')['total_price'].sum().nlargest(10).reset_index()
        
        fig_top_prods = px.bar(
            df_top_products.sort_values(by='total_price', ascending=True),
            x='total_price', y='product_name', orientation='h', title="Top 10 Produtos",
            labels={'product_name': 'Produto', 'total_price': 'Faturamento Total'}
        )
        st.plotly_chart(fig_top_prods, use_container_width=True)

    with col_graf4:
        st.subheader("Faturamento por Forma de Pagamento")
        df_pay_merged = df_payments_filt.merge(df_payment_types, on='payment_type_id')
        df_sales_by_payment = df_pay_merged.groupby('payment_description')['value'].sum().reset_index()
        
        fig_payments = px.pie(
            df_sales_by_payment, names='payment_description', values='value',
            title="Distribuição por Forma de Pagamento"
        )
        st.plotly_chart(fig_payments, use_container_width=True)


elif pagina_selecionada == "Análise Operacional":
    st.title("⏱️ Análise Operacional")
    st.header("Análise de Tempos (Preparo e Entrega)")
    st.write("Responde à dor: *'Meu tempo de entrega piorou. Em quais dias/horários?'*")
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
        st.plotly_chart(fig_prod, use_container_width=True)

    
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
        st.plotly_chart(fig_del, use_container_width=True)

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
        value_col = 'id'
        agg_func = 'count'

    
    heatmap_data = df_sales_filt.pivot_table(
        index='dia_semana_nome',
        columns='hora_dia',
        values=value_col,
        aggfunc=agg_func
    ).fillna(0)
    
    
    heatmap_data = heatmap_data.reindex(index=['1. Seg', '2. Ter', '3. Qua', '4. Qui', '5. Sex', '6. Sab', '7. Dom'])

    fig_heatmap = px.imshow(
        heatmap_data,
        title=f"Mapa de Calor: {metric_map} por Dia da Semana e Hora do Dia",
        labels={'x': 'Hora do Dia', 'y': 'Dia da Semana', 'color': 'Valor'},
        aspect="auto" 
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)



elif pagina_selecionada == "Análise Detalhada (Explorer)":
    st.title("🔬 Análise Detalhada (Explorer)")
    st.header("Construa sua própria análise")
    st.write("""
    Responde à dor: *'Qual produto vende mais na quinta à noite no iFood?'*
    Use os **Filtros Globais** na barra lateral para filtrar o período, lojas ou canais.
    Depois, agrupe os dados como desejar abaixo.
    """)

    
    df_explorer = df_product_sales_filt.merge(df_products, on='product_id', how='left')
    df_explorer = df_explorer.merge(df_categories, on='category_id', how='left')
    
    
    df_explorer = df_explorer.merge(
        df_sales_filt[['id', 'store_name', 'channel_name', 'dia_semana_nome', 'hora_dia']],
        left_on='sale_id',
        right_on='id',
        how='left'
    )

    
    st.subheader("Controles da Análise")
    col1, col2, col3 = st.columns(3)
    
    dimensao_map = {
        "Produto": "product_name",
        "Categoria": "category_name",
        "Loja": "store_name",
        "Canal": "channel_name",
        "Dia da Semana": "dia_semana_nome",
        "Hora do Dia": "hora_dia"
    }
    
    metrica_map = {
        "Faturamento Total": "total_price",
        "Nº de Pedidos (únicos)": "sale_id",
        "Quantidade Vendida": "quantity"
    }
    
    agg_map = {
        "Faturamento Total": "sum",
        "Nº de Pedidos (únicos)": "nunique",
        "Quantidade Vendida": "sum"
    }

    
    dimensao_selec = col1.selectbox(
        "Agrupar por (Dimensão)",
        options=list(dimensao_map.keys())
    )
    
    
    metrica_selec = col2.selectbox(
        "Calcular Métrica (Valor)",
        options=list(metrica_map.keys())
    )
    
    
    segment_selec = col3.selectbox(
        "Segmentar por (Opcional)",
        options=["Nenhum"] + list(dimensao_map.keys())
    )

    
    st.subheader(f"Resultado: {metrica_selec} por {dimensao_selec}" + (f" segmentado por {segment_selec}" if segment_selec != "Nenhum" else ""))

    try:
        dim_col = dimensao_map[dimensao_selec]
        val_col = metrica_map[metrica_selec]
        agg_func = agg_map[metrica_selec]

        if segment_selec == "Nenhum":
            
            analysis_df = df_explorer.groupby(dim_col)[val_col].agg(agg_func).reset_index()
            analysis_df = analysis_df.sort_values(by=val_col, ascending=False)
            
            
            fig = px.bar(
                analysis_df.head(20), 
                x=dim_col,
                y=val_col,
                title=f"Top 20 {dimensao_selec} por {metrica_selec}",
                labels={dim_col: dimensao_selec, val_col: metrica_selec}
            )
            st.plotly_chart(fig, width=True)
            
        else:
            seg_col = dimensao_map[segment_selec]
            
            if dim_col == seg_col:
                st.error("Por favor, selecione uma Dimensão e Segmentação diferentes.")
                st.stop()
            
            analysis_df = df_explorer.pivot_table(
                index=dim_col,
                columns=seg_col,
                values=val_col,
                aggfunc=agg_func
            ).fillna(0)
            
            
            st.write("Gráfico (Top 20 linhas)")
            fig = px.bar(
                analysis_df.head(20),
                title=f"{metrica_selec} por {dimensao_selec} e {segment_selec}",
                labels={'value': metrica_selec}
            )
            st.plotly_chart(fig, use_container_width=True)

        
        st.subheader("Tabela de Dados")
        st.dataframe(analysis_df)

    except Exception as e:
        st.error(f"Não foi possível gerar a análise. Verifique suas seleções. Erro: {e}")