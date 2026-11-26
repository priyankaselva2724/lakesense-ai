{% if target.type == 'postgres' %}
select cast(d as date) as date_key, extract(year from d)::int as year, extract(month from d)::int as month,
       extract(day from d)::int as day, trim(to_char(d, 'Day')) as weekday,
       extract(isodow from d) in (6, 7) as is_weekend
from generate_series(timestamp '2025-01-01', timestamp '2026-12-31', interval '1 day') as t(d)
{% else %}
select cast(d as date) as date_key, year(d) as year, month(d) as month, day(d) as day,
       dayname(d) as weekday, isodow(d) in (6, 7) as is_weekend
from generate_series(timestamp '2025-01-01', timestamp '2026-12-31', interval 1 day) as t(d)
{% endif %}
