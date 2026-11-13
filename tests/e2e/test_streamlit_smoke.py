import json
from pathlib import Path

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[2] / "app/streamlit_app.py"


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppTest:
    db = tmp_path / "sales.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("""
            create schema gold;
            create table gold.mart_executive as select 1 as order_count;
            create table gold.mart_sales_detail as
            select 'L1' line_id, 'O1' order_id, date '2025-01-06' order_date,
                'Online' channel, 'Audio' category, 'Paris' home_city,
                90.0 return_adjusted_revenue, 30.0 return_adjusted_profit,
                10.0 returned_revenue;
            create table gold.mart_customer_360 as
            select 'C1' customer_id, 'Paris' home_city, date '2025-01-06' last_purchase_date,
                1 completed_order_count, 90.0 return_adjusted_value;
            create table gold.mart_cohort_base as
            select 'C1' customer_id, date '2025-01-01' order_month,
                date '2025-01-01' acquisition_cohort_month, 1 retained_quantity
            union all select 'C2', date '2025-02-01', date '2025-02-01', 1;
            create table gold.mart_basket_base as
            select 'O1' order_id, date '2025-01-06' order_date, 'Audio' category,
                product_id, product_id product_name
            from (values ('A'), ('B')) as items(product_id);
            create table gold.mart_forecasting_base as
            select * from (values
                (date '2025-01-06', 'Audio', 4, 10.0, 0.0),
                (date '2025-01-13', 'Audio', 5, 20.0, 0.2),
                (date '2025-01-20', 'Audio', 7, 99.0, 0.9)
            ) as weekly(week_start, category, ordered_quantity, average_unit_price,
                        effective_discount_rate);
        """)
    (tmp_path / "forecast.json").write_text(
        json.dumps(
            {
                "model": "seasonal_naive",
                "training_cutoff": "2025-01-13",
                "predictions": [
                    {"week_start": "2025-01-20", "category": "Audio", "prediction": 5}
                ],
                "fold_metrics": [
                    {"fold": 1, "model": "seasonal_naive", "mae": 2, "smape": 20}
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SALES_DUCKDB_PATH", str(db))
    monkeypatch.setenv("SALES_MODEL_DIR", str(tmp_path))
    return AppTest.from_file(str(APP), default_timeout=10).run()


@pytest.mark.parametrize(
    ("page", "title"),
    [
        ("1_executive_overview", "Executive overview"),
        ("2_customer_insights", "Customer insights"),
        ("3_basket_analysis", "Basket analysis"),
        ("4_forecasting_what_if", "Forecasting & What-If"),
    ],
)
def test_pages_open_with_downloads(app: AppTest, page: str, title: str) -> None:
    app.switch_page(f"pages/{page}.py").run()
    assert not app.exception
    assert app.title[0].value == title
    assert app.get("download_button")
    if page == "2_customer_insights":
        assert any("Propensity artifact" in message.value for message in app.info)
        assert any(item.value == "Days since last purchase" for item in app.subheader)
        assert app.dataframe[1].value.iloc[0].tolist() == [1.0, 0.0]


def test_basket_empty_selection_and_forecast_scenario_bounds(app: AppTest) -> None:
    app.switch_page("pages/3_basket_analysis.py").run()
    app.number_input(key="min_product_baskets").set_value(5).run()
    assert not app.exception
    assert any("No rules" in message.value for message in app.info)

    app.switch_page("pages/4_forecasting_what_if.py").run()
    assert not app.exception
    assert app.slider(key="scenario_price").min == 10
    assert app.slider(key="scenario_price").max == 20
    app.slider(key="scenario_price").set_value(10).run()
    assert not app.exception
    assert (
        next(
            metric.value for metric in app.metric if metric.label == "Scenario revenue"
        )
        == "$40.00"
    )
    app.slider(key="scenario_reference_units").set_value(4).run()
    assert not app.exception
    assert (
        next(
            metric.value for metric in app.metric if metric.label == "Scenario revenue"
        )
        == "$32.00"
    )
