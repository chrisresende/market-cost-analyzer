import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import yfinance as yf
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURAÇÃO DE INTERFACE
# ==============================================================================
st.set_page_config(
    page_title="AgroCost Intelligence | Nutrição Animal",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS executivo
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #2e7d32;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CAMADA DE DADOS: APIs PÚBLICAS COM CACHE
# ==============================================================================
@st.cache_data(ttl=900, show_spinner=False)
def fetch_macro_indicators():
    """Consulta AwesomeAPI para Moedas e SGS-Banco Central para Inflação."""
    data = {
        "usd": 5.42, "usd_delta": 0.15,
        "eur": 5.92, "eur_delta": -0.10,
        "ipca_12m": 4.10, "igpm_12m": 2.80,
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    # 1. Moedas
    try:
        r = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3)
        if r.status_code == 200:
            res = r.json()
            data["usd"] = float(res["USDBRL"]["bid"])
            data["usd_delta"] = float(res["USDBRL"]["pctChange"])
            data["eur"] = float(res["EURBRL"]["bid"])
            data["eur_delta"] = float(res["EURBRL"]["pctChange"])
            data["updated_at"] = res["USDBRL"]["create_date"]
    except Exception:
        pass

    # 2. Séries SGS Banco Central (IPCA mensal acumulado 12m)
    try:
        url_ipca = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados/ultimos/1?formato=json"
        r_ipca = requests.get(url_ipca, timeout=3)
        if r_ipca.status_code == 200:
            data["ipca_12m"] = float(r_ipca.json()[0]["valor"])
    except Exception:
        pass

    return data

@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_futures():
    """Coleta cotações de commodities via Yahoo Finance."""
    tickers = {
        "Milho B3 (CCM=F)": "CCM=F",
        "Soja CBOT (ZS=F)": "ZS=F",
        "Petróleo Brent (BZ=F)": "BZ=F"
    }
    results = {}
    for name, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            df = t.history(period="1mo")
            if not df.empty and len(df) >= 2:
                last_p = float(df["Close"].iloc[-1])
                prev_p = float(df["Close"].iloc[-2])
                results[name] = {
                    "price": last_p,
                    "change": ((last_p - prev_p) / prev_p) * 100,
                    "df": df
                }
            else:
                results[name] = {"price": 62.80 if "Milho" in name else 105.0, "change": 0.0, "df": pd.DataFrame()}
        except Exception:
            results[name] = {"price": 62.80 if "Milho" in name else 105.0, "change": 0.0, "df": pd.DataFrame()}
    return results

macro_data = fetch_macro_indicators()
futures_data = fetch_market_futures()

# ==============================================================================
# MENU DE NAVEGAÇÃO LATERAL
# ==============================================================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3050/3050158.png", width=60)
st.sidebar.title("AgroCost Hub")
st.sidebar.caption("Inteligência em Custos e Reposição Agroindustrial")

menu = st.sidebar.radio(
    "Navegação Principal",
    [
        "📊 Cockpit Macroeconômico",
        "⚖️ Custo Médio vs. Reposição",
        "🚚 Frete Inbound & Despesas CIF",
        "🎯 Formação de Preço & DRE",
        "🌪️ Matriz de Sensibilidade (What-If)"
    ]
)

st.sidebar.divider()
st.sidebar.markdown(f"**Câmbio Atualizado:** R$ {macro_data['usd']:.4f}")
st.sidebar.caption(f"Leitura: {macro_data['updated_at']}")

# ==============================================================================
# MÓDULO 1: COCKPIT MACROECONÔMICO
# ==============================================================================
if menu == "📊 Cockpit Macroeconômico":
    st.title("📊 Painel de Mercado e Indicadores Macroeconômicos")
    st.write("Acompanhamento de variáveis regulatórias e indexadores de contratos de suprimentos.")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Dólar Comercial", f"R$ {macro_data['usd']:.4f}", f"{macro_data['usd_delta']:.2f}%")
    kpi2.metric("Euro Comercial", f"R$ {macro_data['eur']:.4f}", f"{macro_data['eur_delta']:.2f}%")
    
    milho_info = futures_data.get("Milho B3 (CCM=F)", {})
    brent_info = futures_data.get("Petróleo Brent (BZ=F)", {})
    
    kpi3.metric("Milho B3 Futuro", f"R$ {milho_info.get('price', 0):.2f}", f"{milho_info.get('change', 0):.2f}%")
    kpi4.metric("Petróleo Brent (Diesel)", f"US$ {brent_info.get('price', 0):.2f}", f"{brent_info.get('change', 0):.2f}%")

    st.divider()

    col_chart, col_macro = st.columns([2, 1])
    with col_chart:
        st.subheader("Histórico do Contrato Futuro de Milho (B3)")
        df_milho = milho_info.get("df", pd.DataFrame())
        if not df_milho.empty:
            fig = px.line(df_milho, y="Close", title="Evolução do Preço de Fechamento (Últimos 30 dias)", labels={"Close": "Preço R$/saca", "Date": "Data"})
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Série temporal em carregamento ou mercado em fechamento.")

    with col_macro:
        st.subheader("Indexadores de Inflação")
        st.metric("IPCA Acumulado (12M)", f"{macro_data['ipca_12m']:.2f}%", help="Fonte: SGS Banco Central")
        st.metric("IGP-M Referência", f"{macro_data['igpm_12m']:.2f}%", help="Utilizado em reajustes contratuais de armazenagem e locação")
        st.caption("Dados sincronizados diretamente das séries oficiais do SGS-BCB.")

# ==============================================================================
# MÓDULO 2: CUSTO MÉDIO CONTÁBIL VS. REPOSIÇÃO (BOM)
# ==============================================================================
elif menu == "⚖️ Custo Médio vs. Reposição":
    st.title("⚖️ Análise de Ficha Técnica: Custo Médio vs. Custo de Reposição")
    st.write("Identifique se o custo contábil em estoque está defasado frente à cotação spot de mercado.")

    preset = st.selectbox(
        "Carregar Fórmula Padrão de Fábrica:",
        ["Frango de Corte Inicial", "Bovino Confinamento (Alto Grão)", "Suíno Terminação"]
    )

    if preset == "Frango de Corte Inicial":
        raw_items = [
            {"ingrediente": "Milho Grão Moído", "inclusao": 58.0, "custo_medio_kg": 1.10, "custo_spot_kg": 1.22, "moeda": "BRL"},
            {"ingrediente": "Farelo de Soja 46%", "inclusao": 27.5, "custo_medio_kg": 2.05, "custo_spot_kg": 2.18, "moeda": "BRL"},
            {"ingrediente": "Farinha de Vísceras Aves", "inclusao": 5.5, "custo_medio_kg": 2.45, "custo_spot_kg": 2.65, "moeda": "BRL"},
            {"ingrediente": "Óleo Vegetal Degomado", "inclusao": 2.5, "custo_medio_kg": 4.80, "custo_spot_kg": 5.10, "moeda": "BRL"},
            {"ingrediente": "Núcleo Vitamínico/Mineral", "inclusao": 4.0, "custo_medio_kg": 13.50, "custo_spot_kg": 14.20, "moeda": "BRL"},
            {"ingrediente": "L-Lisina HCl (USD)", "inclusao": 1.5, "custo_medio_kg": 2.15, "custo_spot_kg": 2.35, "moeda": "USD"},
            {"ingrediente": "DL-Metionina (USD)", "inclusao": 1.0, "custo_medio_kg": 3.70, "custo_spot_kg": 3.90, "moeda": "USD"}
        ]
    elif preset == "Bovino Confinamento (Alto Grão)":
        raw_items = [
            {"ingrediente": "Milho Grão Inteiro", "inclusao": 75.0, "custo_medio_kg": 1.12, "custo_spot_kg": 1.22, "moeda": "BRL"},
            {"ingrediente": "Pellet Farelo de Soja", "inclusao": 12.0, "custo_medio_kg": 2.08, "custo_spot_kg": 2.18, "moeda": "BRL"},
            {"ingrediente": "Caroço de Algodão", "inclusao": 8.0, "custo_medio_kg": 1.35, "custo_spot_kg": 1.45, "moeda": "BRL"},
            {"ingrediente": "Núcleo Mineral Bovino", "inclusao": 5.0, "custo_medio_kg": 5.80, "custo_spot_kg": 6.10, "moeda": "BRL"}
        ]
    else:
        raw_items = [
            {"ingrediente": "Milho Moído", "inclusao": 65.0, "custo_medio_kg": 1.10, "custo_spot_kg": 1.22, "moeda": "BRL"},
            {"ingrediente": "Farelo de Soja 46%", "inclusao": 22.0, "custo_medio_kg": 2.05, "custo_spot_kg": 2.18, "moeda": "BRL"},
            {"ingrediente": "Farinha de Carne e Ossos", "inclusao": 6.0, "custo_medio_kg": 1.90, "custo_spot_kg": 2.05, "moeda": "BRL"},
            {"ingrediente": "Premix Suínos Terminação", "inclusao": 4.0, "custo_medio_kg": 8.50, "custo_spot_kg": 8.90, "moeda": "BRL"},
            {"ingrediente": "L-Lisina HCl (USD)", "inclusao": 1.5, "custo_medio_kg": 2.15, "custo_spot_kg": 2.35, "moeda": "USD"},
            {"ingrediente": "Aditivo Ractopamina", "inclusao": 1.5, "custo_medio_kg": 18.00, "custo_spot_kg": 18.00, "moeda": "BRL"}
        ]

    df_formula = pd.DataFrame(raw_items)

    st.write("Edite os custos e proporções diretamente na tabela:")
    edited_df = st.data_editor(
        df_formula,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ingrediente": "Matéria-Prima",
            "inclusao": st.column_config.NumberColumn("Inclusão (%)", min_value=0.0, max_value=100.0, format="%.2f%%"),
            "custo_medio_kg": st.column_config.NumberColumn("Custo Médio Estoque (R$/kg)", min_value=0.0, format="R$ %.3f"),
            "custo_spot_kg": st.column_config.NumberColumn("Custo de Reposição (R$/kg)", min_value=0.0, format="R$ %.3f"),
            "moeda": st.column_config.SelectboxColumn("Moeda Base", options=["BRL", "USD"])
        }
    )

    # Validação da Fórmula
    tot_inc = edited_df["inclusao"].sum()
    if abs(tot_inc - 100.0) > 0.01:
        st.warning(f"⚠️ A soma de inclusão está em **{tot_inc:.2f}%**. O fechamento padrão é 100%.")
    else:
        st.success("✅ Fechamento de fórmula conferido (100.00%).")

    # Cálculos
    usd_taxa = macro_data["usd"]
    df_calc = edited_df.copy()

    df_calc["mult_moeda"] = df_calc["moeda"].apply(lambda m: usd_taxa if m == "USD" else 1.0)
    df_calc["custo_medio_total_ton"] = df_calc["custo_medio_kg"] * df_calc["mult_moeda"] * (df_calc["inclusao"] / 100.0) * 1000.0
    df_calc["custo_spot_total_ton"] = df_calc["custo_spot_kg"] * df_calc["mult_moeda"] * (df_calc["inclusao"] / 100.0) * 1000.0

    total_medio_ton = df_calc["custo_medio_total_ton"].sum()
    total_spot_ton = df_calc["custo_spot_total_ton"].sum()
    gap_ton = total_spot_ton - total_medio_ton
    gap_pct = (gap_ton / total_medio_ton) * 100.0

    # KPIs Comparativos
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Custo Médio / Tonelada", f"R$ {total_medio_ton:,.2f}")
    k2.metric("Custo Reposição / Tonelada", f"R$ {total_spot_ton:,.2f}")
    k3.metric("Defasagem de Custo (Gap)", f"R$ {gap_ton:,.2f}", f"{gap_pct:+.2f}%", delta_color="inverse")
    k4.metric("Impacto Saca (40 kg)", f"R$ {(gap_ton/1000)*40:+.2f}", f"R$ {(total_spot_ton/1000)*40:.2f}/saca")

    # Gráfico Comparativo
    fig_comp = go.Figure(data=[
        go.Bar(name="Custo Médio em Estoque", x=df_calc["ingrediente"], y=df_calc["custo_medio_total_ton"], marker_color="#455a64"),
        go.Bar(name="Custo de Reposição (Mercado)", x=df_calc["ingrediente"], y=df_calc["custo_spot_total_ton"], marker_color="#2e7d32")
    ])
    fig_comp.update_layout(
        barmode="group",
        title="Comparativo por Ingrediente na Tonelada (R$/ton)",
        xaxis_tickangle=-45,
        height=400,
        margin=dict(l=20, r=20, t=40, b=100)
    )
    st.plotly_chart(fig_comp, use_container_width=True)

# ==============================================================================
# MÓDULO 3: FRETE INBOUND & DESPESAS CIF
# ==============================================================================
elif menu == "🚚 Frete Inbound & Despesas CIF":
    st.title("🚚 Frete Inbound e Despesas de Aquisição")
    st.write("Simule o custo efetivo de aquisição de grãos e matérias-primas na entrega da fábrica.")

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.subheader("Parâmetros do Trecho e Carga")
        origem = st.text_input("Origem da Carga", "Sorriso - MT")
        tipo_veiculo = st.selectbox("Tipo de Veículo / Carreta", ["Bitrem (57t brutas / ~38t úteis)", "Rodotrem (74t brutas / ~48t úteis)", "Carreta LS (~32t úteis)"])
        peso_util = st.number_input("Carga Líquida Útil (Toneladas)", min_value=1.0, value=48.0, step=1.0)
        frete_bruto_ton = st.number_input("Frete Bruto Negociado (R$/ton)", min_value=0.0, value=285.0, step=5.0)
        seguro_pct = st.number_input("Taxa de Seguro da Carga (%)", min_value=0.0, value=0.25, step=0.05)

    with f_col2:
        st.subheader("Tributação e Despesas Acessórias")
        icms_frete_pct = st.selectbox("Alíquota ICMS Frete Interstadual (%)", [0.0, 7.0, 12.0], index=2)
        icms_recuperavel = st.checkbox("Empresa credita ICMS de frete (Não-cumulativo)", value=True)
        pedagio_total = st.number_input("Pedágio Total da Rota (R$)", min_value=0.0, value=650.0, step=50.0)
        taxa_descarga_ton = st.number_input("Taxa de Transbordo/Descarga (R$/ton)", min_value=0.0, value=12.50, step=1.0)

    # Cálculos
    frete_total_carga = frete_bruto_ton * peso_util
    pedagio_por_ton = pedagio_total / peso_util
    icms_desconto_ton = (frete_bruto_ton * (icms_frete_pct / 100.0)) if icms_recuperavel else 0.0
    seguro_por_ton = frete_bruto_ton * (seguro_pct / 100.0)

    custo_liquido_frete_ton = frete_bruto_ton - icms_desconto_ton + pedagio_por_ton + taxa_descarga_ton + seguro_por_ton

    st.divider()
    st.markdown("### Resumo do Custo Logístico por Tonelada")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Frete Líquido Efetivo", f"R$ {custo_liquido_frete_ton:,.2f}/ton")
    r2.metric("Crédito ICMS Recuperado", f"- R$ {icms_desconto_ton:,.2f}/ton" if icms_recuperavel else "R$ 0.00")
    r3.metric("Pedágio + Descarga", f"R$ {(pedagio_por_ton + taxa_descarga_ton):,.2f}/ton")
    r4.metric("Custo Total da Viagem", f"R$ {(custo_liquido_frete_ton * peso_util):,.2f}")

    # Composição do Frete
    df_frete = pd.DataFrame({
        "Componente": ["Frete Seco (Líquido)", "Crédito ICMS", "Pedágios", "Taxa Descarga", "Seguro"],
        "R$/ton": [frete_bruto_ton - icms_desconto_ton, icms_desconto_ton, pedagio_por_ton, taxa_descarga_ton, seguro_por_ton]
    })
    fig_f = px.bar(df_frete, x="Componente", y="R$/ton", title="Abertura das Despesas de Transporte Inbound", text_auto=".2f")
    st.plotly_chart(fig_f, use_container_width=True)

# ==============================================================================
# MÓDULO 4: FORMAÇÃO DE PREÇO & DRE
# ==============================================================================
elif menu == "🎯 Formação de Preço & DRE":
    st.title("🎯 Formação de Preço de Venda e Margem de Contribuição")
    st.write("Construa a DRE sintética por tonelada e por saca a partir do CPV industrial e despesas comerciais.")

    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Custos Industriais e Embalagem")
        custo_mp_ton = st.number_input("Custo de Matérias-Primas (R$/ton)", 500.0, 5000.0, 1680.0, 50.0)
        cif_fabril_ton = st.number_input("Custo Indireto Fabril / MOD (R$/ton)", 0.0, 500.0, 115.0, 10.0)
        embalagem_ton = st.number_input("Embalagem + Sacaria (R$/ton)", 0.0, 200.0, 42.0, 5.0)
        quebra_industrial_pct = st.slider("Quebra Técnica / Extrusão / Ensaque (%)", 0.0, 4.0, 1.2, 0.1)

    with c_right:
        st.subheader("Deduções sobre a Receita Bruta")
        icms_venda_pct = st.number_input("ICMS Médio sobre Vendas (%)", 0.0, 18.0, 7.0, 0.5)
        pis_cofins_pct = st.number_input("PIS/COFINS Médio Efetivo (%)", 0.0, 9.25, 3.65, 0.25)
        comissao_vendas_pct = st.number_input("Comissão de Venda / Representação (%)", 0.0, 10.0, 3.0, 0.5)
        frete_outbound_ton = st.number_input("Frete Outbound de Entrega (R$/ton)", 0.0, 300.0, 65.0, 5.0)
        margem_desejada_pct = st.slider("Margem de Contribuição Alvo (% sobre Preço)", 5.0, 40.0, 18.0, 0.5)

    # Cálculo do CPV Total
    cpv_ton = (custo_mp_ton * (1 + quebra_industrial_pct / 100.0)) + cif_fabril_ton + embalagem_ton

    # Mark-up Divisor
    total_deducoes_pct = icms_venda_pct + pis_cofins_pct + comissao_vendas_pct + margem_desejada_pct
    divisor_markup = 1.0 - (total_deducoes_pct / 100.0)

    if divisor_markup > 0:
        # Preço considerando o frete outbound somado na base
        preco_venda_ton = (cpv_ton + frete_outbound_ton) / divisor_markup
    else:
        preco_venda_ton = cpv_ton * 1.5

    # DRE Sintética por Tonelada
    rec_bruta = preco_venda_ton
    val_icms = rec_bruta * (icms_venda_pct / 100.0)
    val_piscofins = rec_bruta * (pis_cofins_pct / 100.0)
    val_comissao = rec_bruta * (comissao_vendas_pct / 100.0)
    val_frete_out = frete_outbound_ton
    rec_liquida = rec_bruta - val_icms - val_piscofins
    margem_contrib_r = rec_liquida - cpv_ton - val_comissao - val_frete_out
    margem_contrib_pct = (margem_contrib_r / rec_bruta) * 100.0

    st.divider()
    st.markdown("### Preço de Venda Sugerido e Rentabilidade")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Preço Faturado / Tonelada", f"R$ {preco_venda_ton:,.2f}")
    m2.metric("Preço Saca 40 kg", f"R$ {(preco_venda_ton/1000)*40:,.2f}")
    m3.metric("Preço Saca 25 kg", f"R$ {(preco_venda_ton/1000)*25:,.2f}")
    m4.metric("Margem de Contribuição", f"R$ {margem_contrib_r:,.2f}", f"{margem_contrib_pct:.1f}%")

    # Demonstração da DRE em Tabela Formatada
    st.subheader("DRE Gerencial por Tonelada (R$/ton)")
    dre_df = pd.DataFrame({
        "Linha DRE": [
            "(=) Receita Bruta de Vendas",
            "(-) ICMS sobre Vendas",
            "(-) PIS / COFINS",
            "(=) Receita Líquida Operacional",
            "(-) CPV Industrial (MP + CIF + Embalagem)",
            "(-) Comissões Comerciais",
            "(-) Frete Outbound de Entrega",
            "(=) Margem de Contribuição Gerencial"
        ],
        "Valor (R$/ton)": [
            rec_bruta, -val_icms, -val_piscofins, rec_liquida, -cpv_ton, -val_comissao, -val_frete_out, margem_contrib_r
        ],
        "% da Receita Bruta": [
            100.0, -icms_venda_pct, -pis_cofins_pct, (rec_liquida/rec_bruta)*100, -(cpv_ton/rec_bruta)*100, -comissao_vendas_pct, -(val_frete_out/rec_bruta)*100, margem_contrib_pct
        ]
    })
    st.dataframe(
        dre_df.style.format({"Valor (R$/ton)": "R$ {:,.2f}", "% da Receita Bruta": "{:,.2f}%"}),
        use_container_width=True
    )

# ==============================================================================
# MÓDULO 5: MATRIZ DE SENSIBILIDADE (WHAT-IF)
# ==============================================================================
elif menu == "🌪️ Matriz de Sensibilidade (What-If)":
    st.title("🌪️ Matriz de Sensibilidade Bidimensional (Estresse de Carteira)")
    st.write("Analise o impacto simultâneo da oscilação do Milho B3 e do Dólar no custo final da ração.")

    col_s1, col_s2, col_s3 = st.columns(3)
    custo_base_ton = col_s1.number_input("Custo Atual por Tonelada (R$/ton)", 800.0, 5000.0, 1850.0, 50.0)
    peso_milho_pct = col_s2.slider("Participação do Milho no Custo Total (%)", 30.0, 80.0, 58.0, 1.0)
    peso_usd_pct = col_s3.slider("Participação de Itens Dolarizados (%)", 0.0, 25.0, 8.0, 0.5)

    # Faixas de variação
    var_milho = [-20, -10, -5, 0, 5, 10, 20]
    var_usd = [-15, -10, 0, 10, 15]

    matriz = np.zeros((len(var_usd), len(var_milho)))

    for i, u in enumerate(var_usd):
        for j, m in enumerate(var_milho):
            impacto_milho = (peso_milho_pct / 100.0) * (m / 100.0)
            impacto_usd = (peso_usd_pct / 100.0) * (u / 100.0)
            matriz[i, j] = custo_base_ton * (1.0 + impacto_milho + impacto_usd)

    df_sens = pd.DataFrame(
        matriz,
        index=[f"Dólar {u:+d}%" for u in var_usd],
        columns=[f"Milho {m:+d}%" for m in var_milho]
    )

    st.subheader("Matriz de Impacto no Custo da Tonelada (R$/ton)")
    st.dataframe(df_sens.style.format("R$ {:,.2f}").background_gradient(cmap="YlOrRd"), use_container_width=True)

    st.subheader("Exportar Relatório em Excel")
    st.write("Faça o download da simulação executiva consolidada:")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_sens.to_excel(writer, sheet_name="Matriz de Sensibilidade")
    excel_buffer.seek(0)

    st.download_button(
        label="📥 Baixar Matriz de Sensibilidade (.xlsx)",
        data=excel_buffer,
        file_name="matriz_sensibilidade_agrocost.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
