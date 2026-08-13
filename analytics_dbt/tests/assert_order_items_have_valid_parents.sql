select items.*
from {{ ref('int_order_items') }} items
left join {{ ref('int_orders') }} orders using (order_id)
left join {{ ref('int_customers') }} customers using (customer_id)
left join {{ ref('int_products') }} products using (product_id)
where orders.order_id is null
   or customers.customer_id is null
   or products.product_id is null
