import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from src.core.models import MarketQuote
from src.database.repository import MarketRepository

class ResilientMarketCollector:
    def __init__(self, repo: MarketRepository):
        self.repo = repo

    def get_currencies(self) -> dict:
        url = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL"
        try:
            resp = requests.get(url, timeout=4)
            resp.raise_for_status()
            data = resp.json()
            
            usd_price = float(data["USDBRL"]["bid"])
            eur_price = float(data["EURBRL"]["bid"])
            
            # Persiste no banco local
            self.repo.save_quote("USD-BRL", "Dólar Comercial", usd_price, "BRL")
            self.repo.save_quote("EUR-BRL", "Euro Comercial", eur_price, "BRL")
            
            return {
                "USD": MarketQuote("USD-BRL", "Dólar Comercial", usd_price, float(data["USDBRL"]["pctChange"])),
                "EUR": MarketQuote("EUR-BRL", "Euro Comercial", eur_price, float(data["EURBRL"]["pctChange"]))
            }
        except Exception:
            return {
                "USD": MarketQuote("USD-BRL", "Dólar (Offline)", 5.45, 0.0),
                "EUR": MarketQuote("EUR-BRL", "Euro (Offline)", 5.95, 0.0)
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
