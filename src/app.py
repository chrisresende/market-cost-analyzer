import streamlit as st
import pandas as pd
import plotly.express as px

from src.config import COMMODITY_TICKERS
from src.integrations.market_apis import MarketDataService
from src.calculations.cost_engine import FeedCostEngine

# Configuração da página
st.set_page_config(
    page_title="Market Cost Analyzer | Nutrição Animal",
    page_icon="🌾",
    layout="wide"
)

# Cache de dados de mercado (15 minutos)
@st.cache_data(ttl=900)
def load_market_data():
    currencies = MarketDataService.get_currency_rates()
    commodities = {}
    for label, ticker in COMMODITY_TICKERS.items():
        commodities[label] = MarketDataService.get_commodity_history(ticker, period="1mo")
    return currencies, commodities

currencies, commodities = load_market_data()

# Header
st.title("🌾 Market Cost Analyzer — Nutrição Animal")
st.caption(f"Cotações automatizadas via APIs públicas | Última leitura: {currencies['timestamp']}")

# Linha de Indicadores de Mercado (KPIs)
col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Dólar Comercial (USD)",
    f"R$ {currencies['usd_rate']:.4f}",
    f"{currencies['usd_pct']:.2f}%"
)
col2.metric(
    "Euro Comercial (EUR)",
    f"R$ {currencies['eur_rate']:.4f}",
    f"{currencies['eur_pct']:.2f}%"
)

# Último fechamento de Milho B3
milho_df = commodities.get("Milho B3", pd.DataFrame())
if not milho_df.empty:
    last_close = milho_df["Close"].iloc[-1]
    prev_close = milho_df["Close"].iloc[-2] if len(milho_df) > 1 else last_close
    delta_milho = ((last_close - prev_close) / prev_close) * 100
    col3.metric("Milho B3 (CCM=F)", f"R$ {last_close:.2f}", f"{delta_milho:.2f}%")
else:
    col3.metric("Milho B3 (CCM=F)", "Indisponível", "0.0%")

# Último fechamento de Brent (Logística)
brent_df = commodities.get("Petróleo Brent (Logística)", pd.DataFrame())
if not brent_df.empty:
    last_brent = brent_df["Close"].iloc[-1]
    col4.metric("Petróleo Brent", f"US$ {last_brent:.2f}")
else:
    col4.metric("Petróleo Brent", "Indisponível")

st.divider()

# Layout Principal: Simulação de Formulação
st.subheader("Simulação de Custo Unitário por Fórmula")

sidebar = st.sidebar
sidebar.header("Parâmetros Operacionais")

freight_inbound = sidebar.number_input("Frete Inbound Médio (R$/ton)", min_value=0.0, value=85.0, step=5.0)
packaging_loss = sidebar.slider("Perda Operacional Ensaque (%)", min_value=0.0, max_value=5.0, value=0.8, step=0.1)
cif_industrial = sidebar.number_input("GGF / CIF Industrial (R$/ton)", min_value=0.0, value=110.0, step=10.0)

# Ficha Técnica Padrão de Exemplo (Ração Inicial Aves/Suínos)
default_recipe = pd.DataFrame([
    {"ingrediente": "Milho Moído", "inclusao_pct": 58.0, "preco_base_kg": 1.15, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Farelo de Soja 46%", "inclusao_pct": 28.0, "preco_base_kg": 2.10, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Farinha de Carne e Ossos", "inclusao_pct": 5.0, "preco_base_kg": 1.85, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Óleo de Degomado/Vegetal", "inclusao_pct": 2.5, "preco_base_kg": 4.80, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Premix Vitamínico/Mineral", "inclusao_pct": 4.0, "preco_base_kg": 14.50, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Aminoácidos Essenciais (USD)", "inclusao_pct": 2.5, "preco_base_kg": 4.20, "moeda": "USD", "custo_embalagem_ton": 35.0},
])

st.write("Edite os parâmetros da fórmula em tempo real:")
edited_df = st.data_editor(
    default_recipe,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "ingrediente": "Ingrediente",
        "inclusao_pct": st.column_config.NumberColumn("Inclusão (%)", min_value=0.0, max_value=100.0, step=0.5),
        "preco_base_kg": st.column_config.NumberColumn("Preço Base (por kg)", min_value=0.0, format="R$ %.3f"),
        "moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"]),
        "custo_embalagem_ton": st.column_config.NumberColumn("Embalagem (R$/ton)", min_value=0.0, format="R$ %.2f"),
    }
)

# Validação do Fechamento de Fórmula (100%)
total_inclusao = edited_df["inclusao_pct"].sum()
if abs(total_inclusao - 100.0) > 0.01:
    st.warning(f"Atenção: A inclusão total da fórmula está em **{total_inclusao:.1f}%** (o ideal é 100.0%).")

# Execução do Cálculo
result = FeedCostEngine.calculate_batch_cost(
    edited_df,
    usd_rate=currencies["usd_rate"],
    freight_per_ton=freight_inbound,
    packaging_loss_pct=packaging_loss,
    cif_industrial_per_ton=cif_industrial
)

# Exibição dos Resultados Finais
st.markdown("### Resultados de Custo Unitário")
res_col1, res_col2, res_col3 = st.columns(3)
res_col1.metric("Custo Final por Tonelada", f"R$ {result['custo_total_ton']:,.2f}")
res_col2.metric("Custo Saca 40 kg", f"R$ {result['custo_saca_40kg']:,.2f}")
res_col3.metric("Custo Saca 25 kg", f"R$ {result['custo_saca_25kg']:,.2f}")

# Gráfico de Pareto de Insumos
fig = px.pie(
    result["breakdown_df"],
    names="ingrediente",
    values="custo_ingrediente_ton",
    title="Composição de Custo por Ingrediente na Tonelada",
    hole=0.4
)
st.plotly_chart(fig, use_container_width=True)
