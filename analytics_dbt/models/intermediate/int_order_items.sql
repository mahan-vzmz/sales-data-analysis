select items.*
from {{ ref('stg_order_items') }} items
inner join {{ ref('int_current_load') }} current_load
    on current_load.load_id = items._load_id
where not exists (
    select 1
    from {{ source('audit', 'validation_failures') }} failures
    where failures.load_id = items._load_id
      and failures.source_table = 'order_items'
      and (failures.source_row is null or failures.source_row = items._source_row)
)
and exists (
    select 1
    from {{ ref('int_orders') }} orders
    where orders.order_id = items.order_id
      and orders._load_id = items._load_id
)
and exists (
    select 1
    from {{ ref('int_products') }} products
    where products.product_id = items.product_id
      and products._load_id = items._load_id
)
