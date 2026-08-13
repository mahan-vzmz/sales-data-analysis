select
    cast(date as date) as event_date,
    nullif(trim(holiday), '') as holiday,
    nullif(trim(campaign), '') as campaign,
    nullif(trim(seasonal_event), '') as seasonal_event,
    cast(_load_id as varchar) as _load_id,
    cast(_source_file as varchar) as _source_file,
    cast(_source_row as bigint) as _source_row,
    cast(_ingested_at as timestamp) as _ingested_at
from {{ source('bronze', 'calendar_events') }}
