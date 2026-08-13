select returns.*
from {{ ref('int_returns') }} returns
inner join {{ ref('int_order_items') }} items using (line_id)
inner join {{ ref('int_orders') }} orders using (order_id)
where returns.return_date < cast(orders.order_timestamp as date)
