select products.*
from {{ ref('stg_products') }} products
inner join {{ ref('int_current_load') }} current_load
    on current_load.load_id = products._load_id
where not exists (
    select 1
    from {{ source('audit', 'validation_failures') }} failures
    where failures.load_id = products._load_id
      and failures.source_table = 'products'
      and (failures.source_row is null or failures.source_row = products._source_row)
)
