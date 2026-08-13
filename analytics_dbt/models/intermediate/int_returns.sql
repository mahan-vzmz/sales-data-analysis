select returns.*
from {{ ref('stg_returns') }} returns
inner join {{ ref('int_current_load') }} current_load
    on current_load.load_id = returns._load_id
where not exists (
    select 1
    from {{ source('audit', 'validation_failures') }} failures
    where failures.load_id = returns._load_id
      and failures.source_table = 'returns'
      and (failures.source_row is null or failures.source_row = returns._source_row)
)
and exists (
    select 1
    from {{ ref('int_order_items') }} items
    where items.line_id = returns.line_id
      and items._load_id = returns._load_id
)
