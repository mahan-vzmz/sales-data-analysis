with sales as (
    select
        count(*) as sales_line_count,
        count(distinct order_id) as order_count,
        count(distinct customer_id) as customer_count,
        sum(ordered_quantity) as ordered_quantity,
        sum(gross_sales) as gross_sales,
        sum(discount_amount) as discount_amount,
        sum(net_sales) as net_sales,
        sum(cogs) as cogs,
        sum(gross_profit) as gross_profit
    from {{ ref('fact_sales') }}
),

returns as (
    select
        count(*) as return_event_count,
        coalesce(sum(returned_quantity), 0) as returned_quantity,
        coalesce(sum(returned_revenue), 0) as returned_revenue,
        coalesce(sum(reversed_cogs), 0) as reversed_cogs,
        coalesce(sum(profit_impact), 0) as profit_impact
    from {{ ref('fact_returns') }}
)

select
    sales.*,
    returns.return_event_count,
    returns.returned_quantity,
    returns.returned_revenue,
    returns.reversed_cogs,
    returns.profit_impact,
    sales.net_sales - returns.returned_revenue as return_adjusted_revenue,
    sales.gross_profit - returns.profit_impact as return_adjusted_profit
from sales
cross join returns
