
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Market Cost Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

    /* ===== FUNDO PRINCIPAL ===== */

    .stApp {
        background: #f4f6f8;
    }

    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* ===== SIDEBAR ===== */

    section[data-testid="stSidebar"] {
        background: #17212b !important;
        border-right: 1px solid #273646;
    }

    section[data-testid="stSidebar"] > div {
        background: #17212b !important;
    }

    section[data-testid="stSidebar"] * {
        color: #f3f6f9 !important;
    }

    section[data-testid="stSidebar"] .stMarkdown p {
        color: #d9e1e8 !important;
    }

    section[data-testid="stSidebar"] label {
        color: #f3f6f9 !important;
        font-weight: 500;
    }

    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        color: #17212b !important;
        background: white !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #17212b !important;
        border-radius: 7px;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
        color: #17212b !important;
    }

    section[data-testid="stSidebar"] .stNumberInput input {
        color: #17212b !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #344554 !important;
    }

    section[data-testid="stSidebar"] button {
        border-radius: 7px;
    }

    /* ===== HEADER ===== */

    .app-header {
        background: white;
        border: 1px solid #e1e6eb;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .app-title {
        font-size: 28px;
        font-weight: 700;
        color: #17212b;
        margin-bottom: 3px;
    }

    .app-subtitle {
        color: #697586;
        font-size: 14px;
    }

    .online {
        background: #e8f7ee;
        color: #16794c;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }

    /* ===== CARDS ===== */

    .metric-card {
        background: white;
        border: 1px solid #e1e6eb;
        border-radius: 10px;
        padding: 15px 17px;
        min-height: 105px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.035);
    }

    .metric-label {
        color: #718096;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .4px;
    }

    .metric-value {
        color: #17212b;
        font-size: 24px;
        font-weight: 700;
        margin-top: 6px;
    }

    .metric-desc {
        color: #7b8794;
        font-size: 12px;
        margin-top: 4px;
    }

    /* ===== INTERPRETAÇÃO ===== */

    .interpretation {
        background: white;
        border: 1px solid #dfe5eb;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 7px rgba(0,0,0,.035);
    }

    .interpretation-title {
        font-size: 18px;
        font-weight: 700;
        color: #17212b;
        margin-bottom: 8px;
    }

    .interpretation-text {
        color: #45515d;
        font-size: 14px;
        line-height: 1.65;
    }

    /* ===== SEMÁFORO ===== */

    .factor {
        background: white;
        border: 1px solid #e1e6eb;
        border-radius: 9px;
        padding: 13px 15px;
        margin-bottom: 8px;
    }

    .factor-title {
        font-weight: 700;
        color: #28323c;
        font-size: 14px;
    }

    .factor-text {
        color: #6b7682;
        font-size: 12px;
        margin-top: 4px;
    }

    /* ===== CENÁRIOS ===== */

    .scenario {
        background: white;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #e1e6eb;
        min-height: 155px;
    }

    .scenario-title {
        font-size: 15px;
        font-weight: 700;
        color: #27323d;
    }

    .scenario-price {
        font-size: 22px;
        font-weight: 700;
        margin-top: 8px;
    }

    .scenario-text {
        font-size: 12px;
        color: #697586;
        line-height: 1.5;
        margin-top: 7px;
    }

    /* ===== TÍTULOS ===== */

    .section-title {
        font-size: 19px;
        font-weight: 700;
        color: #17212b;
        margin-top: 15px;
        margin-bottom: 10px;
    }

    /* ===== ALERTAS ===== */

    .simple-alert {
        border-radius: 9px;
        padding: 13px 15px;
        margin-bottom: 8px;
        font-size: 13px;
        line-height: 1.5;
    }

    /* ===== TABELAS ===== */

    .dataframe {
        font-size: 13px !important;
    }

</style>
""", unsafe_allow_html=True)

# ============================================================
# FUNÇÕES
# ============================================================

@st.cache_data(ttl=300)
def baixar_dados(ativo, periodo, intervalo):

    try:

        df = yf.download(
            ativo,
            period=periodo,
            interval=intervalo,
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        colunas = ["Open", "High", "Low", "Close", "Volume"]

        df = df[[c for c in colunas if c in df.columns]]

        return df.dropna()

    except Exception:
        return pd.DataFrame()


def calcular_indicadores(df):

    df = df.copy()

    close = pd.Series(
        df["Close"].values,
        index=df.index,
        dtype="float64"
    )

    high = pd.Series(
        df["High"].values,
        index=df.index,
        dtype="float64"
    )

    low = pd.Series(
        df["Low"].values,
        index=df.index,
        dtype="float64"
    )

    # Médias
    df["SMA20"] = close.rolling(20).mean()
    df["EMA21"] = close.ewm(span=21, adjust=False).mean()

    # RSI
    delta = close.diff()

    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    media_ganho = ganho.rolling(14).mean()
    media_perda = perda.rolling(14).mean()

    rs = media_ganho / media_perda.replace(0, np.nan)

    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df["ATR"] = tr.rolling(14).mean()

    # Retornos / volatilidade
    retornos = close.pct_change()

    df["VOLATILIDADE"] = (
        retornos.rolling(20).std() * np.sqrt(252) * 100
    )

    # Volume médio
    df["VOLUME_MEDIA"] = df["Volume"].rolling(20).mean()

    return df


def fibonacci_automatico(df):

    dados = df.tail(min(150, len(df)))

    maxima = float(dados["High"].max())
    minima = float(dados["Low"].min())

    distancia = maxima - minima

    retr = {
        "0%": maxima,
        "23.6%": maxima - distancia * 0.236,
        "38.2%": maxima - distancia * 0.382,
        "50%": maxima - distancia * 0.500,
        "61.8%": maxima - distancia * 0.618,
        "78.6%": maxima - distancia * 0.786,
        "100%": minima
    }

    ext = {
        "127.2%": maxima + distancia * 0.272,
        "161.8%": maxima + distancia * 0.618,
        "200%": maxima + distancia,
        "261.8%": maxima + distancia * 1.618
    }

    return minima, maxima, retr, ext


def interpretar(df):

    ultimo = df.iloc[-1]

    preco = float(ultimo["Close"])
    sma = float(ultimo["SMA20"])
    ema = float(ultimo["EMA21"])
    rsi = float(ultimo["RSI"])
    macd = float(ultimo["MACD"])
    signal = float(ultimo["MACD_SIGNAL"])
    atr = float(ultimo["ATR"])
    vol = float(ultimo["VOLATILIDADE"])

    volume = float(ultimo["Volume"])
    volume_medio = float(ultimo["VOLUME_MEDIA"])

    fatores = []

    pontos_alta = 0
    pontos_baixa = 0

    # Tendência
    if preco > sma and preco > ema:
        tendencia = "Alta"
        pontos_alta += 2
        fatores.append((
            "🟢",
            "Tendência",
            "O preço está acima das principais médias de curto prazo."
        ))

    elif preco < sma and preco < ema:
        tendencia = "Baixa"
        pontos_baixa += 2
        fatores.append((
            "🔴",
            "Tendência",
            "O preço está abaixo das principais médias de curto prazo."
        ))

    else:
        tendencia = "Mista"
        fatores.append((
            "🟡",
            "Tendência",
            "O preço está entre as principais médias, indicando indefinição."
        ))

    # RSI
    if rsi >= 70:
        leitura_rsi = "sobrecomprado"
        fatores.append((
            "🟡",
            "Força do movimento",
            f"RSI em {rsi:.1f}: o mercado está mais esticado na alta."
        ))

    elif rsi <= 30:
        leitura_rsi = "sobrevendido"
        fatores.append((
            "🟡",
            "Força do movimento",
            f"RSI em {rsi:.1f}: o mercado está pressionado na baixa."
        ))

    elif rsi >= 50:
        leitura_rsi = "comprador"
        pontos_alta += 1
        fatores.append((
            "🟢",
            "Força do movimento",
            f"RSI em {rsi:.1f}: há predominância de força compradora."
        ))

    else:
        leitura_rsi = "vendedor"
        pontos_baixa += 1
        fatores.append((
            "🔴",
            "Força do movimento",
            f"RSI em {rsi:.1f}: há predominância de força vendedora."
        ))

    # MACD
    if macd > signal:
        pontos_alta += 1
        fatores.append((
            "🟢",
            "Momentum",
            "O MACD está acima da linha de sinal."
        ))
    else:
        pontos_baixa += 1
        fatores.append((
            "🔴",
            "Momentum",
            "O MACD está abaixo da linha de sinal."
        ))

    # Volume
    if volume > volume_medio * 1.2:
        fatores.append((
            "🟢",
            "Volume",
            "O volume está acima da média, aumentando a relevância do movimento."
        ))
    elif volume < volume_medio * 0.8:
        fatores.append((
            "🟡",
            "Volume",
            "O volume está abaixo da média; o movimento tem menor participação."
        ))
    else:
        fatores.append((
            "🟡",
            "Volume",
            "O volume está próximo da média."
        ))

    # Volatilidade
    if vol >= 35:
        vol_leitura = "Alta"
        fatores.append((
            "🔴",
            "Volatilidade",
            f"Volatilidade anualizada estimada em {vol:.1f}%, indicando mercado mais agressivo."
        ))
    elif vol >= 20:
        vol_leitura = "Moderada"
        fatores.append((
            "🟡",
            "Volatilidade",
            f"Volatilidade anualizada estimada em {vol:.1f}%, considerada moderada."
        ))
    else:
        vol_leitura = "Baixa"
        fatores.append((
            "🟢",
            "Volatilidade",
            f"Volatilidade anualizada estimada em {vol:.1f}%, relativamente baixa."
        ))

    # Diagnóstico geral
    if pontos_alta >= pontos_baixa + 2:
        geral = "Cenário predominantemente comprador"
        cor = "🟢"
    elif pontos_baixa >= pontos_alta + 2:
        geral = "Cenário predominantemente vendedor"
        cor = "🔴"
    else:
        geral = "Cenário misto / indefinido"
        cor = "🟡"

    return {
        "preco": preco,
        "sma": sma,
        "ema": ema,
        "rsi": rsi,
        "macd": macd,
        "signal": signal,
        "atr": atr,
        "vol": vol,
        "volume": volume,
        "volume_medio": volume_medio,
        "tendencia": tendencia,
        "vol_leitura": vol_leitura,
        "geral": geral,
        "cor": cor,
        "fatores": fatores
    }


def formatar_preco(valor):
    return f"{valor:,.2f}"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            padding:12px 0 18px 0;
            border-bottom:1px solid #344554;
            margin-bottom:18px;">
            <div style="font-size:21px;font-weight:700;color:white;">
                📊 Market Cost Analyzer
            </div>
            <div style="font-size:12px;color:#aebbc7;margin-top:5px;">
                Plataforma de análise de mercado
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### ⚙️ Configuração")

    ativos = {
        "Brent — BRN1! / BZ=F": "BZ=F",
        "WTI": "CL=F",
        "Ouro": "GC=F",
        "Prata": "SI=F",
        "Dólar": "BRL=X",
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD"
    }

    nome_ativo = st.selectbox(
        "Ativo",
        list(ativos.keys())
    )

    ticker = ativos[nome_ativo]

    usar_manual = st.checkbox(
        "Usar outro ticker"
    )

    if usar_manual:
        ticker = st.text_input(
            "Ticker Yahoo Finance",
            value=ticker
        ).upper()

    periodo = st.selectbox(
        "Período",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=2
    )

    intervalo = st.selectbox(
        "Timeframe",
        ["1d", "1h"],
        index=0
    )

    st.markdown("---")

    st.markdown("### 💰 Operação")

    capital = st.number_input(
        "Capital (R$)",
        min_value=0.0,
        value=10000.0,
        step=500.0
    )

    quantidade = st.number_input(
        "Quantidade",
        min_value=0.01,
        value=1.0,
        step=1.0
    )

    st.markdown("#### Custos")

    corretagem = st.number_input(
        "Corretagem (R$)",
        min_value=0.0,
        value=0.0,
        step=1.0
    )

    spread = st.number_input(
        "Spread (%)",
        min_value=0.0,
        value=0.10,
        step=0.05
    )

    slippage = st.number_input(
        "Slippage (%)",
        min_value=0.0,
        value=0.05,
        step=0.05
    )

    outros = st.number_input(
        "Outros custos (R$)",
        min_value=0.0,
        value=0.0,
        step=1.0
    )

    st.markdown("---")

    analisar = st.button(
        "🔎 ANALISAR MERCADO",
        use_container_width=True,
        type="primary"
    )

# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="app-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div class="app-title">📊 Market Cost Analyzer</div>
                <div class="app-subtitle">
                    Análise técnica, custos, risco e interpretação em linguagem simples
                </div>
            </div>
            <div class="online">● ONLINE</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# TELA INICIAL
# ============================================================

if not analisar:

    st.markdown("## 👋 Bem-vindo")

    st.markdown("""
    Configure o ativo na lateral esquerda e clique em **ANALISAR MERCADO**.

    O sistema irá transformar os principais indicadores técnicos em uma
    interpretação simples, mostrando:
    """)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.info("📈 **Tendência**\n\nIdentifica a direção predominante.")

    with col2:
        st.info("🎯 **Níveis**\n\nMostra suportes, resistências e Fibonacci.")

    with col3:
        st.info("🧠 **Interpretação**\n\nTraduz indicadores para linguagem simples.")

    with col4:
        st.info("💰 **Custos**\n\nCalcula custos e ponto de equilíbrio.")

    st.stop()

# ============================================================
# DOWNLOAD
# ============================================================

df = baixar_dados(
    ticker,
    periodo,
    intervalo
)

if df.empty:

    st.error(
        "Não foi possível obter dados para este ativo/período. "
        "Tente outro período ou timeframe."
    )

    st.stop()

# ============================================================
# INDICADORES
# ============================================================

df = calcular_indicadores(df)

df = df.dropna(subset=["EMA21", "RSI", "MACD", "MACD_SIGNAL", "ATR"])

if df.empty:
    st.error("Dados insuficientes para calcular os indicadores.")
    st.stop()

analise = interpretar(df)

preco = analise["preco"]

# ============================================================
# FIBONACCI
# ============================================================

minima, maxima, fib_retr, fib_ext = fibonacci_automatico(df)

# ============================================================
# SUPORTE / RESISTÊNCIA
# ============================================================

ultimos_50 = df.tail(min(50, len(df)))

suporte = float(ultimos_50["Low"].min())
resistencia = float(ultimos_50["High"].max())

# ============================================================
# CUSTOS
# ============================================================

valor_operacao = preco * quantidade

custo_spread = valor_operacao * spread / 100
custo_slippage = valor_operacao * slippage / 100

custo_total = (
    corretagem +
    custo_spread +
    custo_slippage +
    outros
)

percentual_custo = (
    custo_total / valor_operacao * 100
    if valor_operacao > 0 else 0
)

break_even = preco * (1 + percentual_custo / 100)

# ============================================================
# RISCO
# ============================================================

distancia_suporte = preco - suporte

distancia_suporte_pct = (
    distancia_suporte / preco * 100
    if preco else 0
)

atr_pct = (
    analise["atr"] / preco * 100
    if preco else 0
)

# ============================================================
# TOPO DE MÉTRICAS
# ============================================================

st.markdown(
    f"### {nome_ativo}"
)

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Preço</div>
            <div class="metric-value">{formatar_preco(preco)}</div>
            <div class="metric-desc">último fechamento</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Tendência</div>
            <div class="metric-value">{analise["tendencia"]}</div>
            <div class="metric-desc">curto prazo</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">RSI</div>
            <div class="metric-value">{analise["rsi"]:.1f}</div>
            <div class="metric-desc">força do movimento</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">ATR</div>
            <div class="metric-value">{analise["atr"]:.2f}</div>
            <div class="metric-desc">volatilidade em preço</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with m5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Volatilidade</div>
            <div class="metric-value">{analise["vol"]:.1f}%</div>
            <div class="metric-desc">{analise["vol_leitura"]}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# INTERPRETAÇÃO PRINCIPAL
# ============================================================

st.markdown("## 🧠 Interpretação do mercado")

if analise["tendencia"] == "Alta":

    texto_tendencia = (
        "O preço está acima das principais médias de curto prazo, "
        "o que indica que o movimento recente apresenta estrutura de alta."
    )

elif analise["tendencia"] == "Baixa":

    texto_tendencia = (
        "O preço está abaixo das principais médias de curto prazo, "
        "o que indica que o movimento recente apresenta estrutura de baixa."
    )

else:

    texto_tendencia = (
        "O preço está próximo ou entre as principais médias de curto prazo, "
        "indicando falta de direção clara."
    )

if analise["rsi"] > 70:

    texto_momento = (
        "O RSI está elevado, portanto o movimento de alta encontra-se "
        "mais esticado e merece atenção."
    )

elif analise["rsi"] < 30:

    texto_momento = (
        "O RSI está baixo, indicando forte pressão recente de venda."
    )

else:

    texto_momento = (
        "O RSI está em uma região intermediária, sem indicar "
        "extremo de sobrecompra ou sobrevenda."
    )

texto_geral = (
    f"{texto_tendencia} {texto_momento} "
    f"O cenário geral foi classificado como "
    f"**{analise['geral']}**."
)

st.markdown(
    f"""
    <div class="interpretation">
        <div class="interpretation-title">
            {analise["cor"]} {analise["geral"]}
        </div>
        <div class="interpretation-text">
            {texto_geral}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# FATORES
# ============================================================

st.markdown("## 🔍 Por que o sistema chegou a essa leitura?")

col_a, col_b = st.columns(2)

for i, fator in enumerate(analise["fatores"]):

    icone, titulo, texto = fator

    bloco = f"""
    <div class="factor">
        <div class="factor-title">{icone} {titulo}</div>
        <div class="factor-text">{texto}</div>
    </div>
    """

    if i % 2 == 0:
        with col_a:
            st.markdown(bloco, unsafe_allow_html=True)
    else:
        with col_b:
            st.markdown(bloco, unsafe_allow_html=True)

# ============================================================
# GRÁFICO
# ============================================================

st.markdown("## 📈 Gráfico")

fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Preço"
    )
)

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["SMA20"],
        name="SMA 20",
        line=dict(width=1.5)
    )
)

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["EMA21"],
        name="EMA 21",
        line=dict(width=1.5)
    )
)

# Fibonacci
for nome, valor in fib_retr.items():

    fig.add_hline(
        y=valor,
        line_dash="dot",
        line_width=1,
        annotation_text=f"Fib {nome}",
        annotation_position="right"
    )

for nome, valor in fib_ext.items():

    fig.add_hline(
        y=valor,
        line_dash="dash",
        line_width=1,
        annotation_text=f"Ext {nome}",
        annotation_position="right"
    )

# Suporte
fig.add_hline(
    y=suporte,
    line_dash="dash",
    line_width=2,
    annotation_text="SUPORTE",
    annotation_position="left"
)

# Resistência
fig.add_hline(
    y=resistencia,
    line_dash="dash",
    line_width=2,
    annotation_text="RESISTÊNCIA",
    annotation_position="left"
)

fig.update_layout(
    height=700,
    template="plotly_white",
    xaxis_rangeslider_visible=False,
    margin=dict(l=20, r=130, t=20, b=20),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="left",
        x=0
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ============================================================
# CENÁRIOS
# ============================================================

st.markdown("## 🎯 Cenários possíveis")

distancia = maxima - minima

alvo_127 = fib_ext["127.2%"]
alvo_161 = fib_ext["161.8%"]

col1, col2, col3 = st.columns(3)

with col1:

    st.markdown(
        f"""
        <div class="scenario">
            <div class="scenario-title">🟢 Cenário de alta</div>
            <div class="scenario-price">{formatar_preco(resistencia)}</div>
            <div class="scenario-text">
                Se o preço superar a resistência com confirmação,
                os próximos níveis técnicos observados são
                <b>{formatar_preco(alvo_127)}</b> e
                <b>{formatar_preco(alvo_161)}</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:

    st.markdown(
        f"""
        <div class="scenario">
            <div class="scenario-title">🟡 Cenário lateral</div>
            <div class="scenario-price">
                {formatar_preco(suporte)} — {formatar_preco(resistencia)}
            </div>
            <div class="scenario-text">
                Enquanto o preço permanecer nessa região,
                o mercado pode ser interpretado como uma faixa
                de consolidação.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:

    suporte_abaixo = minima

    st.markdown(
        f"""
        <div class="scenario">
            <div class="scenario-title">🔴 Cenário de baixa</div>
            <div class="scenario-price">{formatar_preco(suporte)}</div>
            <div class="scenario-text">
                Se o suporte for perdido com confirmação,
                o próximo nível observado pela estrutura atual
                é aproximadamente <b>{formatar_preco(suporte_abaixo)}</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# RISCO
# ============================================================

st.markdown("## ⚠️ Risco e pontos de atenção")

r1, r2, r3, r4 = st.columns(4)

with r1:
    st.metric(
        "Distância até suporte",
        f"{distancia_suporte_pct:.2f}%"
    )

with r2:
    st.metric(
        "ATR / preço",
        f"{atr_pct:.2f}%"
    )

with r3:
    st.metric(
        "Suporte",
        formatar_preco(suporte)
    )

with r4:
    st.metric(
        "Resistência",
        formatar_preco(resistencia)
    )

if distancia_suporte_pct < 2:

    st.warning(
        "⚠️ O preço está relativamente próximo do suporte identificado. "
        "Uma movimentação pequena pode alterar a leitura atual."
    )

elif atr_pct > 3:

    st.warning(
        "⚠️ A volatilidade em relação ao preço está elevada. "
        "Oscilações maiores devem ser consideradas na interpretação."
    )

else:

    st.info(
        "ℹ️ Não foi identificado, pelos critérios utilizados, "
        "um nível excepcional de risco de curto prazo."
    )

# ============================================================
# CUSTOS
# ============================================================

st.markdown("## 💰 Custos da operação")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Valor da operação",
        f"R$ {valor_operacao:,.2f}"
    )

with c2:
    st.metric(
        "Custos estimados",
        f"R$ {custo_total:,.2f}"
    )

with c3:
    st.metric(
        "Custo %",
        f"{percentual_custo:.3f}%"
    )

with c4:
    st.metric(
        "Break-even",
        formatar_preco(break_even)
    )

st.info(
    f"Para compensar os custos estimados de **R$ {custo_total:,.2f}**, "
    f"o preço precisa superar aproximadamente **{break_even:,.2f}**, "
    "considerando apenas os parâmetros informados na configuração."
)

# ============================================================
# FIBONACCI
# ============================================================

st.markdown("## 📐 Fibonacci")

tab1, tab2 = st.tabs(
    ["Retrações", "Extensões"]
)

with tab1:

    fib_df = pd.DataFrame(
        {
            "Nível": list(fib_retr.keys()),
            "Preço": list(fib_retr.values())
        }
    )

    fib_df["Distância do preço"] = (
        fib_df["Preço"] - preco
    )

    st.dataframe(
        fib_df.style.format({
            "Preço": "{:.2f}",
            "Distância do preço": "{:.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

with tab2:

    ext_df = pd.DataFrame(
        {
            "Extensão": list(fib_ext.keys()),
            "Preço": list(fib_ext.values())
        }
    )

    ext_df["Distância do preço"] = (
        ext_df["Preço"] - preco
    )

    st.dataframe(
        ext_df.style.format({
            "Preço": "{:.2f}",
            "Distância do preço": "{:.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# INDICADORES
# ============================================================

st.markdown("## 📊 Indicadores")

ind1, ind2 = st.columns(2)

with ind1:

    st.metric(
        "SMA 20",
        f"{analise['sma']:.2f}"
    )

    st.metric(
        "EMA 21",
        f"{analise['ema']:.2f}"
    )

    st.metric(
        "MACD",
        f"{analise['macd']:.4f}"
    )

with ind2:

    st.metric(
        "RSI",
        f"{analise['rsi']:.2f}"
    )

    st.metric(
        "ATR",
        f"{analise['atr']:.4f}"
    )

    st.metric(
        "Volume",
        f"{analise['volume']:,.0f}"
    )

# ============================================================
# EXPLICAÇÃO PARA LEIGO
# ============================================================

st.markdown("## 🧭 Como uma pessoa leiga deve interpretar?")

explicacao = f"""
### 1. Primeiro olhe a tendência

O sistema identificou uma tendência de **{analise["tendencia"].lower()}**.

Isso não significa que o próximo movimento obrigatoriamente seguirá
essa direção. Significa apenas que os dados recentes apresentam
essa característica.

### 2. Depois observe os níveis

O suporte atual está próximo de **{suporte:.2f}**.

A resistência está próxima de **{resistencia:.2f}**.

Esses são níveis importantes porque uma mudança de comportamento
nessas regiões pode alterar a leitura do cenário.

### 3. Observe a força do movimento

O RSI está em **{analise["rsi"]:.1f}**.

O sistema considera que o mercado está em uma região
de **{leitura_rsi}**.

### 4. Observe o risco

O ATR atual é de aproximadamente **{analise["atr"]:.2f}**.

Quanto maior o ATR em relação ao preço, maiores tendem a ser
as oscilações recentes.

### 5. Não interprete um indicador isoladamente

A leitura apresentada combina vários fatores.

O resultado atual é:

**{analise["cor"]} {analise["geral"]}.**

A melhor forma de interpretar isso é observar **quais condições
confirmariam ou invalidariam cada cenário**.
"""

st.markdown(
    f"""
    <div class="interpretation">
        <div class="interpretation-text">
            {explicacao.replace(chr(10), "<br>")}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# DADOS
# ============================================================

with st.expander("📋 Ver dados utilizados"):

    st.dataframe(
        df.tail(100),
        use_container_width=True
    )

st.caption(
    "Market Cost Analyzer V4 • Os indicadores são cálculos quantitativos "
    "sobre os dados disponíveis e não representam garantia de resultado futuro."
)
