select
    cast(trim(line_id) as varchar) as line_id,
    cast(trim(order_id) as varchar) as order_id,
    cast(trim(product_id) as varchar) as product_id,
    cast(quantity as bigint) as quantity,
    cast(unit_price as decimal(18, 2)) as unit_price,
    cast(unit_cost as decimal(18, 2)) as unit_cost,
    cast(discount_rate as decimal(9, 4)) as discount_rate,
    cast(_load_id as varchar) as _load_id,
    cast(_source_file as varchar) as _source_file,
    cast(_source_row as bigint) as _source_row,
    cast(_ingested_at as timestamp) as _ingested_at
from {{ source('bronze', 'order_items') }}
