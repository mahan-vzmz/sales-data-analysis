with staged_rows as (
    select
        'customers' as source_table,
        _load_id as load_id,
        _source_row as source_row,
        _source_file as source_file
    from {{ ref('stg_customers') }}
    union all
    select 'products', _load_id, _source_row, _source_file
    from {{ ref('stg_products') }}
    union all
    select 'promotions', _load_id, _source_row, _source_file
    from {{ ref('stg_promotions') }}
    union all
    select 'orders', _load_id, _source_row, _source_file
    from {{ ref('stg_orders') }}
    union all
    select 'order_items', _load_id, _source_row, _source_file
    from {{ ref('stg_order_items') }}
    union all
    select 'returns', _load_id, _source_row, _source_file
    from {{ ref('stg_returns') }}
),
current_rows as (
    select rows.*
    from staged_rows rows
    inner join {{ ref('int_current_load') }} current_load
        on current_load.load_id = rows.load_id
),
direct_rejections as (
    select
        rows.load_id,
        rows.source_table,
        rows.source_row,
        rows.source_file,
        failures.check_name as rule_code,
        coalesce(
            cast(failures.failure_case as varchar),
            failures.column_name || ' failed ' || failures.check_name
        ) as reason
    from current_rows rows
    inner join {{ source('audit', 'validation_failures') }} failures
        on failures.load_id = rows.load_id
       and failures.source_table = rows.source_table
       and (
           failures.source_row is null
           or failures.source_row = rows.source_row
       )
),
cascade_rejections as (
    select
        orders._load_id as load_id,
        'orders' as source_table,
        orders._source_row as source_row,
        orders._source_file as source_file,
        'customer_not_accepted' as rule_code,
        'customer parent was rejected during conformance' as reason
    from {{ ref('stg_orders') }} orders
    inner join {{ ref('int_current_load') }} current_load
        on current_load.load_id = orders._load_id
    left join {{ ref('int_customers') }} customers
        on customers.customer_id = orders.customer_id
       and customers._load_id = orders._load_id
    where customers.customer_id is null
      and not exists (
          select 1 from direct_rejections direct
          where direct.load_id = orders._load_id
            and direct.source_table = 'orders'
            and direct.source_row = orders._source_row
      )

    union all

    select
        orders._load_id,
        'orders',
        orders._source_row,
        orders._source_file,
        'promotion_not_accepted',
        'promotion parent was rejected during conformance'
    from {{ ref('stg_orders') }} orders
    inner join {{ ref('int_current_load') }} current_load
        on current_load.load_id = orders._load_id
    left join {{ ref('int_promotions') }} promotions
        on promotions.promotion_id = orders.promotion_id
       and promotions._load_id = orders._load_id
    where orders.promotion_id is not null
      and promotions.promotion_id is null
      and not exists (
          select 1 from direct_rejections direct
          where direct.load_id = orders._load_id
            and direct.source_table = 'orders'
            and direct.source_row = orders._source_row
      )

    union all

    select
        items._load_id,
        'order_items',
        items._source_row,
        items._source_file,
        'order_not_accepted',
        'order parent was rejected during conformance'
    from {{ ref('stg_order_items') }} items
    inner join {{ ref('int_current_load') }} current_load
        on current_load.load_id = items._load_id
    left join {{ ref('int_orders') }} orders
        on orders.order_id = items.order_id
       and orders._load_id = items._load_id
    where orders.order_id is null
      and not exists (
          select 1 from direct_rejections direct
          where direct.load_id = items._load_id
            and direct.source_table = 'order_items'
            and direct.source_row = items._source_row
      )

    union all

    select
        items._load_id,
        'order_items',
        items._source_row,
        items._source_file,
        'product_not_accepted',
        'product parent was rejected during conformance'
    from {{ ref('stg_order_items') }} items
    inner join {{ ref('int_current_load') }} current_load
        on current_load.load_id = items._load_id
    left join {{ ref('int_products') }} products
        on products.product_id = items.product_id
       and products._load_id = items._load_id
    where products.product_id is null
      and not exists (
          select 1 from direct_rejections direct
          where direct.load_id = items._load_id
            and direct.source_table = 'order_items'
            and direct.source_row = items._source_row
      )

    union all

    select
        returns._load_id,
        'returns',
        returns._source_row,
        returns._source_file,
        'order_item_not_accepted',
        'order-item parent was rejected during conformance'
    from {{ ref('stg_returns') }} returns
    inner join {{ ref('int_current_load') }} current_load
        on current_load.load_id = returns._load_id
    left join {{ ref('int_order_items') }} items
        on items.line_id = returns.line_id
       and items._load_id = returns._load_id
    where items.line_id is null
      and not exists (
          select 1 from direct_rejections direct
          where direct.load_id = returns._load_id
            and direct.source_table = 'returns'
            and direct.source_row = returns._source_row
      )
)

select * from direct_rejections
union all
select * from cascade_rejections
