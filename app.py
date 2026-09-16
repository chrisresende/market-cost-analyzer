import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO DE TELA E METADADOS
# ==============================================================================
st.set_page_config(
    page_title="AgroCost Hub | Inteligência em Nutrição Animal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# DESIGN SYSTEM: CSS CUSTOMIZADO / UI PROFISSIONAL
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1e293b;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 96%;
    }

    .top-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #047857 100%);
        padding: 24px 30px;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .top-header h1 {
        font-size: 26px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .top-header p {
        font-size: 14px;
        margin: 4px 0 0 0;
        color: #cbd5e1;
    }
    .badge-live {
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid #10b981;
        color: #6ee7b7;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-live span {
        width: 8px;
        height: 8px;
        background-color: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10b981;
    }

    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 12px;
        border-top: 4px solid #047857;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.08);
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .kpi-delta-pos {
        font-size: 11px;
        font-weight: 600;
        color: #059669;
    }
    .kpi-delta-neg {
        font-size: 11px;
        font-weight: 600;
        color: #dc2626;
    }

    .cost-box {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #cbd5e1;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
    }
    .cost-box-highlight {
        background: linear-gradient(145deg, #ecfdf5 0%, #d1fae5 100%);
        border: 2px solid #059669;
    }

    section[data-testid="stSidebar"] {
        background: #0f172a !important;
    }
    section[data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# PIPELINE DE DADOS: MACRO, MERCADO FUTURO E COMMODITIES
# ==============================================================================
@st.cache_data(ttl=900, show_spinner=False)
def get_macro_indicators():
    data = {
        "usd": 5.42, "usd_pct": 0.15,
        "eur": 5.92, "eur_pct": -0.10,
        "ipca_12m": 4.10, "selic_meta": 10.50,
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    # AwesomeAPI - Moedas
    try:
        r = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3)
        if r.status_code == 200:
            res = r.json()
            data["usd"] = float(res["USDBRL"]["bid"])
            data["usd_pct"] = float(res["USDBRL"]["pctChange"])
            data["eur"] = float(res["EURBRL"]["bid"])
            data["eur_pct"] = float(res["EURBRL"]["pctChange"])
            data["updated_at"] = res["USDBRL"]["create_date"]
    except Exception:
        pass

    # Banco Central (IPCA 13522 e Meta Selic 432)
    try:
        r_ipca = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados/ultimos/1?formato=json", timeout=3)
        if r_ipca.status_code == 200:
            data["ipca_12m"] = float(r_ipca.json()[0]["valor"])
    except Exception:
        pass

    try:
        r_selic = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=3)
        if r_selic.status_code == 200:
            data["selic_meta"] = float(r_selic.json()[0]["valor"])
    except Exception:
        pass

    return data

@st.cache_data(ttl=900, show_spinner=False)
def get_market_assets():
    """
    Coleta indicadores do TradingView / Mercado Futuro:
    - Petróleo WTI (CL=F)
    - Ibovespa (^BVSP)
    - Milho B3 (CCM=F)
    - Soja CBOT (ZS=F)
    - Farelo de Soja CBOT (ZM=F)
    """
    asset_map = {
        "WTI": {"ticker": "CL=F", "def_price": 74.50},
        "IBOV": {"ticker": "^BVSP", "def_price": 128500.0},
        "MILHO_B3": {"ticker": "CCM=F", "def_price": 63.80},
        "SOJA_CBOT": {"ticker": "ZS=F", "def_price": 104.20},
        "FARELO_CBOT": {"ticker": "ZM=F", "def_price": 318.0},
    }
    
    results = {}
    for key, info in asset_map.items():
        try:
            t = yf.Ticker(info["ticker"])
            df = t.history(period="1mo")
            if not df.empty and len(df) >= 2:
                last_p = float(df["Close"].iloc[-1])
                prev_p = float(df["Close"].iloc[-2])
                pct = ((last_p - prev_p) / prev_p) * 100.0
                results[key] = {"price": last_p, "change": pct, "df": df}
            else:
                results[key] = {"price": info["def_price"], "change": 0.0, "df": pd.DataFrame()}
        except Exception:
            results[key] = {"price": info["def_price"], "change": 0.0, "df": pd.DataFrame()}
            
    return results

macro = get_macro_indicators()
assets = get_market_assets()

# Paridade Técnica do Sorgo Granífero (referência 82% do preço do Milho B3 por saca 60kg)
milho_price = assets["MILHO_B3"]["price"]
sorgo_price_saca = milho_price * 0.82
sorgo_price_kg = sorgo_price_saca / 60.0

# ==============================================================================
# HEADER HERO HTML
# ==============================================================================
st.markdown(f"""
<div class="top-header">
    <div>
        <h1>⚡ AgroCost Hub — Inteligência em Nutrição Animal</h1>
        <p>Monitoramento Contínuo de Commodities, Fretes Inbound e Custo Unitário de Formulação</p>
    </div>
    <div class="badge-live">
        <span></span> APIs Conectadas ({macro['updated_at']})
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# MENU LATERAL REFINADO
# ==============================================================================
st.sidebar.markdown("### 🌾 NAVEGAÇÃO")
menu = st.sidebar.radio(
    "",
    [
        "📊 Cockpit Macroeconômico",
        "⚖️ Custo Médio vs. Reposição",
        "🚚 Frete Inbound & Despesas CIF",
        "🎯 Formação de Preço & DRE",
        "📉 Ponto de Equilíbrio (Break-Even)",
        "🌪️ Matriz de Sensibilidade (What-If)"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 SÍNTESE RÁPIDA DE CÂMBIO")
st.sidebar.markdown(f"""
<div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px;">
    <div style="font-size: 11px; color: #94a3b8;">DÓLAR COMERCIAL</div>
    <div style="font-size: 20px; font-weight: 700; color: #38bdf8;">R$ {macro['usd']:.4f}</div>
    <div style="font-size: 12px; color: {'#4ade80' if macro['usd_pct'] >= 0 else '#f87171'}; font-weight: 600;">{macro['usd_pct']:+.2f}% no dia</div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# MÓDULO 1: COCKPIT MACROECONÔMICO & COMMODITIES
# ==============================================================================
if menu == "📊 Cockpit Macroeconômico":
    st.subheader("Painel Macroeconômico, Risco e Mercado Futuro")

    # Linha 1: Moedas e Ativos Globais (WTI, Ibovespa, Selic)
    st.markdown("##### 🌐 Moedas, Energia e Risco Brasil")
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #047857;">
            <div class="kpi-label">Dólar Comercial</div>
            <div class="kpi-value">R$ {macro['usd']:.4f}</div>
            <div class="{'kpi-delta-pos' if macro['usd_pct'] >= 0 else 'kpi-delta-neg'}">{macro['usd_pct']:+.2f}% dia</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #0284c7;">
            <div class="kpi-label">Euro Comercial</div>
            <div class="kpi-value">R$ {macro['eur']:.4f}</div>
            <div class="{'kpi-delta-pos' if macro['eur_pct'] >= 0 else 'kpi-delta-neg'}">{macro['eur_pct']:+.2f}% dia</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        wti_val = assets["WTI"]["price"]
        wti_ch = assets["WTI"]["change"]
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #3b82f6;">
            <div class="kpi-label">Petróleo WTI (CL1!)</div>
            <div class="kpi-value">US$ {wti_val:.2f}</div>
            <div class="{'kpi-delta-pos' if wti_ch >= 0 else 'kpi-delta-neg'}">{wti_ch:+.2f}% barril</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        ibov_val = assets["IBOV"]["price"]
        ibov_ch = assets["IBOV"]["change"]
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #6366f1;">
            <div class="kpi-label">Ibovespa (IBOV)</div>
            <div class="kpi-value">{ibov_val:,.0f}</div>
            <div class="{'kpi-delta-pos' if ibov_ch >= 0 else 'kpi-delta-neg'}">{ibov_ch:+.2f}% pts</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #475569;">
            <div class="kpi-label">Juros / Meta Selic (BR)</div>
            <div class="kpi-value">{macro['selic_meta']:.2f}% a.a.</div>
            <div class="kpi-delta-pos">IPCA 12M: {macro['ipca_12m']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Linha 2: Culturas Agrícolas (Milho B3, Soja CBOT, Farelo Soja, Sorgo)
    st.markdown("##### 🌾 Culturas Agrícolas & Matérias-Primas Principais")
    k_m1, k_m2, k_m3, k_m4 = st.columns(4)
    with k_m1:
        m_val = assets["MILHO_B3"]["price"]
        m_ch = assets["MILHO_B3"]["change"]
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #f59e0b;">
            <div class="kpi-label">Milho Futuro B3 (CCM=F)</div>
            <div class="kpi-value">R$ {m_val:.2f}</div>
            <div class="{'kpi-delta-pos' if m_ch >= 0 else 'kpi-delta-neg'}">{m_ch:+.2f}% / sc 60kg (R$ {m_val/60:.3f}/kg)</div>
        </div>
        """, unsafe_allow_html=True)
    with k_m2:
        s_val = assets["SOJA_CBOT"]["price"]
        s_ch = assets["SOJA_CBOT"]["change"]
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #10b981;">
            <div class="kpi-label">Soja Grão CBOT (ZS=F)</div>
            <div class="kpi-value">US$ {s_val:.2f}</div>
            <div class="{'kpi-delta-pos' if s_ch >= 0 else 'kpi-delta-neg'}">{s_ch:+.2f}% cents/bushel</div>
        </div>
        """, unsafe_allow_html=True)
    with k_m3:
        f_val = assets["FARELO_CBOT"]["price"]
        f_ch = assets["FARELO_CBOT"]["change"]
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #84cc16;">
            <div class="kpi-label">Farelo de Soja CBOT (ZM=F)</div>
            <div class="kpi-value">US$ {f_val:.1f}</div>
            <div class="{'kpi-delta-pos' if f_ch >= 0 else 'kpi-delta-neg'}">{f_ch:+.2f}% / short ton</div>
        </div>
        """, unsafe_allow_html=True)
    with k_m4:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #eab308;">
            <div class="kpi-label">Sorgo Granífero (Paridade)</div>
            <div class="kpi-value">R$ {sorgo_price_saca:.2f}</div>
            <div class="kpi-delta-pos">82% paridade milho (R$ {sorgo_price_kg:.3f}/kg)</div>
        </div>
        """, unsafe_allow_html=True)

    # Gráfico de Tendências Cruzadas
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        df_milho = assets["MILHO_B3"]["df"]
        if not df_milho.empty:
            fig_m = px.area(df_milho, y="Close", title="Tendência do Milho B3 (Últimos 30 dias)", labels={"Close": "R$/saca", "Date": "Data"})
            fig_m.update_traces(line_color="#047857", fillcolor="rgba(4, 120, 87, 0.1)")
            fig_m.update_layout(height=340, margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor="#ffffff")
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.info("Série do Milho B3 em carregamento.")

    with col_chart2:
        df_wti = assets["WTI"]["df"]
        if not df_wti.empty:
            fig_w = px.line(df_wti, y="Close", title="Evolução do Petróleo WTI (Impacto Frete/Resinas)", labels={"Close": "US$/barril", "Date": "Data"})
            fig_w.update_traces(line_color="#2563eb")
            fig_w.update_layout(height=340, margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor="#ffffff")
            st.plotly_chart(fig_w, use_container_width=True)
        else:
            st.info("Série do Petróleo WTI em carregamento.")

# ==============================================================================
# MÓDULO 2: CUSTO MÉDIO VS. REPOSIÇÃO (COM SORGO, MILHO E SOJA)
# ==============================================================================
elif menu == "⚖️ Custo Médio vs. Reposição":
    st.subheader("Auditoria de Ficha Técnica (BOM) e Custo de Reposição")
    st.write("Compare o custo contábil do estoque com as cotações spot de reposição.")

    preset = st.selectbox(
        "Selecione uma Linha de Ração Padrão:",
        ["Frango de Corte Inicial", "Bovino Confinamento (Alto Grão com Sorgo)", "Suíno Terminação"]
    )

    milho_spot_kg = round(milho_price / 60.0, 3)
    sorgo_spot_kg = round(sorgo_price_kg, 3)

    if preset == "Frango de Corte Inicial":
        items_data = [
            {"ingrediente": "Milho Moído Fino", "inclusao": 58.0, "custo_medio_kg": 1.10, "custo_spot_kg": milho_spot_kg, "moeda": "BRL"},
            {"ingrediente": "Farelo de Soja 46%", "inclusao": 27.5, "custo_medio_kg": 2.05, "custo_spot_kg": 2.18, "moeda": "BRL"},
            {"ingrediente": "Farinha de Vísceras Aves", "inclusao": 5.5, "custo_medio_kg": 2.45, "custo_spot_kg": 2.65, "moeda": "BRL"},
            {"ingrediente": "Óleo de Soja Degomado", "inclusao": 2.5, "custo_medio_kg": 4.80, "custo_spot_kg": 5.10, "moeda": "BRL"},
            {"ingrediente": "Núcleo Mineral/Vitamínico", "inclusao": 4.0, "custo_medio_kg": 13.50, "custo_spot_kg": 14.20, "moeda": "BRL"},
            {"ingrediente": "L-Lisina HCl (USD)", "inclusao": 1.5, "custo_medio_kg": 2.15, "custo_spot_kg": 2.35, "moeda": "USD"},
            {"ingrediente": "DL-Metionina (USD)", "inclusao": 1.0, "custo_medio_kg": 3.70, "custo_spot_kg": 3.90, "moeda": "USD"}
        ]
    elif preset == "Bovino Confinamento (Alto Grão com Sorgo)":
        items_data = [
            {"ingrediente": "Milho Grão Inteiro", "inclusao": 45.0, "custo_medio_kg": 1.10, "custo_spot_kg": milho_spot_kg, "moeda": "BRL"},
            {"ingrediente": "Sorgo Granífero Moído", "inclusao": 30.0, "custo_medio_kg": 0.92, "custo_spot_kg": sorgo_spot_kg, "moeda": "BRL"},
            {"ingrediente": "Farelo de Soja 46%", "inclusao": 12.0, "custo_medio_kg": 2.05, "custo_spot_kg": 2.18, "moeda": "BRL"},
            {"ingrediente": "Caroço de Algodão", "inclusao": 8.0, "custo_medio_kg": 1.35, "custo_spot_kg": 1.45, "moeda": "BRL"},
            {"ingrediente": "Núcleo Mineral Confinamento", "inclusao": 5.0, "custo_medio_kg": 5.80, "custo_spot_kg": 6.10, "moeda": "BRL"}
        ]
    else:
        items_data = [
            {"ingrediente": "Milho Moído", "inclusao": 45.0, "custo_medio_kg": 1.10, "custo_spot_kg": milho_spot_kg, "moeda": "BRL"},
            {"ingrediente": "Sorgo Granífero", "inclusao": 20.0, "custo_medio_kg": 0.92, "custo_spot_kg": sorgo_spot_kg, "moeda": "BRL"},
            {"ingrediente": "Farelo de Soja 46%", "inclusao": 22.0, "custo_medio_kg": 2.05, "custo_spot_kg": 2.18, "moeda": "BRL"},
            {"ingrediente": "Farinha de Carne e Ossos", "inclusao": 6.0, "custo_medio_kg": 1.90, "custo_spot_kg": 2.05, "moeda": "BRL"},
            {"ingrediente": "Premix Suínos Terminação", "inclusao": 4.0, "custo_medio_kg": 8.50, "custo_spot_kg": 8.90, "moeda": "BRL"},
            {"ingrediente": "L-Lisina HCl (USD)", "inclusao": 1.5, "custo_medio_kg": 2.15, "custo_spot_kg": 2.35, "moeda": "USD"},
            {"ingrediente": "Aditivo Ractopamina", "inclusao": 1.5, "custo_medio_kg": 18.00, "custo_spot_kg": 18.00, "moeda": "BRL"}
        ]

    edited_df = st.data_editor(
        pd.DataFrame(items_data),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ingrediente": "Matéria-Prima",
            "inclusao": st.column_config.NumberColumn("Inclusão (%)", min_value=0.0, max_value=100.0, format="%.2f%%"),
            "custo_medio_kg": st.column_config.NumberColumn("Custo Médio Estoque (R$/kg)", min_value=0.0, format="R$ %.3f"),
            "custo_spot_kg": st.column_config.NumberColumn("Custo Reposição Spot (R$/kg)", min_value=0.0, format="R$ %.3f"),
            "moeda": st.column_config.SelectboxColumn("Moeda", options=["BRL", "USD"])
        }
    )

    tot_inc = edited_df["inclusao"].sum()
    if abs(tot_inc - 100.0) > 0.01:
        st.warning(f"⚠️ A soma da inclusão é **{tot_inc:.2f}%**. O fechamento padrão é 100.00%.")

    usd_rate = macro["usd"]
    calc_df = edited_df.copy()
    calc_df["mult"] = calc_df["moeda"].apply(lambda m: usd_rate if m == "USD" else 1.0)
    calc_df["medio_ton"] = calc_df["custo_medio_kg"] * calc_df["mult"] * (calc_df["inclusao"] / 100.0) * 1000.0
    calc_df["spot_ton"] = calc_df["custo_spot_kg"] * calc_df["mult"] * (calc_df["inclusao"] / 100.0) * 1000.0

    total_medio = calc_df["medio_ton"].sum()
    total_spot = calc_df["spot_ton"].sum()
    gap_val = total_spot - total_medio
    gap_pct = (gap_val / total_medio) * 100.0

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    with c_m1:
        st.markdown(f"""
        <div class="cost-box">
            <div class="kpi-label">CUSTO MÉDIO ESTOQUE</div>
            <div style="font-size:24px; font-weight:800; color:#475569;">R$ {total_medio:,.2f}</div>
            <div style="font-size:12px; color:#64748b;">R$ {(total_medio/1000)*40:.2f} / saca 40kg</div>
        </div>
        """, unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"""
        <div class="cost-box cost-box-highlight">
            <div class="kpi-label" style="color:#065f46;">CUSTO DE REPOSIÇÃO (SPOT)</div>
            <div style="font-size:24px; font-weight:800; color:#047857;">R$ {total_spot:,.2f}</div>
            <div style="font-size:12px; color:#065f46; font-weight:600;">R$ {(total_spot/1000)*40:.2f} / saca 40kg</div>
        </div>
        """, unsafe_allow_html=True)
    with c_m3:
        color_gap = "#dc2626" if gap_val > 0 else "#059669"
        st.markdown(f"""
        <div class="cost-box">
            <div class="kpi-label">DEFASAGEM DE CUSTO (GAP)</div>
            <div style="font-size:24px; font-weight:800; color:{color_gap};">R$ {gap_val:+,.2f}</div>
            <div style="font-size:12px; color:{color_gap}; font-weight:600;">{gap_pct:+.2f}% vs. estoque</div>
        </div>
        """, unsafe_allow_html=True)
    with c_m4:
        st.markdown(f"""
        <div class="cost-box">
            <div class="kpi-label">SACA 25 KG (REPOSIÇÃO)</div>
            <div style="font-size:24px; font-weight:800; color:#0f172a;">R$ {(total_spot/1000)*25:.2f}</div>
            <div style="font-size:12px; color:#64748b;">Impacto: R$ {(gap_val/1000)*25:+.2f}/sc</div>
        </div>
        """, unsafe_allow_html=True)

    fig_bar = go.Figure(data=[
        go.Bar(name="Estoque Médio", x=calc_df["ingrediente"], y=calc_df["medio_ton"], marker_color="#64748b"),
        go.Bar(name="Reposição Spot", x=calc_df["ingrediente"], y=calc_df["spot_ton"], marker_color="#047857")
    ])
    fig_bar.update_layout(
        barmode="group",
        title="Impacto por Ingrediente na Batelada (R$/ton)",
        height=380,
        margin=dict(l=20, r=20, t=50, b=100),
        plot_bgcolor="#ffffff",
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ==============================================================================
# MÓDULO 3: FRETE INBOUND & DESPESAS CIF
# ==============================================================================
elif menu == "🚚 Frete Inbound & Despesas CIF":
    st.subheader("Cálculo do Custo Efetivo de Aquisição (Inbound)")

    c_f1, c_f2 = st.columns(2)
    with c_f1:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin-bottom:15px;">
            <div style="font-weight:700; color:#0f172a; margin-bottom:12px;">Parâmetros da Rota e Veículo</div>
        """, unsafe_allow_html=True)
        rota = st.text_input("Origem do Carregamento", "Rondonópolis - MT")
        carga_util = st.number_input("Carga Líquida Transportada (ton)", 1.0, 60.0, 48.0, 1.0)
        frete_bruto_ton = st.number_input("Frete Bruto Negociado (R$/ton)", 0.0, 600.0, 275.0, 5.0)
        seguro_pct = st.number_input("Taxa de Seguro de Carga (%)", 0.0, 2.0, 0.25, 0.05)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_f2:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin-bottom:15px;">
            <div style="font-weight:700; color:#0f172a; margin-bottom:12px;">Tributos Recuperáveis e Taxas</div>
        """, unsafe_allow_html=True)
        icms_aliquota = st.selectbox("Alíquota ICMS Frete Interestadual (%)", [0.0, 7.0, 12.0], index=2)
        icms_credito = st.checkbox("Credita ICMS sobre frete (Não-cumulativo)", value=True)
        pedagio_total = st.number_input("Pedágios da Rota (R$ total)", 0.0, 3000.0, 680.0, 50.0)
        taxa_descarga = st.number_input("Taxa de Moega / Descarga (R$/ton)", 0.0, 50.0, 12.0, 1.0)
        st.markdown("</div>", unsafe_allow_html=True)

    pedagio_ton = pedagio_total / carga_util
    icms_ton = (frete_bruto_ton * (icms_aliquota / 100.0)) if icms_credito else 0.0
    seguro_ton = frete_bruto_ton * (seguro_pct / 100.0)
    frete_liquido_ton = frete_bruto_ton - icms_ton + pedagio_ton + taxa_descarga + seguro_ton

    st.markdown("### Resumo do Custo Logístico por Tonelada")
    rf1, rf2, rf3, rf4 = st.columns(4)
    with rf1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #047857;">
            <div class="kpi-label">Frete Líquido Efetivo</div>
            <div class="kpi-value">R$ {frete_liquido_ton:,.2f}</div>
            <div class="kpi-delta-pos">por tonelada entregue</div>
        </div>
        """, unsafe_allow_html=True)
    with rf2:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #0284c7;">
            <div class="kpi-label">Crédito ICMS Recuperado</div>
            <div class="kpi-value">R$ {icms_ton:,.2f}</div>
            <div class="kpi-delta-pos">economia fiscal/ton</div>
        </div>
        """, unsafe_allow_html=True)
    with rf3:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #f59e0b;">
            <div class="kpi-label">Pedágio + Descarga</div>
            <div class="kpi-value">R$ {(pedagio_ton + taxa_descarga):,.2f}</div>
            <div class="kpi-delta-neg">despesas acessórias/ton</div>
        </div>
        """, unsafe_allow_html=True)
    with rf4:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #475569;">
            <div class="kpi-label">Custo Total da Viagem</div>
            <div class="kpi-value">R$ {(frete_liquido_ton * carga_util):,.2f}</div>
            <div class="kpi-delta-pos">{carga_util} toneladas</div>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# MÓDULO 4: FORMAÇÃO DE PREÇO & DRE
# ==============================================================================
elif menu == "🎯 Formação de Preço & DRE":
    st.subheader("Formação de Preço de Venda e Margem de Contribuição")

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin-bottom:15px;">
            <div style="font-weight:700; color:#0f172a; margin-bottom:12px;">Custos Fabris e Quebras</div>
        """, unsafe_allow_html=True)
        c_mp = st.number_input("Custo de Matérias-Primas (R$/ton)", 500.0, 5000.0, 1690.0, 50.0)
        c_cif = st.number_input("GGF / CIF Industrial (R$/ton)", 0.0, 500.0, 115.0, 10.0)
        c_emb = st.number_input("Embalagem e Sacaria (R$/ton)", 0.0, 200.0, 42.0, 5.0)
        quebra = st.slider("Quebra Técnica / Ensaque (%)", 0.0, 4.0, 1.2, 0.1)
        st.markdown("</div>", unsafe_allow_html=True)

    with p_col2:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin-bottom:15px;">
            <div style="font-weight:700; color:#0f172a; margin-bottom:12px;">Deduções e Margem Alvo</div>
        """, unsafe_allow_html=True)
        icms_v = st.number_input("ICMS sobre Vendas (%)", 0.0, 18.0, 7.0, 0.5)
        pis_cof = st.number_input("PIS/COFINS Efetivo (%)", 0.0, 9.25, 3.65, 0.25)
        comissao = st.number_input("Comissão Comercial (%)", 0.0, 10.0, 3.0, 0.5)
        frete_out = st.number_input("Frete Outbound / Entrega (R$/ton)", 0.0, 300.0, 65.0, 5.0)
        margem_alvo = st.slider("Margem de Contribuição Desejada (%)", 5.0, 40.0, 18.0, 0.5)
        st.markdown("</div>", unsafe_allow_html=True)

    cpv_total = (c_mp * (1 + quebra / 100.0)) + c_cif + c_emb
    markup_div = 1.0 - ((icms_v + pis_cof + comissao + margem_alvo) / 100.0)
    preco_venda_ton = (cpv_total + frete_out) / markup_div if markup_div > 0 else cpv_total * 1.5

    v_icms = preco_venda_ton * (icms_v / 100.0)
    v_piscof = preco_venda_ton * (pis_cof / 100.0)
    v_comissao = preco_venda_ton * (comissao / 100.0)
    rec_liq = preco_venda_ton - v_icms - v_piscof
    margem_val = rec_liq - cpv_total - v_comissao - frete_out

    st.markdown("### Resultados Comerciais Sugeridos")
    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #047857;">
            <div class="kpi-label">Preço Sugerido / Tonelada</div>
            <div class="kpi-value">R$ {preco_venda_ton:,.2f}</div>
            <div class="kpi-delta-pos">Faturado com tributos</div>
        </div>
        """, unsafe_allow_html=True)
    with rc2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Preço Saca 40 kg</div>
            <div class="kpi-value">R$ {(preco_venda_ton/1000)*40:,.2f}</div>
            <div class="kpi-delta-pos">Base faturada</div>
        </div>
        """, unsafe_allow_html=True)
    with rc3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Preço Saca 25 kg</div>
            <div class="kpi-value">R$ {(preco_venda_ton/1000)*25:,.2f}</div>
            <div class="kpi-delta-pos">Base faturada</div>
        </div>
        """, unsafe_allow_html=True)
    with rc4:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #0284c7;">
            <div class="kpi-label">Margem de Contribuição</div>
            <div class="kpi-value">R$ {margem_val:,.2f}</div>
            <div class="kpi-delta-pos">{margem_alvo:.1f}% da receita bruta</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### Demonstração de Resultado (DRE Sintética por Tonelada)")
    dre_table = pd.DataFrame({
        "Estrutura DRE": [
            "(=) Receita Bruta de Venda",
            "(-) ICMS sobre Faturamento",
            "(-) PIS / COFINS",
            "(=) Receita Líquida Operacional",
            "(-) CPV Industrial (Insumos + CIF + Embalagem)",
            "(-) Comissões de Representação",
            "(-) Frete Outbound de Distribuição",
            "(=) Margem de Contribuição Gerencial"
        ],
        "Valor (R$/ton)": [
            preco_venda_ton, -v_icms, -v_piscof, rec_liq, -cpv_total, -v_comissao, -frete_out, margem_val
        ],
        "% da Receita": [
            100.0, -icms_v, -pis_cof, (rec_liq/preco_venda_ton)*100, -(cpv_total/preco_venda_ton)*100, -comissao, -(frete_out/preco_venda_ton)*100, (margem_val/preco_venda_ton)*100
        ]
    })
    st.dataframe(
        dre_table.style.format({"Valor (R$/ton)": "R$ {:,.2f}", "% da Receita": "{:,.2f}%"}),
        use_container_width=True
    )

# ==============================================================================
# MÓDULO 5: PONTO DE EQUILÍBRIO (BREAK-EVEN)
# ==============================================================================
elif menu == "📉 Ponto de Equilíbrio (Break-Even)":
    st.subheader("Análise de Ponto de Equilíbrio Operacional (Break-Even Point)")
    st.write("Determine o volume de vendas e o faturamento mínimo para cobrir a estrutura fixa da fábrica.")

    col_be1, col_be2 = st.columns(2)
    with col_be1:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin-bottom:15px;">
            <div style="font-weight:700; color:#0f172a; margin-bottom:12px;">Estrutura de Custos e Despesas Fixas (Mensal)</div>
        """, unsafe_allow_html=True)
        folha_fixa = st.number_input("Folha Salarial + Encargos (Indiretos/Admin) (R$)", 0.0, 2000000.0, 145000.0, 5000.0)
        manutencao_fabril = st.number_input("Manutenção Preventiva & Predial Fixa (R$)", 0.0, 500000.0, 35000.0, 2000.0)
        energia_demanda = st.number_input("Energia Elétrica (Demanda Contratada) (R$)", 0.0, 500000.0, 28000.0, 2000.0)
        despesas_admin = st.number_input("Despesas Administrativas, TI e Seguros (R$)", 0.0, 500000.0, 42000.0, 2000.0)
        depreciacao_maquinas = st.number_input("Depreciação de Máquinas e Galpões (R$)", 0.0, 500000.0, 30000.0, 2000.0)
        custo_fixo_total = folha_fixa + manutencao_fabril + energia_demanda + despesas_admin + depreciacao_maquinas
        st.markdown(f"**Custo Fixo Total Mensal:** `R$ {custo_fixo_total:,.2f}`")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_be2:
        st.markdown("""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin-bottom:15px;">
            <div style="font-weight:700; color:#0f172a; margin-bottom:12px;">Parâmetros Unitários e Volume Atual</div>
        """, unsafe_allow_html=True)
        preco_venda_medio = st.number_input("Preço de Venda Faturado Médio (R$/ton)", 500.0, 6000.0, 2450.0, 50.0)
        custo_variavel_ton = st.number_input("Custo Variável Unitário (CPV + Impostos + Frete) (R$/ton)", 300.0, 5000.0, 1980.0, 50.0)
        volume_atual_fabrica = st.number_input("Volume Mensal Atual de Produção (Toneladas)", 100.0, 20000.0, 850.0, 50.0)
        
        margem_contrib_unit = preco_venda_medio - custo_variavel_ton
        margem_contrib_ratio = (margem_contrib_unit / preco_venda_medio) if preco_venda_medio > 0 else 0
        st.markdown(f"**Margem de Contribuição Unitária:** `R$ {margem_contrib_unit:,.2f}/ton` (`{margem_contrib_ratio*100:.1f}%`)")
        st.markdown("</div>", unsafe_allow_html=True)

    if margem_contrib_unit > 0:
        pe_toneladas = custo_fixo_total / margem_contrib_unit
        pe_sacas_40kg = (pe_toneladas * 1000.0) / 40.0
        pe_sacas_25kg = (pe_toneladas * 1000.0) / 25.0
        pe_faturamento = pe_toneladas * preco_venda_medio
        margem_seguranca_pct = ((volume_atual_fabrica - pe_toneladas) / volume_atual_fabrica) * 100.0
    else:
        pe_toneladas = 0.0
        pe_sacas_40kg = 0.0
        pe_sacas_25kg = 0.0
        pe_faturamento = 0.0
        margem_seguranca_pct = -100.0

    st.markdown("### Indicadores do Ponto de Equilíbrio Operacional")
    be1, be2, be3, be4 = st.columns(4)
    with be1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #047857;">
            <div class="kpi-label">Ponto de Equilíbrio (PE)</div>
            <div class="kpi-value">{pe_toneladas:,.1f} ton</div>
            <div class="kpi-delta-pos">Volume mínimo de vendas</div>
        </div>
        """, unsafe_allow_html=True)
    with be2:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #0284c7;">
            <div class="kpi-label">Sacas de 40 kg</div>
            <div class="kpi-value">{pe_sacas_40kg:,.0f} sc</div>
            <div class="kpi-delta-pos">ou {pe_sacas_25kg:,.0f} sc de 25kg</div>
        </div>
        """, unsafe_allow_html=True)
    with be3:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: #f59e0b;">
            <div class="kpi-label">Receita Mínima Mensal</div>
            <div class="kpi-value">R$ {pe_faturamento:,.2f}</div>
            <div class="kpi-delta-pos">Faturamento de cobertura</div>
        </div>
        """, unsafe_allow_html=True)
    with be4:
        cor_seguranca = "#059669" if margem_seguranca_pct >= 0 else "#dc2626"
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color: {cor_seguranca};">
            <div class="kpi-label">Margem de Segurança</div>
            <div class="kpi-value" style="color:{cor_seguranca};">{margem_seguranca_pct:+.1f}%</div>
            <div class="{'kpi-delta-pos' if margem_seguranca_pct >= 0 else 'kpi-delta-neg'}">
                {'Operação Superavitária' if margem_seguranca_pct >= 0 else 'Operação em Prejuízo'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("Gráfico Interativo de Cruzamento Operacional")
    
    max_volume = max(volume_atual_fabrica, pe_toneladas) * 1.6
    volume_axis = np.linspace(0, max_volume, 60)
    receita_total = volume_axis * preco_venda_medio
    custo_total = custo_fixo_total + (volume_axis * custo_variavel_ton)
    custo_fixo_linha = np.full_like(volume_axis, custo_fixo_total)

    fig_be = go.Figure()

    fig_be.add_trace(go.Scatter(
        x=volume_axis, y=custo_fixo_linha,
        mode="lines", name="Custos Fixos",
        line=dict(color="#64748b", width=2, dash="dash")
    ))

    fig_be.add_trace(go.Scatter(
        x=volume_axis, y=custo_total,
        mode="lines", name="Custos Totais (Fixo + Variável)",
        line=dict(color="#dc2626", width=3)
    ))

    fig_be.add_trace(go.Scatter(
        x=volume_axis, y=receita_total,
        mode="lines", name="Receita Bruta Total",
        line=dict(color="#047857", width=3)
    ))

    fig_be.add_trace(go.Scatter(
        x=[pe_toneladas], y=[pe_faturamento],
        mode="markers+text", name="Ponto de Equilíbrio",
        marker=dict(color="#f59e0b", size=14, symbol="diamond"),
        text=[f"  PE: {pe_toneladas:,.1f} ton"],
        textposition="top left",
        textfont=dict(color="#0f172a", size=12, family="Inter")
    ))

    receita_atual = volume_atual_fabrica * preco_venda_medio
    fig_be.add_trace(go.Scatter(
        x=[volume_atual_fabrica], y=[receita_atual],
        mode="markers+text", name="Volume Atual de Produção",
        marker=dict(color="#2563eb", size=12, symbol="circle"),
        text=[f"  Atual: {volume_atual_fabrica:,.0f} ton"],
        textposition="bottom right",
        textfont=dict(color="#1d4ed8", size=12, family="Inter")
    ))

    fig_be.update_layout(
        title="Curva de Equilíbrio Operacional: Receita vs. Custos Totais",
        xaxis_title="Volume Faturado (Toneladas)",
        yaxis_title="Montante Financeiro (R$)",
        hovermode="x unified",
        height=480,
        plot_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_be, use_container_width=True)

# ==============================================================================
# MÓDULO 6: MATRIZ DE SENSIBILIDADE
# ==============================================================================
elif menu == "🌪️ Matriz de Sensibilidade (What-If)":
    st.subheader("Matriz de Estresse de Portfólio (Milho vs. Dólar)")
    st.write("Simule a sensibilidade do custo final por tonelada cruzando diferentes cenários de commodities e câmbio.")

    s1, s2, s3 = st.columns(3)
    base_ton = s1.number_input("Custo Atual por Tonelada (R$)", 500.0, 5000.0, 1850.0, 50.0)
    p_milho = s2.slider("Participação do Milho no Custo Total (%)", 30.0, 80.0, 58.0, 1.0)
    p_usd = s3.slider("Participação de Itens Dolarizados (%)", 0.0, 25.0, 8.0, 0.5)

    var_milho = [-20, -10, -5, 0, 5, 10, 20]
    var_usd = [-15, -10, 0, 10, 15]

    mat = np.zeros((len(var_usd), len(var_milho)))
    for i, u in enumerate(var_usd):
        for j, m in enumerate(var_milho):
            mat[i, j] = base_ton * (1.0 + (p_milho / 100.0) * (m / 100.0) + (p_usd / 100.0) * (u / 100.0))

    df_stress = pd.DataFrame(
        mat,
        index=[f"Dólar {u:+d}%" for u in var_usd],
        columns=[f"Milho {m:+d}%" for m in var_milho]
    )

    try:
        st.dataframe(
            df_stress.style.format("R$ {:,.2f}").background_gradient(cmap="YlOrRd"),
            use_container_width=True
        )
    except Exception:
        st.dataframe(
            df_stress.style.format("R$ {:,.2f}"),
            use_container_width=True
        )

    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_stress.to_excel(writer, sheet_name="Matriz de Sensibilidade")
    excel_buf.seek(0)

    st.download_button(
        label="📥 Baixar Matriz de Sensibilidade em Excel (.xlsx)",
        data=excel_buf,
        file_name="matriz_sensibilidade_agrocost.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
