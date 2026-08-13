select distinct channel as channel_key
from {{ ref('int_orders') }}
