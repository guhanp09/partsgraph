import hashlib

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import xlsxwriter

from .core import SupplyModel
from .io import ROOT, chart, dump, report


def prepare():
    source = ROOT / "data/source_bom.csv"
    if not source.exists():
        raise FileNotFoundError("Missing bundled CondenserLab source BOM")
    original = pd.read_csv(source)
    study = original[original.assembly == "study"]
    products, bom, parts = [], [], []
    rng = np.random.default_rng(26)
    for variant, demand, margin in [
        ("baseline", 8, 3200),
        ("rounded", 10, 3700),
        ("tapered", 12, 4200),
        ("combined", 6, 4600),
    ]:
        product = f"condenser-{variant}"
        products.append(dict(product=product, demand=demand, margin_inr=margin))
        bom.append(dict(parent=product, component=f"chassis-{variant}", quantity=1))
        for row in study.itertuples():
            part = f"shroud-{variant}" if row.component == "shroud" else row.component
            parent = (
                f"chassis-{variant}"
                if row.component in ["enclosure", "mounting_feet", "core_rails"]
                else product
            )
            quantity = 1 if row.component == "shroud" else float(str(row.quantity).split()[0])
            bom.append(dict(parent=parent, component=part, quantity=quantity))
            if part not in [p["part"] for p in parts]:
                interface = (
                    "300mm"
                    if row.component == "axial_fan"
                    else "standard-seal"
                    if row.component == "gaskets_and_fasteners"
                    else part
                )
                parts.append(
                    dict(
                        part=part,
                        description=row.description,
                        source="CondenserLab BOM; scenario specifications",
                        kind=row.component,
                        interface=interface,
                        voltage=24 if row.component == "axial_fan" else 0,
                        max_temp_c=80,
                        inventory=2 if row.component == "gaskets_and_fasteners" else 8,
                        supplier="SealWorks"
                        if row.component == "gaskets_and_fasteners"
                        else f"Supplier-{int(rng.integers(1, 5))}",
                        unit_cost_inr=25
                        if row.component == "gaskets_and_fasteners"
                        else int(rng.integers(150, 2200)),
                    )
                )
    parts += [
        dict(
            part="seal-spare",
            description="Scenario-approved seal",
            source="simulated",
            kind="gaskets_and_fasteners",
            interface="standard-seal",
            voltage=0,
            max_temp_c=90,
            inventory=12,
            supplier="BackupSeal",
            unit_cost_inr=40,
        ),
        dict(
            part="fan-wrong-voltage",
            description="Scenario incompatible 12V fan",
            source="simulated",
            kind="axial_fan",
            interface="300mm",
            voltage=12,
            max_temp_c=80,
            inventory=20,
            supplier="BackupFan",
            unit_cost_inr=900,
        ),
    ]
    p = pd.DataFrame(parts)
    orders = pd.DataFrame(
        [
            dict(
                order=f"PO-{i}",
                part=r.part,
                supplier=r.supplier,
                quantity=40 if r.kind == "gaskets_and_fasteners" else 160,
                days_to_arrival=14,
                status="simulated open purchase order",
            )
            for i, r in enumerate(p.itertuples())
            if r.source != "simulated"
        ]
    )
    alternatives = pd.DataFrame(
        [
            dict(original="gaskets_and_fasteners", alternate="seal-spare", approved=True),
            dict(original="axial_fan", alternate="fan-wrong-voltage", approved=True),
        ]
    )
    out = ROOT / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in [
        ("bom", pd.DataFrame(bom)),
        ("parts", p),
        ("products", pd.DataFrame(products)),
        ("orders", orders),
        ("alternatives", alternatives),
    ]:
        frame.to_csv(out / f"{name}.csv", index=False)
    dump(
        ROOT / "data/provenance.json",
        {
            "source": "CondenserLab reports/bom.csv",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "simulation_seed": 26,
            "actual_artifacts": "component names, descriptions, and source quantities",
            "scenario_assumptions": "product families, subassemblies, demand, costs, margins, stock, lead times, compatibility and suppliers; source shroud quantity 4 represents four alternatives, mapped to one per variant",
        },
    )
    return load()


def load():
    folder = ROOT / "data/processed"
    return SupplyModel(
        **{
            name: pd.read_csv(folder / f"{name}.csv")
            for name in ["bom", "parts", "products", "orders", "alternatives"]
        }
    )


def run():
    model = prepare()
    baseline = model.scenario()
    rows = []
    for supplier in sorted(model.orders.supplier.unique()):
        result = model.scenario(supplier_outage=supplier)
        spend = model.orders.merge(model.parts[["part", "unit_cost_inr"]], on="part")
        spend = spend[spend.supplier == supplier]
        rows.append(
            dict(
                supplier=supplier,
                purchase_spend_inr=float((spend.quantity * spend.unit_cost_inr).sum()),
                lost_contribution_inr=result["lost_contribution_inr"],
                unfilled_units=result["unfilled_units"],
            )
        )
    risks = pd.DataFrame(rows).sort_values("lost_contribution_inr", ascending=False)
    risks.to_csv(ROOT / "reports/supplier_risk.csv", index=False)
    disruption = model.scenario(supplier_outage="SealWorks")
    mitigated = model.scenario(supplier_outage="SealWorks", substitutions=True)
    disruption["allocation"].to_csv(ROOT / "reports/outage_allocation.csv", index=False)
    disruption["paths"].to_csv(ROOT / "reports/dependency_paths.csv", index=False)
    nx.write_graphml(model.graph(), ROOT / "reports/dependencies.graphml")
    actions = []
    for option, kwargs, cost in [
        ("No action", {}, 0),
        ("Approved substitution", {"substitutions": True}, 12 * 40),
        ("Expedite unaffected orders", {"lead_increase": -7}, 2500),
    ]:
        r = model.scenario(supplier_outage="SealWorks", **kwargs)
        actions.append(
            dict(
                action=option,
                incremental_cost_inr=cost,
                recovered_contribution_inr=disruption["lost_contribution_inr"] - r["lost_contribution_inr"],
                remaining_lost_contribution_inr=r["lost_contribution_inr"],
            )
        )
    actions = pd.DataFrame(actions)
    actions["net_recovery_inr"] = actions.recovered_contribution_inr - actions.incremental_cost_inr
    actions.to_csv(ROOT / "reports/actions.csv", index=False)
    sensitivity = pd.DataFrame(
        [
            dict(
                horizon=h,
                rejected_fraction=q,
                lost_contribution_inr=model.scenario(horizon=h, rejected_fraction=q)["lost_contribution_inr"],
            )
            for h in [7, 14, 28]
            for q in [0, 0.1, 0.3]
        ]
    )
    sensitivity.to_csv(ROOT / "reports/sensitivity.csv", index=False)
    chart(
        px.scatter(
            risks,
            x="purchase_spend_inr",
            y="lost_contribution_inr",
            text="supplier",
            title="Purchase spend versus disruption consequence — simulated scenario",
        ),
        "supplier_risk",
    )
    with xlsxwriter.Workbook(ROOT / "reports/scenario_review.xlsx") as workbook:
        for name, frame in [
            ("Supplier risk", risks),
            ("Actions", actions),
            ("Allocation", disruption["allocation"]),
            ("Sensitivity", sensitivity),
        ]:
            sheet = workbook.add_worksheet(name)
            sheet.write_row(0, 0, frame.columns)
            for i, row in enumerate(frame.itertuples(index=False, name=None), 1):
                sheet.write_row(i, 0, row)
            sheet.autofilter(0, 0, len(frame), len(frame.columns) - 1)
            sheet.freeze_panes(1, 0)
            sheet.set_column(0, len(frame.columns) - 1, 24)
    metrics = dict(
        products=len(model.products),
        components=len(model.parts),
        baseline_units=int(baseline["allocation"].buildable.sum()),
        seal_outage_lost_contribution_inr=disruption["lost_contribution_inr"],
        after_substitution_lost_contribution_inr=mitigated["lost_contribution_inr"],
        incompatible_fan_rejected=not model.compatibility("axial_fan", "fan-wrong-voltage"),
    )
    report(
        "PartsGraph",
        f"""# Component dependency review

Component names and descriptions come from the bundled CondenserLab BOM. Purchasing, production, margins and compatibility properties are simulated assumptions, not supplier quotations or validated hardware specifications.

The four variant products require {len(model.parts)} part-master entries. An integer programme allocates shared stock to maximize assumed contribution margin under demand bounds. It does not count the same seal twice across products.

All-source baseline: {metrics["baseline_units"]} units. Removing SealWorks deliveries causes INR {disruption["lost_contribution_inr"]:,.0f} of lost scenario contribution. Approved spare seals reduce that to INR {mitigated["lost_contribution_inr"]:,.0f}. The nominally approved 12V fan is rejected against the scenario 24V requirement.

The seal purchase order has low spend but affects every product variant. Spend alone does not capture shared-component dependence. See supplier_risk.csv and the exact dependency paths for the full comparison.

Recommendation: investigate approved spare seal stock before expediting unrelated deliveries. Assumed action costs and recoverable contribution are in actions.csv. No real procurement savings are claimed.

Limitations: four assumed product variants, static demand and stock, no stochastic demand, no lead-time distributions, no physical fit validation, no transport or assembly capacity constraints. Contributions depend on assumed unit economics. Rejected fractions and delivery horizons are scenario sensitivities.
""",
        metrics,
    )
    return metrics
