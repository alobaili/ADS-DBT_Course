{#
    Bands a request against its own service target, so a 30-hour permit and a
    30-hour water fault are judged on their own terms rather than a flat threshold.
#}
{% macro resolution_band(hours_column, target_column) %}
    case
        when {{ hours_column }} is null then null
        when {{ hours_column }} <= 0.5 * {{ target_column }} then 'Fast'
        when {{ hours_column }} <= {{ target_column }}       then 'On-time'
        else 'Slow'
    end
{% endmacro %}
