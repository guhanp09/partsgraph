# Engineering notes

BOM edges carry component quantities. Validation rejects cycles, duplicate relationships,
unknown leaf components and duplicate master identifiers. Recursive expansion accumulates
requirements across every assembly path.

Production is allocated through an integer programme under demand and shared-stock limits.
The resulting allocation is checked against available inventory. Supplier outages remove
future receipts, while existing stock remains available. Spare stock is consumed once and
requires matching component, interface, voltage and temperature properties.

Small fixtures check stock conservation, nested quantities, receipt timing, rejected receipts
and substitute compatibility. Engineering source rows are distinguished from simulated
purchasing, demand, compatibility and unit-economics assumptions in the data dictionary.

Tested dependency versions are recorded in constraints.txt and environment.json.
