select distinct home_city as geography_key
from {{ ref('int_customers') }}
