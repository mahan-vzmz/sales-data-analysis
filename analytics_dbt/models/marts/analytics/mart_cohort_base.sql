with sales_orders as (
    select
        sales.order_id,
        sales.customer_id,
        dates.full_date as order_date,
        date_trunc('month', dates.full_date)::date as order_month,
        sum(sales.ordered_quantity) as ordered_quantity,
        sum(sales.net_sales) as net_sales
    from {{ ref('fact_sales') }} sales
    inner join {{ ref('dim_date') }} dates using (date_key)
    group by sales.order_id, sales.customer_id, dates.full_date
),

return_orders as (
    select
        order_id,
        sum(returned_quantity) as returned_quantity,
        sum(returned_revenue) as returned_revenue
    from {{ ref('fact_returns') }}
    group by order_id
),

completed_orders as (
    select
        sales.*,
        coalesce(returns.returned_quantity, 0) as returned_quantity,
        coalesce(returns.returned_revenue, 0) as returned_revenue
    from sales_orders sales
    left join return_orders returns using (order_id)
    where sales.ordered_quantity > coalesce(returns.returned_quantity, 0)
)

select
    order_id,
    customer_id,
    order_date,
    order_month,
    min(order_month) over (partition by customer_id) as acquisition_cohort_month,
    date_diff(
        'month',
        min(order_month) over (partition by customer_id),
        order_month
    ) as months_since_acquisition,
    ordered_quantity,
    returned_quantity,
    ordered_quantity - returned_quantity as retained_quantity,
    net_sales,
    returned_revenue,
    net_sales - returned_revenue as return_adjusted_value
from completed_orders
