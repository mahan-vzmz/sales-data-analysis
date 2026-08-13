select orders.*
from {{ ref('stg_orders') }} orders
inner join {{ ref('int_current_load') }} current_load
    on current_load.load_id = orders._load_id
where not exists (
    select 1
    from {{ source('audit', 'validation_failures') }} failures
    where failures.load_id = orders._load_id
      and failures.source_table = 'orders'
      and (failures.source_row is null or failures.source_row = orders._source_row)
)
and exists (
    select 1
    from {{ ref('int_customers') }} customers
    where customers.customer_id = orders.customer_id
      and customers._load_id = orders._load_id
)
and (
    orders.promotion_id is null
    or exists (
        select 1
        from {{ ref('int_promotions') }} promotions
        where promotions.promotion_id = orders.promotion_id
          and promotions._load_id = orders._load_id
    )
)
