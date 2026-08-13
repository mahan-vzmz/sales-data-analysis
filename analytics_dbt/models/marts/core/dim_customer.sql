select
    customer_id,
    signup_date,
    home_city,
    segment
from {{ ref('int_customers') }}
