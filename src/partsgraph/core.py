"""BOM graph validation, constrained allocation, and disruption scenarios."""

from dataclasses import dataclass

import networkx as nx
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass
class SupplyModel:
    bom: pd.DataFrame
    parts: pd.DataFrame
    products: pd.DataFrame
    orders: pd.DataFrame
    alternatives: pd.DataFrame

    def graph(self):
        g = nx.DiGraph()
        for row in self.bom.itertuples():
            if row.quantity <= 0:
                raise ValueError("BOM quantities must be positive")
            g.add_edge(row.parent, row.component, quantity=float(row.quantity), relation="requires")
        if not nx.is_directed_acyclic_graph(g):
            raise ValueError("Circular assembly dependency")
        if self.parts.part.duplicated().any() or self.products["product"].duplicated().any():
            raise ValueError("Duplicate master identifier")
        if self.bom.duplicated(["parent", "component"]).any():
            raise ValueError("Duplicate BOM relationship")
        leaves = {n for n in g if g.out_degree(n) == 0}
        if leaves - set(self.parts.part):
            raise ValueError("BOM leaf missing from part master")
        return g

    def requirements(self):
        g = self.graph()
        leaves = list(self.parts.part)

        def expand(node):
            if g.out_degree(node) == 0:
                return {node: 1.0}
            totals = {}
            for child in g.successors(node):
                for part, count in expand(child).items():
                    totals[part] = totals.get(part, 0) + count * g[node][child]["quantity"]
            return totals

        matrix = pd.DataFrame(0.0, index=leaves, columns=self.products["product"])
        for product in matrix.columns:
            if product not in g:
                raise ValueError(f"Product missing from BOM: {product}")
            for part, count in expand(product).items():
                matrix.loc[part, product] = count
        return matrix

    def available(self, supplier_outage=None, horizon=28, lead_increase=0, rejected_fraction=0):
        if horizon < 0 or not 0 <= rejected_fraction <= 1:
            raise ValueError("Invalid horizon or rejected fraction")
        stock = self.parts.set_index("part").inventory.astype(float).copy()
        eligible = self.orders[
            (self.orders.days_to_arrival + lead_increase <= horizon)
            & (self.orders.supplier != supplier_outage)
        ]
        stock = stock.add(eligible.groupby("part").quantity.sum() * (1 - rejected_fraction), fill_value=0)
        return stock.reindex(self.parts.part).fillna(0)

    def compatibility(self, original, alternate):
        p = self.parts.set_index("part")
        if original not in p.index or alternate not in p.index:
            return False
        a, b = p.loc[original], p.loc[alternate]
        return bool(
            a.kind == b.kind
            and a.interface == b.interface
            and a.voltage == b.voltage
            and b.max_temp_c >= a.max_temp_c
        )

    def allocate(self, stock):
        """Integer programme: maximize scenario contribution under shared stock constraints."""
        a = self.requirements()
        products = self.products.set_index("product").loc[a.columns]
        result = milp(
            c=-products.margin_inr.to_numpy(float),
            integrality=np.ones(len(products)),
            bounds=Bounds(np.zeros(len(products)), products.demand.to_numpy(float)),
            constraints=LinearConstraint(a.to_numpy(), -np.inf, stock.reindex(a.index).to_numpy()),
            options={"time_limit": 15},
        )
        if not result.success:
            raise ValueError(f"Production allocation failed: {result.message}")
        units = np.rint(result.x).astype(int)
        if (a.to_numpy() @ units > stock.reindex(a.index).to_numpy() + 1e-7).any():
            raise ValueError("Allocation exceeds inventory")
        frame = products.reset_index()
        frame["buildable"] = units
        frame["unfilled"] = frame.demand - frame.buildable
        frame["contribution_inr"] = frame.buildable * frame.margin_inr
        return frame

    def scenario(
        self, supplier_outage=None, horizon=28, lead_increase=0, rejected_fraction=0, substitutions=False
    ):
        stock = self.available(supplier_outage, horizon, lead_increase, rejected_fraction)
        baseline = self.allocate(self.available(horizon=horizon))
        transfers = []
        if substitutions:
            need = self.requirements() @ self.products.set_index("product").demand
            # Alternatives are dedicated spare inventory. Sequential consumption avoids double counting.
            for row in self.alternatives.itertuples():
                if row.approved and self.compatibility(row.original, row.alternate):
                    qty = max(0, min(stock[row.alternate], need[row.original] - stock[row.original]))
                    stock[row.original] += qty
                    stock[row.alternate] -= qty
                    transfers.append({"original": row.original, "alternate": row.alternate, "quantity": qty})
        allocation = self.allocate(stock)
        requirements = self.requirements() @ self.products.set_index("product").demand
        shortages = (requirements - stock).clip(lower=0)
        paths = []
        g = self.graph()
        for product in self.products["product"]:
            for part in shortages[shortages > 0].index:
                if nx.has_path(g, product, part):
                    paths.append(
                        {
                            "product": product,
                            "part": part,
                            "path": " → ".join(nx.shortest_path(g, product, part)),
                            "shortage": float(shortages[part]),
                        }
                    )
        return {
            "allocation": allocation,
            "stock": stock,
            "paths": pd.DataFrame(paths),
            "transfers": transfers,
            "lost_contribution_inr": float(
                baseline.contribution_inr.sum() - allocation.contribution_inr.sum()
            ),
            "unfilled_units": int(allocation.unfilled.sum()),
        }
