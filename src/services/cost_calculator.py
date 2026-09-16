import pandas as pd
from typing import List
from src.core.models import RawMaterialItem, ProductionParameters, CostBreakdownResult

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
            # Converte itens em dólar para BRL
            rate = usd_rate if item.currency == "USD" else 1.0
            price_brl_kg = item.unit_price * rate
            
            # Custo do ingrediente por tonelada produzida
            cost_ton = price_brl_kg * (item.inclusion_pct / 100.0) * 1000.0
            raw_mat_sum += cost_ton
            
            breakdown.append({
                "Ingrediente": item.name,
                "Categoria": item.category,
                "Inclusão (%)": item.inclusion_pct,
                "Preço/kg (BRL)": round(price_brl_kg, 3),
                "Custo R$/ton": round(cost_ton, 2)
            })

        # Custos Industriais e de Processo
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
