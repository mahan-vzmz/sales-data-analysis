# Streamlit page acceptance

| Page | Business question | Acceptance checks |
| --- | --- | --- |
| Executive overview | How much revenue and profit remains after returns, and where did it come from? | Reconcile unfiltered totals to Gold, recompute under date, channel, category and city filters, show trend and breakdowns, download matching rows. |
| Customer insights | Which customers buy again, and where is inactivity concentrated? | Show RFM, cohort retention, recency and saved probabilities for the selected customer population, handle missing model files, download customer scores. |
| Basket analysis | Which product pairs warrant a cross-sell experiment? | Apply inclusive support, confidence and lift thresholds, show directional rules and pair counts, download matching rules. |
| Forecasting & What-If | How did the forecast perform, and how do seasonal reference units, price and discount affect the scenario? | Show held-out predictions and backtest errors, constrain inputs to the observed ranges, label the estimate, download the comparison. |

Each page provides a readable state for missing data or empty selections.
Check navigation, chart and table layout, and downloads at desktop and narrow
viewport sizes.

The seasonal-naive prediction for each target week is the observed unit count
from its reference week. The scenario can replace that input for one target
week. Price and discount convert predicted units to estimated revenue.
Other artifact models use their saved unit estimates for the revenue comparison.
