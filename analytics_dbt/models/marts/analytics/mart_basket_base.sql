with sales_products as (
    select
        sales.order_id,
        sales.customer_id,
        dates.full_date as order_date,
        sales.product_id,
        sum(sales.ordered_quantity) as ordered_quantity,
        sum(sales.net_sales) as net_sales
    from {{ ref('fact_sales') }} sales
    inner join {{ ref('dim_date') }} dates using (date_key)
    group by sales.order_id, sales.customer_id, dates.full_date, sales.product_id
),

return_products as (
    select
        order_id,
        product_id,
        sum(returned_quantity) as returned_quantity,
        sum(returned_revenue) as returned_revenue
    from {{ ref('fact_returns') }}
    group by order_id, product_id
),

remaining_products as (
    select
        sales.*,
        coalesce(returns.returned_quantity, 0) as returned_quantity,
        coalesce(returns.returned_revenue, 0) as returned_revenue
    from sales_products sales
    left join return_products returns using (order_id, product_id)
    where sales.ordered_quantity > coalesce(returns.returned_quantity, 0)
)

select
    remaining.order_id,
    remaining.customer_id,
    remaining.order_date,
    remaining.product_id,
    products.product_name,
    products.category,
    remaining.ordered_quantity,
    remaining.returned_quantity,
    remaining.ordered_quantity - remaining.returned_quantity
        as remaining_quantity,
    remaining.net_sales,
    remaining.returned_revenue,
    remaining.net_sales - remaining.returned_revenue as return_adjusted_value
from remaining_products remaining
inner join {{ ref('dim_product') }} products using (product_id)
