select *
from {{ ref('int_order_items') }}
where quantity <= 0
   or unit_cost < 0
   or unit_price <= 0
