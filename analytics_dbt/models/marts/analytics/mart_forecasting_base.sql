with weeks as (
    select
        date_trunc('week', full_date)::date as week_start,
        count(*) filter (where holiday is not null) as holiday_days,
        count(*) filter (where campaign is not null) as campaign_days
    from {{ ref('dim_date') }}
    group by week_start
),

categories as (
    select distinct category
    from {{ ref('dim_product') }}
),

sales as (
    select
        date_trunc('week', dates.full_date)::date as week_start,
        products.category,
        count(distinct facts.order_id) as order_count,
        sum(facts.ordered_quantity) as ordered_quantity,
        sum(facts.gross_sales) as gross_sales,
        sum(facts.discount_amount) as discount_amount,
        sum(facts.net_sales) as net_sales,
        sum(facts.cogs) as cogs,
        sum(facts.gross_profit) as gross_profit,
        sum(facts.gross_sales) / nullif(sum(facts.ordered_quantity), 0)
            as average_unit_price,
        sum(facts.discount_amount) / nullif(sum(facts.gross_sales), 0)
            as effective_discount_rate,
        count(distinct facts.order_id) filter (where promotion_id is not null)
            as promoted_order_count,
        sum(facts.ordered_quantity) filter (where channel_key = 'Online')
            / sum(facts.ordered_quantity) as online_unit_share,
        sum(facts.ordered_quantity) filter (where channel_key = 'Store')
            / sum(facts.ordered_quantity) as store_unit_share,
        sum(facts.ordered_quantity) filter (where channel_key = 'Marketplace')
            / sum(facts.ordered_quantity) as marketplace_unit_share
    from {{ ref('fact_sales') }} facts
    inner join {{ ref('dim_date') }} dates using (date_key)
    inner join {{ ref('dim_product') }} products using (product_id)
    group by week_start, products.category
),

returns as (
    select
        date_trunc('week', dates.full_date)::date as week_start,
        products.category,
        sum(facts.returned_quantity) as returned_quantity,
        sum(facts.returned_revenue) as returned_revenue,
        sum(facts.reversed_cogs) as reversed_cogs,
        sum(facts.profit_impact) as profit_impact
    from {{ ref('fact_returns') }} facts
    inner join {{ ref('dim_date') }} dates
        on dates.date_key = facts.order_date_key
    inner join {{ ref('dim_product') }} products using (product_id)
    group by week_start, products.category
)

select
    weeks.week_start,
    categories.category,
    weeks.holiday_days,
    weeks.campaign_days,
    coalesce(sales.order_count, 0) as order_count,
    coalesce(sales.ordered_quantity, 0) as ordered_quantity,
    coalesce(returns.returned_quantity, 0) as returned_quantity,
    coalesce(sales.gross_sales, 0) as gross_sales,
    coalesce(sales.discount_amount, 0) as discount_amount,
    coalesce(sales.net_sales, 0) as net_sales,
    coalesce(returns.returned_revenue, 0) as returned_revenue,
    coalesce(sales.net_sales, 0) - coalesce(returns.returned_revenue, 0)
        as return_adjusted_revenue,
    coalesce(sales.cogs, 0) as cogs,
    coalesce(returns.reversed_cogs, 0) as reversed_cogs,
    coalesce(sales.gross_profit, 0) as gross_profit,
    coalesce(returns.profit_impact, 0) as profit_impact,
    coalesce(sales.gross_profit, 0) - coalesce(returns.profit_impact, 0)
        as return_adjusted_profit,
    sales.average_unit_price,
    sales.effective_discount_rate,
    coalesce(sales.promoted_order_count, 0) as promoted_order_count,
    coalesce(sales.online_unit_share, 0) as online_unit_share,
    coalesce(sales.store_unit_share, 0) as store_unit_share,
    coalesce(sales.marketplace_unit_share, 0) as marketplace_unit_share
from weeks
cross join categories
left join sales using (week_start, category)
left join returns using (week_start, category)
