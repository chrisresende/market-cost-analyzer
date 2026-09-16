from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

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
    category: str = "Macro"  # Macro, Micro, Premix, Aditivo

@dataclass
class ProductionParameters:
    freight_inbound_ton: float = 85.0
    packaging_cost_ton: float = 35.0
    packaging_loss_pct: float = 0.8
    industrial_cif_ton: float = 115.0
    moisture_loss_pct: float = 1.2  # Quebra térmica/processo

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
