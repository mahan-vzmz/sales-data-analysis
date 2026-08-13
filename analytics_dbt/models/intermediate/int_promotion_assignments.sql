select
    orders.order_id,
    orders.promotion_id,
    orders._load_id,
    orders._source_file,
    orders._source_row,
    orders._ingested_at
from {{ ref('int_orders') }} orders
inner join {{ ref('int_promotions') }} promotions
    on promotions.promotion_id = orders.promotion_id
   and promotions._load_id = orders._load_id
where orders.promotion_id is not null
