with sales_failures as (
    select 'fact_sales' as model_name, line_id as record_id
    from {{ ref('fact_sales') }}
    where gross_sales <> round(ordered_quantity * unit_price, 2)
       or discount_amount <> round(gross_sales * discount_rate, 2)
       or net_sales <> gross_sales - discount_amount
       or cogs <> round(ordered_quantity * unit_cost, 2)
       or gross_profit <> net_sales - cogs
),

return_failures as (
    select 'fact_returns' as model_name, return_id as record_id
    from {{ ref('fact_returns') }}
    where returned_revenue
            <> round(returned_quantity * unit_price * (1 - discount_rate), 2)
       or reversed_cogs <> round(returned_quantity * unit_cost, 2)
       or profit_impact <> returned_revenue - reversed_cogs
)

select * from sales_failures
union all
select * from return_failures
