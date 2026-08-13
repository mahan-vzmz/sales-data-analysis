with sales_orders as (
    select
        sales.customer_id,
        sales.order_id,
        dates.full_date as order_date,
        sum(sales.ordered_quantity) as ordered_quantity,
        sum(sales.gross_sales) as gross_sales,
        sum(sales.discount_amount) as discount_amount,
        sum(sales.net_sales) as net_sales,
        sum(sales.cogs) as cogs,
        sum(sales.gross_profit) as gross_profit
    from {{ ref('fact_sales') }} sales
    inner join {{ ref('dim_date') }} dates using (date_key)
    group by sales.customer_id, sales.order_id, dates.full_date
),

return_orders as (
    select
        customer_id,
        order_id,
        sum(returned_quantity) as returned_quantity,
        sum(returned_revenue) as returned_revenue,
        sum(reversed_cogs) as reversed_cogs,
        sum(profit_impact) as profit_impact
    from {{ ref('fact_returns') }}
    group by customer_id, order_id
),

orders as (
    select
        sales.*,
        coalesce(returns.returned_quantity, 0) as returned_quantity,
        coalesce(returns.returned_revenue, 0) as returned_revenue,
        coalesce(returns.reversed_cogs, 0) as reversed_cogs,
        coalesce(returns.profit_impact, 0) as profit_impact,
        sales.ordered_quantity > coalesce(returns.returned_quantity, 0)
            as is_completed_purchase
    from sales_orders sales
    left join return_orders returns using (customer_id, order_id)
),

customer_metrics as (
    select
        customer_id,
        min(order_date) filter (where is_completed_purchase) as first_purchase_date,
        max(order_date) filter (where is_completed_purchase) as last_purchase_date,
        count(*) as order_count,
        count(*) filter (where is_completed_purchase) as completed_order_count,
        sum(ordered_quantity) as ordered_quantity,
        sum(returned_quantity) as returned_quantity,
        sum(gross_sales) as gross_sales,
        sum(discount_amount) as discount_amount,
        sum(net_sales) as net_sales,
        sum(returned_revenue) as returned_revenue,
        sum(cogs) as cogs,
        sum(reversed_cogs) as reversed_cogs,
        sum(gross_profit) as gross_profit,
        sum(profit_impact) as profit_impact
    from orders
    group by customer_id
)

select
    customers.customer_id,
    customers.signup_date,
    customers.home_city,
    customers.segment,
    metrics.first_purchase_date,
    metrics.last_purchase_date,
    coalesce(metrics.order_count, 0) as order_count,
    coalesce(metrics.completed_order_count, 0) as completed_order_count,
    coalesce(metrics.ordered_quantity, 0) as ordered_quantity,
    coalesce(metrics.returned_quantity, 0) as returned_quantity,
    coalesce(metrics.gross_sales, 0) as gross_sales,
    coalesce(metrics.discount_amount, 0) as discount_amount,
    coalesce(metrics.net_sales, 0) as net_sales,
    coalesce(metrics.returned_revenue, 0) as returned_revenue,
    coalesce(metrics.net_sales, 0) - coalesce(metrics.returned_revenue, 0)
        as return_adjusted_value,
    coalesce(metrics.cogs, 0) as cogs,
    coalesce(metrics.reversed_cogs, 0) as reversed_cogs,
    coalesce(metrics.gross_profit, 0) as gross_profit,
    coalesce(metrics.profit_impact, 0) as profit_impact,
    coalesce(metrics.gross_profit, 0) - coalesce(metrics.profit_impact, 0)
        as return_adjusted_profit
from {{ ref('dim_customer') }} customers
left join customer_metrics metrics using (customer_id)
