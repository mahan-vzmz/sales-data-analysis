select promotions.*
from {{ ref('stg_promotions') }} promotions
inner join {{ ref('int_current_load') }} current_load
    on current_load.load_id = promotions._load_id
where not exists (
    select 1
    from {{ source('audit', 'validation_failures') }} failures
    where failures.load_id = promotions._load_id
      and failures.source_table = 'promotions'
      and (
          failures.source_row is null
          or failures.source_row = promotions._source_row
      )
)
