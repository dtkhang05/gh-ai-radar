{#- Own version of dbt_utils.unique_combination_of_columns: avoids a package install (slow network) for one small test. -#}
{% test unique_combination(model, cols) %}
select {{ cols | join(', ') }}, count(*) as n
from {{ model }}
group by {{ cols | join(', ') }}
having count(*) > 1
{% endtest %}
