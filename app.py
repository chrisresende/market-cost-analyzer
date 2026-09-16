import io
import sqlite3
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import yfinance as yf

# 1. Configuração de Tela (Deve ser o primeiro comando Streamlit)
st.set_page_config(
    page_title="Market Cost Analyzer | Nutrição Animal",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# CAMADA DE DOMÍNIO: Dataclasses & Contratos
# =====================================================================
@dataclass
class MarketQuote:
    ticker: str
    name: str
    price: float
    change_pct: float
    currency: str = "BRL"
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RawMaterialItem:
    name: str
    inclusion_pct: float
    unit_price: float
    currency: str = "BRL"
    category: str = "Macro"

@dataclass
class ProductionParameters:
    freight_inbound_ton: float = 85.0
    packaging_cost_ton: float = 35.0
    packaging_loss_pct: float = 0.8
    industrial_cif_ton: float = 115.0
    moisture_loss_pct: float = 1.2

@dataclass
class CostBreakdownResult:
    total_cost_ton: float
    cost_bag_40kg: float
    cost_bag_25kg: float
    raw_material_cost_ton: float
    freight_total_ton: float
    packaging_total_ton: float
    industrial_cif_ton: float
    process_loss_cost_ton: float
    items_breakdown: List[dict]

# =====================================================================
# CAMADA DE ENGENHARIA DE DADOS: Repositório SQLite Local
# =====================================================================
class MarketRepository:
    def __init__(self, db_path: str = "market_history.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, ticker)
                )
            """)
            conn.commit()

    def save_quote(self, ticker: str, name: str, price: float, currency: str = "BRL"):
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO market_quotes (date, ticker, name, price, currency)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(date, ticker) DO UPDATE SET price=excluded.price
                """, (today, ticker, name, price, currency))
                conn.commit()
        except Exception:
            pass

# =====================================================================
# CAMADA DE SERVIÇOS: Coleta com Resiliência e Fallback
# =====================================================================
class ResilientMarketCollector:
    def __init__(self, repo: MarketRepository):
        self.repo = repo

    def get_currencies(self) -> dict:
        url = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL"
        try:
            resp = requests.get(url, timeout=3)
            resp.raise_for_status()
            data = resp.json()
            
            usd_val = float(data["USDBRL"]["bid"])
            eur_val = float(data["EURBRL"]["bid"])
            
            self.repo.save_quote("USD-BRL", "Dólar Comercial", usd_val, "BRL")
            self.repo.save_quote("EUR-BRL", "Euro Comercial", eur_val, "BRL")
            
            return {
                "USD": MarketQuote("USD-BRL", "Dólar Comercial", usd_val, float(data["USDBRL"]["pctChange"])),
                "EUR": MarketQuote("EUR-BRL", "Euro Comercial", eur_val, float(data["EURBRL"]["pctChange"]))
            }
        except Exception:
            return {
                "USD": MarketQuote("USD-BRL", "Dólar (Ref)", 5.45, 0.0),
                "EUR": MarketQuote("EUR-BRL", "Euro (Ref)", 5.95, 0.0)
            }

    def get_commodity_quote(self, ticker: str, name: str, default_price: float) -> MarketQuote:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if not hist.empty and len(hist) >= 2:
                close = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                pct = ((close - prev) / prev) * 100
                self.repo.save_quote(ticker, name, close)
                return MarketQuote(ticker, name, close, pct)
        except Exception:
            pass
        return MarketQuote(ticker, f"{name} (Ref)", default_price, 0.0)

# =====================================================================
# CAMADA DE REGRAS DE NEGÓCIO: Motor de Custo Agroindustrial
# =====================================================================
class IndustrialCostEngine:
    @staticmethod
    def calculate(
        items: List[RawMaterialItem],
        params: ProductionParameters,
        usd_rate: float
    ) -> CostBreakdownResult:
        breakdown = []
        raw_mat_sum = 0.0

        for item in items:
            rate = usd_rate if item.currency == "USD" else 1.0
            price_brl_kg = item.unit_price * rate
            cost_ton = price_brl_kg * (item.inclusion_pct / 100.0) * 1000.0
            raw_mat_sum += cost_ton
            
            breakdown.append({
                "Ingrediente": item.name,
                "Categoria": item.category,
                "Inclusão (%)": item.inclusion_pct,
                "Preço Unit. (R$/kg)": round(price_brl_kg, 3),
                "Custo R$/ton": round(cost_ton, 2)
            })

        process_loss_cost = raw_mat_sum * (params.moisture_loss_pct / 100.0)
        packaging_total = params.packaging_cost_ton * (1.0 + (params.packaging_loss_pct / 100.0))
        
        total_ton = (
            raw_mat_sum 
            + process_loss_cost 
            + params.freight_inbound_ton 
            + packaging_total 
            + params.industrial_cif_ton
        )

        return CostBreakdownResult(
            total_cost_ton=round(total_ton, 2),
            cost_bag_40kg=round((total_ton / 1000.0) * 40.0, 2),
            cost_bag_25kg=round((total_ton / 1000.0) * 25.0, 2),
            raw_material_cost_ton=round(raw_mat_sum, 2),
            freight_total_ton=round(params.freight_inbound_ton, 2),
            packaging_total_ton=round(packaging_total, 2),
            industrial_cif_ton=round(params.industrial_cif_ton, 2),
            process_loss_cost_ton=round(process_loss_cost, 2),
            items_breakdown=breakdown
        )

# =====================================================================
# CAMADA FULL-STACK: Interface Streamlit por Abas
# =====================================================================
@st.cache_resource
def init_services():
    repo = MarketRepository()
    collector = ResilientMarketCollector(repo)
    return repo, collector

repo, collector = init_services()

@st.cache_data(ttl=600, show_spinner="Sincronizando cotações do agronegócio...")
def get_live_data():
    currencies = collector.get_currencies()
    milho = collector.get_commodity_quote("CCM=F", "Milho B3", 64.20)
    soja = collector.get_commodity_quote("ZS=F", "Soja CBOT", 102.50)
    brent = collector.get_commodity_quote("BZ=F", "Petróleo Brent", 79.50)
    return currencies, milho, soja, brent

currencies, milho, soja, brent = get_live_data()

# Header
st.title("🌾 Plataforma de Inteligência de Custos Agroindustriais")
st.caption("Visão Integrada de Mercado, Volatilidade de Commodities e Custo Unitário de Formulação")

# Sidebar: Parâmetros Fabris
with st.sidebar:
    st.header("⚙️ Parâmetros Fabris")
    freight = st.number_input("Frete Inbound Médio (R$/ton)", 0.0, 500.0, 85.0, 5.0)
    pkg_cost = st.number_input("Custo Base Embalagem (R$/ton)", 0.0, 200.0, 35.0, 2.0)
    pkg_loss = st.slider("Perda Operacional no Ensaque (%)", 0.0, 5.0, 0.8, 0.1)
    process_loss = st.slider("Quebra de Processo / Secagem (%)", 0.0, 5.0, 1.2, 0.1)
    cif = st.number_input("GGF / CIF Industrial (R$/ton)", 0.0, 500.0, 115.0, 10.0)

params = ProductionParameters(
    freight_inbound_ton=freight,
    packaging_cost_ton=pkg_cost,
    packaging_loss_pct=pkg_loss,
    moisture_loss_pct=process_loss,
    industrial_cif_ton=cif
)

# Abas Executivas
tab1, tab2, tab3 = st.tabs([
    "📊 Cockpit de Mercado", 
    "🧪 Engenharia de Custos & Formulação", 
    "📈 Análise de Sensibilidade & Exportação"
])

# ABA 1: MERCADO
with tab1:
    st.subheader("Indicadores Macroeconômicos e de Commodities")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(currencies["USD"].name, f"R$ {currencies['USD'].price:.4f}", f"{currencies['USD'].change_pct:.2f}%")
    c2.metric(currencies["EUR"].name, f"R$ {currencies['EUR'].price:.4f}", f"{currencies['EUR'].change_pct:.2f}%")
    c3.metric(milho.name, f"R$ {milho.price:.2f}", f"{milho.change_pct:.2f}%")
    c4.metric(brent.name, f"US$ {brent.price:.2f}", f"{brent.change_pct:.2f}%")
    st.divider()
    st.info("💡 **Dica do Analista:** Variações no Petróleo Brent antecipam oscilações no custo de diesel da tabela de frete ANP em aproximadamente 15 a 21 dias.")

# ABA 2: FORMULAÇÃO
with tab2:
    st.subheader("Composição da Ficha Técnica (BOM)")
    
    if "recipe_df" not in st.session_state:
        st.session_state.recipe_df = pd.DataFrame([
            {"ingrediente": "Milho Moído Fino", "categoria": "Macro", "inclusao_pct": 58.0, "preco_kg": 1.18, "moeda": "BRL"},
            {"ingrediente": "Farelo de Soja 46%", "categoria": "Macro", "inclusao_pct": 27.5, "preco_kg": 2.15, "moeda": "BRL"},
            {"ingrediente": "Farinha de Vísceras Aves", "categoria": "Macro", "inclusao_pct": 5.5, "preco_kg": 2.60, "moeda": "BRL"},
            {"ingrediente": "Óleo de Soja Degomado", "categoria": "Macro", "inclusao_pct": 2.5, "preco_kg": 4.95, "moeda": "BRL"},
            {"ingrediente": "Núcleo Mineral/Vitamínico", "categoria": "Premix", "inclusao_pct": 4.0, "preco_kg": 14.20, "moeda": "BRL"},
            {"ingrediente": "L-Lisina HCL (USD)", "categoria": "Aditivo", "inclusao_pct": 1.5, "preco_kg": 2.30, "moeda": "USD"},
            {"ingrediente": "DL-Metionina (USD)", "categoria": "Aditivo", "inclusao_pct": 1.0, "preco_kg": 3.85, "moeda": "USD"},
        ])
    
    edited_recipe = st.data_editor(
        st.session_state.recipe_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ingrediente": "Ingrediente / Matéria-Prima",
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["Macro", "Micro", "Premix", "Aditivo"]),
            "inclusao_pct": st.column_config.NumberColumn("Inclusão (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f%%"),
            "preco_kg": st.column_config.NumberColumn("Preço Unitário (por kg)", min_value=0.0, format="R$ %.3f"),
            "moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"])
        }
    )
    
    items = [
        RawMaterialItem(
            name=row["ingrediente"],
            inclusion_pct=row["inclusao_pct"],
            unit_price=row["preco_kg"],
            currency=row["moeda"],
            category=row["categoria"]
        )
        for _, row in edited_recipe.iterrows() if pd.notna(row["ingrediente"])
    ]
    
    total_inc = sum(i.inclusion_pct for i in items)
    if abs(total_inc - 100.0) > 0.01:
        st.warning(f"⚠️ A inclusão total está em **{total_inc:.2f}%**. O padrão de fechamento é 100.00%.")
    else:
        st.success("✅ Fechamento de fórmula conferido (100.00%).")
    
    calc_result = IndustrialCostEngine.calculate(items, params, currencies["USD"].price)
    
    st.markdown("### Síntese de Custos Fabris")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Custo Final / Tonelada", f"R$ {calc_result.total_cost_ton:,.2f}")
    m2.metric("Custo Saca 40 kg", f"R$ {calc_result.cost_bag_40kg:,.2f}")
    m3.metric("Custo Saca 25 kg", f"R$ {calc_result.cost_bag_25kg:,.2f}")
    m4.metric("Matérias-Primas (CPV)", f"R$ {calc_result.raw_material_cost_ton:,.2f}")

    col_g1, col_g2 = st.columns([3, 2])
    with col_g1:
        fig_pie = px.pie(
            calc_result.items_breakdown,
            names="Ingrediente",
            values="Custo R$/ton",
            title="Distribuição do Custo de Insumos por Tonelada",
            hole=0.45
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_g2:
        df_costs = pd.DataFrame({
            "Etapa": ["Matérias-Primas", "Frete Inbound", "Embalagens", "CIF Industrial", "Quebra Térmica"],
            "Custo (R$/ton)": [
                calc_result.raw_material_cost_ton,
                calc_result.freight_total_ton,
                calc_result.packaging_total_ton,
                calc_result.industrial_cif_ton,
                calc_result.process_loss_cost_ton
            ]
        })
        fig_bar = px.bar(df_costs, x="Etapa", y="Custo (R$/ton)", title="Formação Completa do Custo Unitário", text_auto=True)
        st.plotly_chart(fig_bar, use_container_width=True)

# ABA 3: SENSIBILIDADE & EXCEL
with tab3:
    st.subheader("Simulação de Estresse (What-If)")
    st.write("Simule como choques de oferta e câmbio afetam a margem sem alterar a fórmula base:")
    
    s_col1, s_col2 = st.columns(2)
    shock_corn = s_col1.slider("Choque no Preço do Milho (%)", -30, 30, 0, 5)
    shock_fx = s_col2.slider("Choque no Câmbio USD (%)", -20, 20, 0, 5)
    
    stressed_items = []
    for it in items:
        item_copy = RawMaterialItem(it.name, it.inclusion_pct, it.unit_price, it.currency, it.category)
        if "Milho" in it.name:
            item_copy.unit_price *= (1 + shock_corn / 100.0)
        stressed_items.append(item_copy)
    
    stressed_usd = currencies["USD"].price * (1 + shock_fx / 100.0)
    stressed_res = IndustrialCostEngine.calculate(stressed_items, params, stressed_usd)
    
    diff_ton = stressed_res.total_cost_ton - calc_result.total_cost_ton
    st.metric(
        "Custo Estressado por Tonelada",
        f"R$ {stressed_res.total_cost_ton:,.2f}",
        delta=f"R$ {diff_ton:,.2f} ({((diff_ton)/calc_result.total_cost_ton)*100:+.2f}%)",
        delta_color="inverse"
    )
    
    st.divider()
    st.subheader("📥 Exportação Executiva")
    st.write("Baixe a planilha estruturada para reuniões de precificação:")
    
    # Geração do arquivo Excel em memória
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_summary = pd.DataFrame({
            "Métrica Operacional": [
                "Custo Total por Tonelada", "Custo por Saca (40 kg)", "Custo por Saca (25 kg)",
                "Subtotal Matérias-Primas", "Quebra de Processo / Umidade", "Frete Inbound Médio",
                "Embalagens (+ perdas)", "CIF / GGF Industrial"
            ],
            "Valor (R$)": [
                calc_result.total_cost_ton, calc_result.cost_bag_40kg, calc_result.cost_bag_25kg,
                calc_result.raw_material_cost_ton, calc_result.process_loss_cost_ton,
                calc_result.freight_total_ton, calc_result.packaging_total_ton, calc_result.industrial_cif_ton
            ]
        })
        df_summary.to_excel(writer, sheet_name="Resumo Gerencial", index=False)
        pd.DataFrame(calc_result.items_breakdown).to_excel(writer, sheet_name="Ficha Técnica (BOM)", index=False)
    
    excel_buffer.seek(0)
    st.download_button(
        label="📊 Baixar Relatório em Excel (.xlsx)",
        data=excel_buffer,
        file_name="relatorio_custos_nutricao_animal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
