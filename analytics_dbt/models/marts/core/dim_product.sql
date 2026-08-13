select
    product_id,
    product_name,
    category,
    base_price,
    base_cost
from {{ ref('int_products') }}
