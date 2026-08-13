select
    cast(trim(order_id) as varchar) as order_id,
    cast(trim(customer_id) as varchar) as customer_id,
    cast(order_timestamp as timestamp) as order_timestamp,
    nullif(trim(channel), '') as channel,
    nullif(trim(payment_method), '') as payment_method,
    nullif(trim(promotion_id), '') as promotion_id,
    cast(_load_id as varchar) as _load_id,
    cast(_source_file as varchar) as _source_file,
    cast(_source_row as bigint) as _source_row,
    cast(_ingested_at as timestamp) as _ingested_at
from {{ source('bronze', 'orders') }}
