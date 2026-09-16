import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Market Cost Analyzer", page_icon="💰", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stSidebar"] {background: #172033;}
[data-testid="stSidebar"] * {color: white !important;}
.metric-card {padding: 14px; border-radius: 10px; background: #f5f7fa; border: 1px solid #e1e5ea;}
.alert-box {padding: 14px; border-radius: 10px; background: #f5f7fa; margin-bottom: 8px;}
.small {font-size: 0.85rem; color: #667085;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(ttl=900)
def yahoo_data(ticker, period="1y", interval="1d"):
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.copy()
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["Close"])

@st.cache_data(ttl=3600)
def bcb_sgs(code, days=365):
    """Banco Central SGS public series."""
    end = datetime.now().date()
    start = end - timedelta(days=days)
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    try:
        r = requests.get(url, params={
            "formato": "json",
            "dataInicial": start.strftime("%d/%m/%Y"),
            "dataFinal": end.strftime("%d/%m/%Y")
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame()
        df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
        df["valor"] = pd.to_numeric(df["valor"].astype(str).str.replace(",", "."), errors="coerce")
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def pct_change(df, n):
    if len(df) <= n:
        return np.nan
    return (df["Close"].iloc[-1] / df["Close"].iloc[-1-n] - 1) * 100

def technicals(df):
    out = df.copy()
    close = out["Close"]
    high = out["High"]
    low = out["Low"]
    out["SMA20"] = close.rolling(20).mean()
    out["EMA21"] = close.ewm(span=21, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["RSI14"] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["MACD"] = ema12 - ema26
    out["Signal"] = out["MACD"].ewm(span=9, adjust=False).mean()
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    out["ATR14"] = tr.rolling(14).mean()
    out["Volatilidade"] = close.pct_change().rolling(30).std() * np.sqrt(252) * 100
    return out

def fib_levels(df):
    if df.empty:
        return {}
    recent = df.tail(min(180, len(df)))
    hi = float(recent["High"].max())
    lo = float(recent["Low"].min())
    rng = hi - lo
    if rng <= 0:
        return {}
    retr = {
        "0%": hi,
        "23,6%": hi - rng*0.236,
        "38,2%": hi - rng*0.382,
        "50%": hi - rng*0.500,
        "61,8%": hi - rng*0.618,
        "78,6%": hi - rng*0.786,
        "100%": lo
    }
    ext = {
        "127,2%": lo - rng*0.272,
        "161,8%": lo - rng*0.618,
        "200%": lo - rng,
        "261,8%": lo - rng*1.618
    }
    return {"retr": retr, "ext": ext, "hi": hi, "lo": lo}

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("COST ANALYST")
st.sidebar.caption("Market Cost Analyzer")

page = st.sidebar.radio(
    "Módulo",
    ["🏠 Visão Geral", "🌎 Radar Econômico", "📈 Mercado", "💰 Custos", "🔮 Simulador"]
)

st.sidebar.divider()
st.sidebar.caption("Configurações")

period = st.sidebar.selectbox("Período de mercado", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
interval = st.sidebar.selectbox("Intervalo", ["1d", "1h"], index=0)

# -----------------------------
# Header
# -----------------------------
st.title("Market Cost Analyzer")
st.caption("Plataforma de análise para custos, mercado, indicadores econômicos e simulações.")

# -----------------------------
# Radar
# -----------------------------
if page == "🌎 Radar Econômico":
    st.subheader("Radar Econômico")
    st.write("Indicadores públicos que podem ajudar o analista a acompanhar fatores externos que pressionam ou reduzem custos.")

    # BCB: Selic meta (series 432)
    selic = bcb_sgs(432, 30)
    # BCB: IPCA mensal (series 433)
    ipca = bcb_sgs(433, 400)
    # BCB: PTAX venda (series 1)
    dolar = bcb_sgs(1, 400)

    # Yahoo market proxies
    assets = {
        "Petróleo Brent": "BZ=F",
        "Petróleo WTI": "CL=F",
        "Ouro": "GC=F",
        "Soja": "ZS=F",
        "Milho": "ZC=F",
        "S&P 500": "^GSPC"
    }

    cols = st.columns(3)
    if not selic.empty:
        cols[0].metric("Selic", f"{selic['valor'].iloc[-1]:.2f}%")
    else:
        cols[0].metric("Selic", "Indisponível")

    if not ipca.empty:
        ipca12 = ipca["valor"].tail(12).sum()
        cols[1].metric("IPCA 12 meses*", f"{ipca12:.2f}%")
    else:
        cols[1].metric("IPCA", "Indisponível")

    if not dolar.empty:
        cols[2].metric("PTAX venda", f"R$ {dolar['valor'].iloc[-1]:.4f}")
    else:
        cols[2].metric("PTAX", "Indisponível")

    st.caption("* Soma dos últimos 12 valores mensais disponíveis na série pública consultada.")

    rows = []
    for name, ticker in assets.items():
        d = yahoo_data(ticker, "1y", "1d")
        if not d.empty:
            rows.append({
                "Indicador": name,
                "Atual": float(d["Close"].iloc[-1]),
                "7 dias": pct_change(d, 7),
                "30 dias": pct_change(d, 30),
                "90 dias": pct_change(d, 90)
            })

    if rows:
        radar = pd.DataFrame(rows)
        st.dataframe(
            radar.style.format({
                "Atual": "{:.2f}",
                "7 dias": "{:+.2f}%",
                "30 dias": "{:+.2f}%",
                "90 dias": "{:+.2f}%"
            }),
            use_container_width=True
        )

        st.subheader("Leitura para o analista de custos")
        for _, r in radar.iterrows():
            ch = r["30 dias"]
            if pd.isna(ch):
                continue
            if ch >= 5:
                status = "🔴 pressão relevante"
            elif ch <= -5:
                status = "🟢 movimento de queda"
            else:
                status = "🟡 variação moderada"
            st.markdown(f"**{r['Indicador']}** — {ch:+.2f}% em 30 dias → {status}.")
    else:
        st.warning("Não foi possível obter os dados de mercado agora.")

    st.info("Fontes: Banco Central do Brasil (SGS) e Yahoo Finance. Os dados são informativos e devem ser validados antes de decisões operacionais.")

# -----------------------------
# Mercado
# -----------------------------
elif page == "📈 Mercado":
    options = {
        "Brent — BRN1!": "BZ=F",
        "WTI": "CL=F",
        "Ouro": "GC=F",
        "Prata": "SI=F",
        "Dólar": "BRL=X",
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD"
    }

    selected = st.selectbox("Ativo", list(options.keys()))
    ticker = options[selected]
    df = yahoo_data(ticker, period, interval)

    if df.empty:
        st.error("Não foi possível obter os dados desse ativo.")
        st.stop()

    df = technicals(df)
    current = float(df["Close"].iloc[-1])
    rsi = float(df["RSI14"].iloc[-1]) if pd.notna(df["RSI14"].iloc[-1]) else np.nan
    atr = float(df["ATR14"].iloc[-1]) if pd.notna(df["ATR14"].iloc[-1]) else np.nan
    vol = float(df["Volatilidade"].iloc[-1]) if pd.notna(df["Volatilidade"].iloc[-1]) else np.nan

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preço", f"{current:.2f}", f"{pct_change(df, 1):+.2f}%")
    c2.metric("RSI 14", f"{rsi:.1f}" if not np.isnan(rsi) else "—")
    c3.metric("ATR 14", f"{atr:.2f}" if not np.isnan(atr) else "—")
    c4.metric("Volatilidade anual", f"{vol:.1f}%" if not np.isnan(vol) else "—")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Preço"
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20", mode="lines"))
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], name="EMA 21", mode="lines"))

    fib = fib_levels(df)
    if fib:
        for label, level in fib["retr"].items():
            fig.add_hline(y=level, annotation_text=f"Fib {label}", line_dash="dot")
        for label, level in fib["ext"].items():
            fig.add_hline(y=level, annotation_text=f"Ext {label}", line_dash="dash")

    fig.update_layout(height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Interpretação")
    factors = []
    if current > df["SMA20"].iloc[-1]:
        factors.append("🟢 preço acima da média de 20 períodos: estrutura recente mais firme")
    else:
        factors.append("🔴 preço abaixo da média de 20 períodos: estrutura recente mais fraca")
    if not np.isnan(rsi):
        if rsi >= 70:
            factors.append("🟡 RSI elevado: movimento pode estar esticado")
        elif rsi <= 30:
            factors.append("🟡 RSI baixo: movimento pode estar pressionado")
        else:
            factors.append("🟢 RSI em faixa intermediária")
    if not np.isnan(atr):
        factors.append(f"🟡 ATR indica movimentação média de aproximadamente {atr:.2f} por período")

    for f in factors:
        st.write(f)

    st.subheader("Fibonacci")
    if fib:
        st.write("Níveis automáticos calculados pelo máximo e mínimo recentes. Para análise operacional, a próxima versão poderá permitir selecionar manualmente os pontos A e B.")
        st.dataframe(pd.DataFrame([
            {"Tipo": "Retração", "Nível": k, "Preço": v} for k, v in fib["retr"].items()
        ] + [
            {"Tipo": "Extensão", "Nível": k, "Preço": v} for k, v in fib["ext"].items()
        ]).style.format({"Preço": "{:.4f}"}), use_container_width=True)

# -----------------------------
# Custos
# -----------------------------
elif page == "💰 Custos":
    st.subheader("Análise de Custos")
    st.write("Área preparada para receber dados internos de compras, fórmulas, estoque e produção.")

    col1, col2, col3 = st.columns(3)
    with col1:
        custo = st.number_input("Custo atual por unidade (R$)", min_value=0.0, value=100.0, step=1.0)
    with col2:
        quantidade = st.number_input("Quantidade produzida", min_value=1.0, value=1000.0, step=100.0)
    with col3:
        novo_custo = st.number_input("Novo custo por unidade (R$)", min_value=0.0, value=105.0, step=1.0)

    impacto_unit = novo_custo - custo
    impacto_total = impacto_unit * quantidade
    variacao = (novo_custo / custo - 1) * 100 if custo else np.nan

    a, b, c = st.columns(3)
    a.metric("Variação unitária", f"R$ {impacto_unit:,.2f}")
    b.metric("Variação percentual", f"{variacao:+.2f}%")
    c.metric("Impacto no lote", f"R$ {impacto_total:,.2f}")

    st.subheader("Composição do custo")
    componentes = pd.DataFrame({
        "Componente": ["Matéria-prima", "Embalagem", "Mão de obra", "Energia", "Outros"],
        "% do custo": [70, 8, 7, 5, 10]
    })
    st.bar_chart(componentes.set_index("Componente"))

    st.info("Na próxima etapa, podemos substituir esses exemplos por upload de Excel/CSV ou conexão com dados do Sankhya.")

# -----------------------------
# Simulador
# -----------------------------
elif page == "🔮 Simulador":
    st.subheader("Simulador de Impacto no Custo")
    st.write("Simule mudanças de preços e veja o efeito matemático sobre o custo final.")

    base = st.number_input("Custo atual (R$/un)", min_value=0.0, value=100.0)
    peso = st.number_input("Participação do componente no custo (%)", min_value=0.0, max_value=100.0, value=40.0)
    mudanca = st.number_input("Variação esperada do componente (%)", value=10.0)

    impacto = (peso / 100) * (mudanca / 100)
    novo = base * (1 + impacto)

    c1, c2, c3 = st.columns(3)
    c1.metric("Custo atual", f"R$ {base:,.2f}")
    c2.metric("Impacto teórico", f"{impacto*100:+.2f}%")
    c3.metric("Novo custo estimado", f"R$ {novo:,.2f}")

    st.subheader("Explicação")
    st.write(
        f"Se o componente representa {peso:.1f}% do custo e seu preço variar {mudanca:+.1f}%, "
        f"mantendo os demais componentes constantes, o impacto matemático estimado no custo total "
        f"é de {impacto*100:+.2f}%, levando o custo de R$ {base:,.2f} para aproximadamente R$ {novo:,.2f}."
    )

# -----------------------------
# Visão geral
# -----------------------------
else:
    st.subheader("Visão Geral")
    st.write("Centro de controle do analista de custos.")

    cols = st.columns(4)
    cols[0].metric("Módulos", "5")
    cols[1].metric("Fontes públicas", "2+")
    cols[2].metric("Indicadores", "10+")
    cols[3].metric("Status", "ONLINE")

    st.markdown("### O que o aplicativo já faz")
    items = [
        "🌎 Consulta indicadores públicos do Banco Central.",
        "📈 Consulta commodities, moedas e índices via Yahoo Finance.",
        "📊 Calcula médias, RSI, MACD, ATR e volatilidade.",
        "〽️ Calcula retrações e extensões de Fibonacci.",
        "💰 Simula variações de custo.",
        "🧠 Traduz indicadores em explicações simples."
    ]
    for item in items:
        st.write(item)

    st.markdown("### Próximas expansões")
    st.write("• Importação de Excel/CSV de compras e custos")
    st.write("• Histórico de preços por fornecedor")
    st.write("• Pareto e análise de concentração")
    st.write("• Custo padrão × real")
    st.write("• Estoque, cobertura e giro")
    st.write("• Alertas automáticos")
    st.write("• Integração com outras APIs públicas")
