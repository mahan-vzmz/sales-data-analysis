select
    cast(trim(customer_id) as varchar) as customer_id,
    cast(signup_date as date) as signup_date,
    nullif(trim(home_city), '') as home_city,
    nullif(trim(segment), '') as segment,
    cast(_load_id as varchar) as _load_id,
    cast(_source_file as varchar) as _source_file,
    cast(_source_row as bigint) as _source_row,
    cast(_ingested_at as timestamp) as _ingested_at
from {{ source('bronze', 'customers') }}
