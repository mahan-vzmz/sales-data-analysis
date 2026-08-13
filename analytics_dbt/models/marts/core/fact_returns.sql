with return_lines as (
    select
        returns.return_id,
        returns.line_id,
        items.order_id,
        cast(strftime(returns.return_date, '%Y%m%d') as bigint) as return_date_key,
        cast(strftime(cast(orders.order_timestamp as date), '%Y%m%d') as bigint)
            as order_date_key,
        orders.customer_id,
        items.product_id,
        orders.channel as channel_key,
        customers.home_city as geography_key,
        orders.promotion_id,
        orders.payment_method as payment_method_key,
        returns.returned_quantity,
        returns.reason as return_reason,
        items.unit_price,
        items.unit_cost,
        items.discount_rate,
        cast(
            round(
                returns.returned_quantity * items.unit_price * (1 - items.discount_rate),
                2
            ) as decimal(18, 2)
        ) as returned_revenue,
        cast(
            round(returns.returned_quantity * items.unit_cost, 2)
            as decimal(18, 2)
        ) as reversed_cogs
    from {{ ref('int_returns') }} returns
    inner join {{ ref('int_order_items') }} items
        on items.line_id = returns.line_id
       and items._load_id = returns._load_id
    inner join {{ ref('int_orders') }} orders
        on orders.order_id = items.order_id
       and orders._load_id = items._load_id
    inner join {{ ref('int_customers') }} customers
        on customers.customer_id = orders.customer_id
       and customers._load_id = orders._load_id
)

select
    *,
    cast(returned_revenue - reversed_cogs as decimal(18, 2)) as profit_impact
from return_lines
