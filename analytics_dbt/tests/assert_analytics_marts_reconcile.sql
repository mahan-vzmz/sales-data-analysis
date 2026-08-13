with sales as (
    select
        count(*) as sales_line_count,
        count(distinct order_id) as order_count,
        count(distinct customer_id) as customer_count,
        sum(ordered_quantity) as ordered_quantity,
        sum(gross_sales) as gross_sales,
        sum(discount_amount) as discount_amount,
        sum(net_sales) as net_sales,
        sum(cogs) as cogs,
        sum(gross_profit) as gross_profit
    from {{ ref('fact_sales') }}
),

returns as (
    select
        count(*) as return_event_count,
        coalesce(sum(returned_quantity), 0) as returned_quantity,
        coalesce(sum(returned_revenue), 0) as returned_revenue,
        coalesce(sum(reversed_cogs), 0) as reversed_cogs,
        coalesce(sum(profit_impact), 0) as profit_impact
    from {{ ref('fact_returns') }}
),

sales_orders as (
    select
        order_id,
        max(customer_id) as customer_id,
        sum(ordered_quantity) as ordered_quantity,
        sum(net_sales) as net_sales
    from {{ ref('fact_sales') }}
    group by order_id
),

return_orders as (
    select
        order_id,
        sum(returned_quantity) as returned_quantity,
        sum(returned_revenue) as returned_revenue
    from {{ ref('fact_returns') }}
    group by order_id
),

eligible_orders as (
    select
        sales.*,
        coalesce(returns.returned_quantity, 0) as returned_quantity,
        coalesce(returns.returned_revenue, 0) as returned_revenue
    from sales_orders sales
    left join return_orders returns using (order_id)
    where sales.ordered_quantity > coalesce(returns.returned_quantity, 0)
),

sales_order_products as (
    select
        order_id,
        product_id,
        max(customer_id) as customer_id,
        sum(ordered_quantity) as ordered_quantity,
        sum(net_sales) as net_sales
    from {{ ref('fact_sales') }}
    group by order_id, product_id
),

return_order_products as (
    select
        order_id,
        product_id,
        sum(returned_quantity) as returned_quantity,
        sum(returned_revenue) as returned_revenue
    from {{ ref('fact_returns') }}
    group by order_id, product_id
),

eligible_order_products as (
    select
        sales.*,
        coalesce(returns.returned_quantity, 0) as returned_quantity,
        coalesce(returns.returned_revenue, 0) as returned_revenue
    from sales_order_products sales
    left join return_order_products returns using (order_id, product_id)
    where sales.ordered_quantity > coalesce(returns.returned_quantity, 0)
),

failures as (
    select 'executive_grain_or_totals' as check_name
    from {{ ref('mart_executive') }} executive
    cross join sales
    cross join returns
    where executive.sales_line_count <> sales.sales_line_count
       or executive.order_count <> sales.order_count
       or executive.customer_count <> sales.customer_count
       or executive.ordered_quantity <> sales.ordered_quantity
       or executive.return_event_count <> returns.return_event_count
       or executive.returned_quantity <> returns.returned_quantity
       or abs(executive.gross_sales - sales.gross_sales) > 0.01
       or abs(executive.discount_amount - sales.discount_amount) > 0.01
       or abs(executive.net_sales - sales.net_sales) > 0.01
       or abs(executive.cogs - sales.cogs) > 0.01
       or abs(executive.gross_profit - sales.gross_profit) > 0.01
       or abs(executive.returned_revenue - returns.returned_revenue) > 0.01
       or abs(executive.reversed_cogs - returns.reversed_cogs) > 0.01
       or abs(executive.profit_impact - returns.profit_impact) > 0.01
       or abs(
            executive.return_adjusted_revenue
            - (sales.net_sales - returns.returned_revenue)
       ) > 0.01
       or abs(
            executive.return_adjusted_profit
            - (sales.gross_profit - returns.profit_impact)
       ) > 0.01

    union all

    select 'executive_row_count'
    where (select count(*) from {{ ref('mart_executive') }}) <> 1

    union all

    select 'customer_totals'
    from {{ ref('mart_customer_360') }} customers
    cross join sales
    cross join returns
    having sum(customers.order_count) <> max(sales.order_count)
       or sum(customers.ordered_quantity) <> max(sales.ordered_quantity)
       or sum(customers.returned_quantity) <> max(returns.returned_quantity)
       or abs(sum(customers.gross_sales) - max(sales.gross_sales)) > 0.01
       or abs(sum(customers.discount_amount) - max(sales.discount_amount)) > 0.01
       or abs(sum(customers.net_sales) - max(sales.net_sales)) > 0.01
       or abs(sum(customers.returned_revenue) - max(returns.returned_revenue)) > 0.01
       or abs(sum(customers.cogs) - max(sales.cogs)) > 0.01
       or abs(sum(customers.reversed_cogs) - max(returns.reversed_cogs)) > 0.01
       or abs(sum(customers.gross_profit) - max(sales.gross_profit)) > 0.01
       or abs(sum(customers.profit_impact) - max(returns.profit_impact)) > 0.01
       or abs(
            sum(customers.return_adjusted_value)
            - (max(sales.net_sales) - max(returns.returned_revenue))
       ) > 0.01
       or abs(
            sum(customers.return_adjusted_profit)
            - (max(sales.gross_profit) - max(returns.profit_impact))
       ) > 0.01

    union all

    select 'cohort_population'
    where (select count(*) from {{ ref('mart_cohort_base') }})
        <> (select count(*) from eligible_orders)

    union all

    select 'cohort_measures'
    from eligible_orders expected
    full outer join {{ ref('mart_cohort_base') }} actual using (order_id)
    where expected.order_id is null
       or actual.order_id is null
       or expected.customer_id <> actual.customer_id
       or expected.ordered_quantity <> actual.ordered_quantity
       or expected.returned_quantity <> actual.returned_quantity
       or expected.ordered_quantity - expected.returned_quantity
            <> actual.retained_quantity
       or abs(expected.net_sales - actual.net_sales) > 0.01
       or abs(expected.returned_revenue - actual.returned_revenue) > 0.01
       or abs(
            expected.net_sales - expected.returned_revenue
            - actual.return_adjusted_value
       ) > 0.01

    union all

    select 'basket_measures'
    from eligible_order_products expected
    full outer join {{ ref('mart_basket_base') }} actual
        using (order_id, product_id)
    where expected.order_id is null
       or actual.order_id is null
       or expected.product_id is null
       or actual.product_id is null
       or expected.customer_id <> actual.customer_id
       or expected.ordered_quantity <> actual.ordered_quantity
       or expected.returned_quantity <> actual.returned_quantity
       or expected.ordered_quantity - expected.returned_quantity
            <> actual.remaining_quantity
       or abs(expected.net_sales - actual.net_sales) > 0.01
       or abs(expected.returned_revenue - actual.returned_revenue) > 0.01
       or abs(
            expected.net_sales - expected.returned_revenue
            - actual.return_adjusted_value
       ) > 0.01

    union all

    select 'forecast_totals'
    from {{ ref('mart_forecasting_base') }} forecast
    cross join sales
    cross join returns
    having sum(forecast.order_count) < max(sales.order_count)
       or sum(forecast.ordered_quantity) <> max(sales.ordered_quantity)
       or sum(forecast.returned_quantity) <> max(returns.returned_quantity)
       or abs(sum(forecast.gross_sales) - max(sales.gross_sales)) > 0.01
       or abs(sum(forecast.discount_amount) - max(sales.discount_amount)) > 0.01
       or abs(sum(forecast.net_sales) - max(sales.net_sales)) > 0.01
       or abs(sum(forecast.returned_revenue) - max(returns.returned_revenue)) > 0.01
       or abs(sum(forecast.cogs) - max(sales.cogs)) > 0.01
       or abs(sum(forecast.reversed_cogs) - max(returns.reversed_cogs)) > 0.01
       or abs(sum(forecast.gross_profit) - max(sales.gross_profit)) > 0.01
       or abs(sum(forecast.profit_impact) - max(returns.profit_impact)) > 0.01
       or abs(
            sum(forecast.return_adjusted_revenue)
            - (max(sales.net_sales) - max(returns.returned_revenue))
       ) > 0.01
       or abs(
            sum(forecast.return_adjusted_profit)
            - (max(sales.gross_profit) - max(returns.profit_impact))
       ) > 0.01
)

select * from failures
