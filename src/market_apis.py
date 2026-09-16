import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

class MarketDataService:
    """Coletor de indicadores públicos de mercado para o agronegócio."""

    @staticmethod
    def get_currency_rates() -> dict:
        """Coleta USD/BRL e EUR/BRL em tempo real via AwesomeAPI."""
        url = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL"
        try:
            resp = requests.get(url, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            return {
                "usd_rate": float(data["USDBRL"]["bid"]),
                "usd_pct": float(data["USDBRL"]["pctChange"]),
                "eur_rate": float(data["EURBRL"]["bid"]),
                "eur_pct": float(data["EURBRL"]["pctChange"]),
                "timestamp": data["USDBRL"]["create_date"],
            }
        except Exception:
            # Valores de fallback caso a API oscile
            return {
                "usd_rate": 5.40,
                "usd_pct": 0.0,
                "eur_rate": 5.90,
                "eur_pct": 0.0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    @staticmethod
    def get_commodity_history(ticker: str, period: str = "3mo") -> pd.DataFrame:
        """Coleta histórico de fechamento de commodities via Yahoo Finance."""
        try:
            asset = yf.Ticker(ticker)
            df = asset.history(period=period)
            if df.empty:
                return pd.DataFrame()
            df.reset_index(inplace=True)
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            return df[["Date", "Close", "Volume"]]
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def get_bcb_series(serie_code: int, months: int = 6) -> pd.DataFrame:
        """Coleta dados históricos do Banco Central do Brasil (SGS)."""
        start_date = (datetime.now() - timedelta(days=months * 30)).strftime("%d/%m/%Y")
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_code}/dados?formato=json&dataInicial={start_date}"
        try:
            resp = requests.get(url, timeout=6)
            resp.raise_for_status()
            df = pd.DataFrame(resp.json())
            df["valor"] = pd.to_numeric(df["valor"])
            df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
            return df
        except Exception:
            return pd.DataFrame()
