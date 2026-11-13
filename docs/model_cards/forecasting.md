# Weekly category demand forecast

## Reference run

The target is ordered units per product category per week from
`gold.mart_forecasting_base`. The run used the repository generator fixture
with seed 42, 100 customers, and error injection disabled. Its load ID was
`forecast-test`. All figures describe synthetic data.

The source calendar covered 2023-01-01 through 2025-12-31. The first and last
calendar weeks were partial and excluded. The remaining panel has 156 complete
weeks and six categories. The run used 104 initial training weeks, 12 disjoint
four-week validation windows, and a final four-week holdout. The last training
week began on 2025-11-24. The holdout weeks began on 2025-12-01 through
2025-12-22. The selected artifact uses model version `1`.

## Methods and features

- **Last value** repeats the last observed weekly count for each category.
- **Seasonal naive** repeats the most recent 52-week pattern for each category.
- **Ridge** uses L2 regularization with alpha 10.
- **Random Forest** uses 40 trees, maximum depth 6, at least four samples
  per leaf, and seed 42.

The candidates fit a separate direct regressor for each forecast horizon.
At the origin they use one-week lags of units, promoted order count, average
unit price, effective discount rate, and online, store, and marketplace unit
shares, plus the previous four weeks' mean units. The target week's ISO week,
holiday days, and planned campaign days come from the calendar. Lagged inputs
stay frozen throughout the four-week forecast. Training skips the first four
weeks of each category. Missing lagged drivers are filled with zero and
negative predictions are clipped to zero.

## Results

MAE is in ordered units per category-week. sMAPE is on a 0–200% scale.
An actual and prediction that are both zero contribute zero error to sMAPE.

| Method | Validation MAE | Validation sMAPE | Holdout MAE | Holdout sMAPE |
| --- | ---: | ---: | ---: | ---: |
| Last value | 3.323 | 99.95% | 9.833 | 87.91% |
| Seasonal naive | 2.965 | 101.20% | **6.958** | 74.36% |
| Ridge | 2.833 | 132.94% | 7.361 | 72.35% |
| Random Forest | **2.653** | 130.64% | 7.608 | 77.49% |

Validation MAE nominates Random Forest and selects seasonal naive as the
fallback baseline. The final holdout serves as a one-time promotion gate.
The nominee must strictly improve on the preselected baseline there too.
Seasonal naive is published because Random Forest did not clear the gate.
Its holdout MAE by horizon is 12.50, 6.50, 3.67, and 5.17 units.
The holdout results inform release and should be interpreted as gate results.

## Reproduce and interpret

The integration test generates the reference warehouse and builds its Gold
mart. Pass its `mart_forecasting_base` frame and the generator's coverage dates
to `run_backtest` with the default settings to reproduce this card.
`write_forecast_artifact` exports the selected model's holdout predictions,
metadata, and per-fold and per-horizon/category metrics as JSON.

Sparse categories can have zero sales, making sMAPE sensitive to small
nonzero forecasts. The 52-week baseline can miss shifts in campaign timing,
and fixed-origin realized drivers become stale at longer horizons. Changes
in future prices, discounts, and channel mix are outside this run's known
inputs. This run uses a single synthetic series per category and a single
final holdout, so its accuracy figures apply to this fixture.
