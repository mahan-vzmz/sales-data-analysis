with calendar as (
    select events.*
    from {{ ref('stg_calendar_events') }} events
    inner join {{ ref('int_current_load') }} current_load
        on current_load.load_id = events._load_id
),

date_spine as (
    select unnest(
        generate_series(min(event_date), max(event_date), interval 1 day)
    )::date as full_date
    from calendar
)

select
    cast(strftime(dates.full_date, '%Y%m%d') as bigint) as date_key,
    dates.full_date,
    year(dates.full_date) as year_number,
    quarter(dates.full_date) as quarter_number,
    month(dates.full_date) as month_number,
    monthname(dates.full_date) as month_name,
    day(dates.full_date) as day_of_month,
    dayofweek(dates.full_date) as day_of_week,
    dayname(dates.full_date) as day_name,
    calendar.holiday,
    calendar.campaign,
    calendar.seasonal_event
from date_spine dates
left join calendar on calendar.event_date = dates.full_date
