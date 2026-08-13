{{ config(materialized='ephemeral') }}

select load_id
from {{ source('audit', 'ingestion_runs') }}
where status = 'succeeded'
qualify row_number() over (
    order by completed_at desc, started_at desc, load_id desc
) = 1
