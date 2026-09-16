import pandas as pd

class FeedCostEngine:
    """Motor de cálculo de custo e formulação de nutrição animal."""

    @staticmethod
    def calculate_batch_cost(
        recipe_df: pd.DataFrame,
        usd_rate: float,
        freight_per_ton: float,
        packaging_loss_pct: float,
        cif_industrial_per_ton: float
    ) -> dict:
        """
        Recebe a ficha técnica e calcula o custo por tonelada considerando:
        - Insumos dolarizados vs nacionais
        - Rateio de frete inbound
        - Perda técnica de embalagem/ensaque
        - Custo indireto de fabricação (CIF/GGF)
        """
        df = recipe_df.copy()

        # Ajuste de insumos importados com base na cotação da API
        def adjust_price(row):
            price = row["preco_base_kg"]
            if row.get("moeda", "BRL") == "USD":
                return price * usd_rate
            return price

        df["preco_ajustado_kg"] = df.apply(adjust_price, axis=1)
        df["custo_ingrediente_ton"] = df["preco_ajustado_kg"] * (df["inclusao_pct"] / 100) * 1000

        raw_material_cost_ton = df["custo_ingrediente_ton"].sum()
        packaging_cost_ton = df["custo_embalagem_ton"].iloc[0] * (1 + (packaging_loss_pct / 100))

        total_cost_ton = (
            raw_material_cost_ton
            + freight_per_ton
            + packaging_cost_ton
            + cif_industrial_per_ton
        )

        return {
            "custo_total_ton": round(total_cost_ton, 2),
            "custo_saca_40kg": round((total_cost_ton / 1000) * 40, 2),
            "custo_saca_25kg": round((total_cost_ton / 1000) * 25, 2),
            "custo_mp_ton": round(raw_material_cost_ton, 2),
            "breakdown_df": df[["ingrediente", "inclusao_pct", "custo_ingrediente_ton"]]
        }
