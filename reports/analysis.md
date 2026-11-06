# Component dependency review

Component names and descriptions come from the bundled CondenserLab BOM. Purchasing, production, margins and compatibility properties are simulated assumptions, not supplier quotations or validated hardware specifications.

The four variant products require 14 part-master entries. An integer programme allocates shared stock to maximize assumed contribution margin under demand bounds. It does not count the same seal twice across products.

All-source baseline: 36 units. Removing SealWorks deliveries causes INR 131,400 of lost scenario contribution. Approved spare seals reduce that to INR 79,400. The nominally approved 12V fan is rejected against the scenario 24V requirement.

The seal purchase order has low spend but affects every product variant. Spend alone does not capture shared-component dependence. See supplier_risk.csv and the exact dependency paths for the full comparison.

Recommendation: investigate approved spare seal stock before expediting unrelated deliveries. Assumed action costs and recoverable contribution are in actions.csv. No real procurement savings are claimed.

Limitations: four assumed product variants, static demand and stock, no stochastic demand, no lead-time distributions, no physical fit validation, no transport or assembly capacity constraints. Contributions depend on assumed unit economics. Rejected fractions and delivery horizons are scenario sensitivities.
