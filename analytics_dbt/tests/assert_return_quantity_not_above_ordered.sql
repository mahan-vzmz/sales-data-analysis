select returns.*
from {{ ref('int_returns') }} returns
inner join {{ ref('int_order_items') }} items using (line_id)
where returns.returned_quantity > items.quantity
