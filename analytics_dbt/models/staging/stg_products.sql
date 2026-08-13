select
    cast(trim(product_id) as varchar) as product_id,
    nullif(trim(name), '') as product_name,
    nullif(trim(category), '') as category,
    cast(base_price as decimal(18, 2)) as base_price,
    cast(base_cost as decimal(18, 2)) as base_cost,
    cast(_load_id as varchar) as _load_id,
    cast(_source_file as varchar) as _source_file,
    cast(_source_row as bigint) as _source_row,
    cast(_ingested_at as timestamp) as _ingested_at
from {{ source('bronze', 'products') }}
