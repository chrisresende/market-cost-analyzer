import io
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from src.core.models import CostBreakdownResult, ProductionParameters

class ExcelReportService:
    @staticmethod
    def generate_executive_sheet(result: CostBreakdownResult, params: ProductionParameters) -> io.BytesIO:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # 1. Resumo Executivo
            summary_data = {
                "Métrica Operacional": [
                    "Custo Total por Tonelada",
                    "Custo por Saca (40 kg)",
                    "Custo por Saca (25 kg)",
                    "Subtotal Matérias-Primas",
                    "Quebra de Processo / Umidade",
                    "Frete Inbound Médio",
                    "Embalagens (+ perdas operacionais)",
                    "CIF / GGF Industrial"
                ],
                "Valor (R$)": [
                    result.total_cost_ton,
                    result.cost_bag_40kg,
                    result.cost_bag_25kg,
                    result.raw_material_cost_ton,
                    result.process_loss_cost_ton,
                    result.freight_total_ton,
                    result.packaging_total_ton,
                    result.industrial_cif_ton
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name="Resumo Gerencial", index=False)

            # 2. Detalhamento da Ficha Técnica
            df_details = pd.DataFrame(result.items_breakdown)
            df_details.to_excel(writer, sheet_name="Ficha Técnica (BOM)", index=False)

        output.seek(0)
        return output
