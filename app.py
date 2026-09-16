import os
import sys
from pathlib import Path

# Garante a resolução dos caminhos do repositório
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página (primeiro comando visual do Streamlit)
st.set_page_config(
    page_title="Market Cost Analyzer | Nutrição Animal",
    page_icon="🌾",
    layout="wide"
)

# Imports tolerantes para carregar os módulos em qualquer layout de pastas
try:
    from src.integrations.market_apis import MarketDataService
except ModuleNotFoundError:
    try:
        from src.market_apis import MarketDataService
    except ModuleNotFoundError:
        from market_apis import MarketDataService

try:
    from src.calculations.cost_engine import FeedCostEngine
except ModuleNotFoundError:
    try:
        from src.cost_engine import FeedCostEngine
    except ModuleNotFoundError:
        from cost_engine import FeedCostEngine

try:
    from src.config import COMMODITY_TICKERS
except ModuleNotFoundError:
    try:
        from config import COMMODITY_TICKERS
    except ModuleNotFoundError:
        COMMODITY_TICKERS = {
            "Milho B3": "CCM=F",
            "Petróleo Brent": "BZ=F",
        }

# Header da aplicação
st.title("🌾 Market Cost Analyzer — Nutrição Animal")
st.caption("Painel automatizado de monitoramento de mercado e custos de formulação")

# Cache para requisições de mercado
@st.cache_data(ttl=600, show_spinner="Atualizando cotações de mercado...")
def fetch_indicators():
    currencies = MarketDataService.get_currency_rates()
    commodities = {}
    for name, ticker in COMMODITY_TICKERS.items():
        try:
            df = MarketDataService.get_commodity_history(ticker, period="1mo")
            commodities[name] = df
        except Exception:
            commodities[name] = pd.DataFrame()
    return currencies, commodities

# Carga com fallback para garantir inicialização sem falhas
try:
    currencies, commodities = fetch_indicators()
except Exception:
    currencies = {"usd_rate": 5.45, "usd_pct": 0.0, "eur_rate": 5.95, "eur_pct": 0.0, "timestamp": "Offline (Padrão)"}
    commodities = {}

# KPIs de Mercado
col1, col2, col3, col4 = st.columns(4)

usd_val = currencies.get("usd_rate", 5.45)
usd_pct = currencies.get("usd_pct", 0.0)
eur_val = currencies.get("eur_rate", 5.95)
eur_pct = currencies.get("eur_pct", 0.0)

col1.metric("Dólar Comercial (USD)", f"R$ {usd_val:.4f}", f"{usd_pct:.2f}%")
col2.metric("Euro Comercial (EUR)", f"R$ {eur_val:.4f}", f"{eur_pct:.2f}%")

# Milho B3
milho_df = commodities.get("Milho B3", pd.DataFrame())
if isinstance(milho_df, pd.DataFrame) and not milho_df.empty and "Close" in milho_df.columns:
    last_close = milho_df["Close"].iloc[-1]
    prev_close = milho_df["Close"].iloc[-2] if len(milho_df) > 1 else last_close
    delta = ((last_close - prev_close) / prev_close) * 100
    col3.metric("Milho B3 (CCM=F)", f"R$ {last_close:.2f}", f"{delta:.2f}%")
else:
    col3.metric("Milho B3 (CCM=F)", "R$ 62.50", "Ref. Spot")

# Petróleo Brent
brent_df = commodities.get("Petróleo Brent", pd.DataFrame())
if isinstance(brent_df, pd.DataFrame) and not brent_df.empty and "Close" in brent_df.columns:
    last_brent = brent_df["Close"].iloc[-1]
    col4.metric("Petróleo Brent", f"US$ {last_brent:.2f}")
else:
    col4.metric("Petróleo Brent", "US$ 78.00", "Ref. Spot")

st.divider()

# Barra Lateral: Parâmetros Operacionais
st.sidebar.header("⚙️ Parâmetros Operacionais")
freight_inbound = st.sidebar.number_input("Frete Inbound Médio (R$/ton)", min_value=0.0, value=85.0, step=5.0)
packaging_loss = st.sidebar.slider("Perda Operacional Ensaque (%)", min_value=0.0, max_value=5.0, value=0.8, step=0.1)
cif_industrial = st.sidebar.number_input("GGF / CIF Industrial (R$/ton)", min_value=0.0, value=110.0, step=10.0)

# Ficha Técnica Padrão
st.subheader("📋 Simulação de Custo por Ficha Técnica")
st.write("Edite as matérias-primas e percentuais de inclusão abaixo:")

default_recipe = pd.DataFrame([
    {"ingrediente": "Milho Moído", "inclusao_pct": 58.0, "preco_base_kg": 1.15, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Farelo de Soja 46%", "inclusao_pct": 28.0, "preco_base_kg": 2.10, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Farinha de Carne e Ossos", "inclusao_pct": 5.0, "preco_base_kg": 1.85, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Óleo Vegetal Degomado", "inclusao_pct": 2.5, "preco_base_kg": 4.80, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Premix Vitamínico/Mineral", "inclusao_pct": 4.0, "preco_base_kg": 14.50, "moeda": "BRL", "custo_embalagem_ton": 35.0},
    {"ingrediente": "Aminoácidos Essenciais (USD)", "inclusao_pct": 2.5, "preco_base_kg": 4.20, "moeda": "USD", "custo_embalagem_ton": 35.0},
])

edited_df = st.data_editor(
    default_recipe,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "ingrediente": "Ingrediente",
        "inclusao_pct": st.column_config.NumberColumn("Inclusão (%)", min_value=0.0, max_value=100.0, step=0.5),
        "preco_base_kg": st.column_config.NumberColumn("Preço Base (R$/kg)", min_value=0.0, format="R$ %.3f"),
        "moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"]),
        "custo_embalagem_ton": st.column_config.NumberColumn("Embalagem (R$/ton)", min_value=0.0, format="R$ %.2f"),
    }
)

# Validação do Fechamento de Fórmula
total_pct = edited_df["inclusao_pct"].sum()
if abs(total_pct - 100.0) > 0.01:
    st.warning(f"⚠️ A soma da inclusão está em **{total_pct:.1f}%**. O fechamento padrão de fórmula é 100.0%.")

# Cálculo do Custo Unitário
result = FeedCostEngine.calculate_batch_cost(
    edited_df,
    usd_rate=usd_val,
    freight_per_ton=freight_inbound,
    packaging_loss_pct=packaging_loss,
    cif_industrial_per_ton=cif_industrial
)

# Exibição dos Resultados
st.markdown("### 📊 Síntese de Custos")
res1, res2, res3 = st.columns(3)
res1.metric("Custo Total / Tonelada", f"R$ {result['custo_total_ton']:,.2f}")
res2.metric("Custo Saca 40 kg", f"R$ {result['custo_saca_40kg']:,.2f}")
res3.metric("Custo Saca 25 kg", f"R$ {result['custo_saca_25kg']:,.2f}")

# Gráfico de Distribuição do Custo de Matérias-Primas
fig = px.pie(
    result["breakdown_df"],
    names="ingrediente",
    values="custo_ingrediente_ton",
    title="Composição do Custo de Matéria-Prima por Tonelada",
    hole=0.4
)
st.plotly_chart(fig, use_container_width=True)
