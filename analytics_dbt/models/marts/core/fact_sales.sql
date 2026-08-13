with sales_lines as (
    select
        items.line_id,
        items.order_id,
        cast(strftime(cast(orders.order_timestamp as date), '%Y%m%d') as bigint)
            as date_key,
        orders.customer_id,
        items.product_id,
        orders.channel as channel_key,
        customers.home_city as geography_key,
        orders.promotion_id,
        orders.payment_method as payment_method_key,
        items.quantity as ordered_quantity,
        items.unit_price,
        items.unit_cost,
        items.discount_rate,
        cast(round(items.quantity * items.unit_price, 2) as decimal(18, 2))
            as gross_sales,
        cast(round(items.quantity * items.unit_cost, 2) as decimal(18, 2))
            as cogs
    from {{ ref('int_order_items') }} items
    inner join {{ ref('int_orders') }} orders
        on orders.order_id = items.order_id
       and orders._load_id = items._load_id
    inner join {{ ref('int_customers') }} customers
        on customers.customer_id = orders.customer_id
       and customers._load_id = orders._load_id
),

discounted as (
    select
        *,
        cast(round(gross_sales * discount_rate, 2) as decimal(18, 2))
            as discount_amount
    from sales_lines
)

select
    * exclude (gross_sales, cogs, discount_amount),
    gross_sales,
    discount_amount,
    cast(gross_sales - discount_amount as decimal(18, 2)) as net_sales,
    cogs,
    cast(gross_sales - discount_amount - cogs as decimal(18, 2))
        as gross_profit
from discounted
