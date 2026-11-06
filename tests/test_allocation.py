import networkx as nx
import numpy as np
import pytest

from partsgraph.pipeline import prepare


def test_shared_inventory_is_not_double_counted():
    m = prepare()
    stock = m.available("SealWorks")
    r = m.allocate(stock)
    assert r.buildable.sum() == 2
    assert np.all(m.requirements().to_numpy() @ r.buildable.to_numpy() <= stock.to_numpy() + 1e-8)


def test_incompatible_substitute_and_approved_spares():
    m = prepare()
    assert not m.compatibility("axial_fan", "fan-wrong-voltage")
    assert m.compatibility("gaskets_and_fasteners", "seal-spare")
    assert m.scenario("SealWorks", substitutions=True)["allocation"].buildable.sum() == 14


def test_cycle_and_duplicate_master_fail():
    m = prepare()
    m.bom.loc[len(m.bom)] = ["enclosure", "condenser-baseline", 1]
    with pytest.raises(ValueError, match="Circular"):
        m.graph()


def test_nested_quantities_and_healthy_baseline():
    m = prepare()
    assert nx.is_directed_acyclic_graph(m.graph())
    assert m.requirements().loc["mounting_feet", "condenser-baseline"] == 4
    assert m.scenario()["unfilled_units"] == 0


def test_receipt_horizon_and_outage_preserve_existing_inventory():
    m = prepare()
    assert m.available("SealWorks")["gaskets_and_fasteners"] == 2
    assert m.available(horizon=7)["gaskets_and_fasteners"] == 2
    assert m.available(horizon=28)["gaskets_and_fasteners"] == 42
    assert m.available(horizon=28, rejected_fraction=0.5)["gaskets_and_fasteners"] == 22


def test_invalid_receipt_rejection_rate():
    m = prepare()
    with pytest.raises(ValueError, match="Invalid"):
        m.available(rejected_fraction=1.5)
