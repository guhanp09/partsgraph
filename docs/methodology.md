# PartsGraph methodology

A directed edge means a parent requires a quantity of a child. Cycles, duplicate BOM relationships, duplicate master IDs and unknown leaf components fail validation. Recursive expansion sums quantities across all paths; it does not count each component only once.

Production allocation solves an integer programme maximizing sum(product margin × units), subject to A × units ≤ available part stock, 0 ≤ units ≤ demand. Units are integral and the final solution is checked against stock. This avoids independently promising the same shared component to multiple assemblies. Demand and contribution margins are assumed inputs, not forecasts or observed economics.

Available stock includes opening inventory and eligible purchase receipts inside the horizon. An outage removes affected supplier deliveries, not existing stock. Receipt rejection and lead-time shifts are scenario parameters. Compatible dedicated spare inventory is consumed once, with explicit transfers. Approval flags alone do not override kind/interface/voltage/temperature checks; these properties remain assumed pending engineering validation.

Lost contribution is the difference against the all-source baseline at the same horizon. A low-spend shared seal can cause broad disruption. Mitigation action costs are assumptions. The model omits labour capacity, stochastic lead times, transport capacity, real substitute qualification and demand uncertainty.

## Data flow

Bundled engineering BOM + seeded purchasing scenario → graph validation → recursive requirements → eligible stock → integer allocation → disruption/mitigation comparison → graph, workbook and report.
