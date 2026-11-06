# Data dictionary and provenance

Component names and descriptions come from data/source_bom.csv, copied from the existing CondenserLab study. The four product variants, nested chassis grouping, inventory, suppliers, compatibility properties, purchasing, demand, costs and margins are simulated assumptions. Four alternative source shrouds are mapped to one shroud per variant. No supplier quote, hardware fit approval or procurement savings is claimed.

| Input | Grain | Important columns |
| --- | --- | --- |
| source_bom.csv | Original BOM row | assembly, component, description, quantity, specification |
| bom.csv | Parent/component relation | parent, component, quantity |
| parts.csv | Part master | part, kind, interface, voltage, max_temp_c, inventory, supplier, unit_cost_inr |
| products.csv | Product variant | product, demand, margin_inr |
| orders.csv | Open purchase order | order, part, supplier, quantity, days_to_arrival |
| alternatives.csv | Candidate substitution | original, alternate, approved |

Only the original engineering descriptions and source quantities are existing artifacts.
All operational and compatibility properties are scenario assumptions. Quantities are
counts, time is days, economics are INR. No supplier has been contacted and nothing has
been purchased. Simulation seed: 26. Dedicated alternate stock is not a substitute for
actual fit, electrical or thermal qualification.
