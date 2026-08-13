select distinct payment_method as payment_method_key
from {{ ref('int_orders') }}
