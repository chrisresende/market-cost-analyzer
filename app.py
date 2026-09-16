import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.core.models import RawMaterialItem, ProductionParameters
from src.database.repository import MarketRepository
from src.services.market_collector import ResilientMarketCollector
from src.services.cost_calculator import IndustrialCostEngine
from src.services.exporter import ExcelReportService

# Configuração de Página
st.set_page_config(
    page_title="Market Cost Analyzer | Nutrição Animal",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização de Serviços
@st.cache_resource
def init_services():
    repo = MarketRepository()
    collector = ResilientMarketCollector(repo)
    return repo, collector

repo, collector = init_services()

# Coleta de Dados em Cache (10 minutos)
@st.cache_data(ttl=600, show_spinner="Sincronizando cotações do agronegócio...")
def get_live_data():
    currencies = collector.get_currencies()
    milho = collector.get_commodity_quote("CCM=F", "Milho B3", 64.20)
    soja = collector.get_commodity_quote("ZS=F", "Soja CBOT", 102.50)
    brent = collector.get_commodity_quote("BZ=F", "Petróleo Brent", 79.50)
    return currencies, milho, soja, brent

currencies, milho, soja, brent = get_live_data()

# Header Executivo
st.title("🌾 Plataforma de Inteligência de Custos Agroindustriais")
st.caption("Visão Integrada de Mercado, Volatilidade de Commodities e Custo Unitário de Formulação")

# Barra Lateral: Parâmetros Globais de Fábrica
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

# Navegação por Abas
tab1, tab2, tab3 = st.tabs([
    "📊 Cockpit de Mercado", 
    "🧪 Engenharia de Custos & Formulação", 
    "📈 Análise de Sensibilidade & Exportação"
])

# -------------------------------------------------------------
# ABA 1: COCKPIT DE MERCADO
# -------------------------------------------------------------
with tab1:
    st.subheader("Indicadores Macroeconômicos e de Commodities")
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric(currencies["USD"].name, f"R$ {currencies['USD'].price:.4f}", f"{currencies['USD'].change_pct:.2f}%")
    c2.metric(currencies["EUR"].name, f"R$ {currencies['EUR'].price:.4f}", f"{currencies['EUR'].change_pct:.2f}%")
    c3.metric(milho.name, f"R$ {milho.price:.2f}", f"{milho.change_pct:.2f}%")
    c4.metric(brent.name, f"US$ {brent.price:.2f}", f"{brent.change_pct:.2f}%")
    
    st.divider()
    st.info("💡 **Dica do Analista:** Variações no Petróleo Brent antecipam oscilações no custo de diesel da tabela de frete ANP em aproximadamente 15 a 21 dias.")

# -------------------------------------------------------------
# ABA 2: FORMULAÇÃO & ENGENHARIA DE CUSTOS
# -------------------------------------------------------------
with tab2:
    st.subheader("Composição da Ficha Técnica (BOM)")
    
    # Ficha padrão inicial
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
    
    # Conversão para objetos de domínio
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
    
    # Validação do fechamento
    total_inc = sum(i.inclusion_pct for i in items)
    if abs(total_inc - 100.0) > 0.01:
        st.warning(f"⚠️ A inclusão total atual é de **{total_inc:.2f}%**. O fechamento padrão da batelada é 100%.")
    else:
        st.success("✅ Fechamento de fórmula conferido (100.00%).")
    
    # Cálculo
    calc_result = IndustrialCostEngine.calculate(items, params, currencies["USD"].price)
    
    st.markdown("### Síntese de Custos Fabris")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Custo Final / Tonelada", f"R$ {calc_result.total_cost_ton:,.2f}")
    m2.metric("Custo Saca 40 kg", f"R$ {calc_result.cost_bag_40kg:,.2f}")
    m3.metric("Custo Saca 25 kg", f"R$ {calc_result.cost_bag_25kg:,.2f}")
    m4.metric("Matérias-Primas (CPV)", f"R$ {calc_result.raw_material_cost_ton:,.2f}")

    # Gráfico de Pareto/Distribuição
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

# -------------------------------------------------------------
# ABA 3: SENSIBILIDADE E EXPORTAÇÃO
# -------------------------------------------------------------
with tab3:
    st.subheader("Simulação de Estresse (What-If)")
    st.write("Simule como choques de oferta e câmbio afetam a margem sem alterar a fórmula base:")
    
    s_col1, s_col2 = st.columns(2)
    shock_corn = s_col1.slider("Choque no Preço do Milho (%)", -30, 30, 0, 5)
    shock_fx = s_col2.slider("Choque no Câmbio USD (%)", -20, 20, 0, 5)
    
    # Aplica choque em cópia temporária
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
    st.write("Baixe a planilha estruturada com todas as memórias de cálculo para apresentação:")
    
    excel_file = ExcelReportService.generate_executive_sheet(calc_result, params)
    st.download_button(
        label="📊 Baixar Relatório em Excel (.xlsx)",
        data=excel_file,
        file_name="relatorio_custos_nutricao_animal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
