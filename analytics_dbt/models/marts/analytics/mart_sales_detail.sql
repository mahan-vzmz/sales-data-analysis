with returns_by_line as (
    select
        line_id,
        sum(returned_quantity) as returned_quantity,
        sum(returned_revenue) as returned_revenue,
        sum(profit_impact) as profit_impact
    from {{ ref('fact_returns') }}
    group by line_id
)

select
    sales.line_id,
    sales.order_id,
    dates.full_date as order_date,
    sales.channel_key as channel,
    products.category,
    sales.geography_key as home_city,
    sales.ordered_quantity,
    coalesce(returns.returned_quantity, 0) as returned_quantity,
    coalesce(returns.returned_revenue, 0) as returned_revenue,
    sales.net_sales - coalesce(returns.returned_revenue, 0) as return_adjusted_revenue,
    sales.gross_profit - coalesce(returns.profit_impact, 0) as return_adjusted_profit
from {{ ref('fact_sales') }} sales
join {{ ref('dim_date') }} dates using (date_key)
join {{ ref('dim_product') }} products using (product_id)
left join returns_by_line returns using (line_id)
