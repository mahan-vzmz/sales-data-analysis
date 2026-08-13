select
    cast(trim(promotion_id) as varchar) as promotion_id,
    nullif(trim(promotion_type), '') as promotion_type,
    cast(start_date as date) as start_date,
    cast(end_date as date) as end_date,
    cast(discount_policy as decimal(9, 4)) as discount_policy,
    cast(_load_id as varchar) as _load_id,
    cast(_source_file as varchar) as _source_file,
    cast(_source_row as bigint) as _source_row,
    cast(_ingested_at as timestamp) as _ingested_at
from {{ source('bronze', 'promotions') }}
