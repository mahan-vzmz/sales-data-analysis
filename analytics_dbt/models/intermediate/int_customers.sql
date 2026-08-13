select customers.*
from {{ ref('stg_customers') }} customers
inner join {{ ref('int_current_load') }} current_load
    on current_load.load_id = customers._load_id
where not exists (
    select 1
    from {{ source('audit', 'validation_failures') }} failures
    where failures.load_id = customers._load_id
      and failures.source_table = 'customers'
      and (failures.source_row is null or failures.source_row = customers._source_row)
)
