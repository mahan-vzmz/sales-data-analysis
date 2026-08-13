select
    cast(trim(return_id) as varchar) as return_id,
    cast(trim(line_id) as varchar) as line_id,
    cast(return_date as date) as return_date,
    cast(returned_quantity as bigint) as returned_quantity,
    nullif(trim(reason), '') as reason,
    cast(_load_id as varchar) as _load_id,
    cast(_source_file as varchar) as _source_file,
    cast(_source_row as bigint) as _source_row,
    cast(_ingested_at as timestamp) as _ingested_at
from {{ source('bronze', 'returns') }}
