with current_load as (
    select load_id
    from {{ ref('int_current_load') }}
),

source_counts as (
    select 'customers' as source_table, count(*) as source_count
    from {{ source('bronze', 'customers') }}
    inner join current_load on _load_id = load_id

    union all
    select 'products', count(*)
    from {{ source('bronze', 'products') }}
    inner join current_load on _load_id = load_id

    union all
    select 'promotions', count(*)
    from {{ source('bronze', 'promotions') }}
    inner join current_load on _load_id = load_id

    union all
    select 'orders', count(*)
    from {{ source('bronze', 'orders') }}
    inner join current_load on _load_id = load_id

    union all
    select 'order_items', count(*)
    from {{ source('bronze', 'order_items') }}
    inner join current_load on _load_id = load_id

    union all
    select 'returns', count(*)
    from {{ source('bronze', 'returns') }}
    inner join current_load on _load_id = load_id
),

accepted_counts as (
    select 'customers' as source_table, count(*) as accepted_count
    from {{ ref('int_customers') }}

    union all
    select 'products', count(*) from {{ ref('int_products') }}

    union all
    select 'promotions', count(*) from {{ ref('int_promotions') }}

    union all
    select 'orders', count(*) from {{ ref('int_orders') }}

    union all
    select 'order_items', count(*) from {{ ref('int_order_items') }}

    union all
    select 'returns', count(*) from {{ ref('int_returns') }}
),

rejected_counts as (
    select source_table, count(distinct source_row) as rejected_count
    from {{ ref('int_rejected_records') }}
    group by source_table
)

select
    sources.source_table,
    sources.source_count,
    accepted.accepted_count,
    coalesce(rejected.rejected_count, 0) as rejected_count
from source_counts as sources
inner join accepted_counts as accepted using (source_table)
left join rejected_counts as rejected using (source_table)
where sources.source_count
    <> accepted.accepted_count + coalesce(rejected.rejected_count, 0)
