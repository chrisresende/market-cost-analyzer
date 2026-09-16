# Import flexível: busca nas subpastas ou direto na pasta src
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
    from config import COMMODITY_TICKERS
