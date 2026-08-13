select
    promotion_id,
    promotion_type,
    start_date,
    end_date,
    discount_policy
from {{ ref('int_promotions') }}
