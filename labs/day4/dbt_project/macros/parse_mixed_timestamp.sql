{#
    The raw feed carries submitted_at in two presentations, because two upstream
    systems write the same event with different conventions:
        ISO            2025-01-16 05:25:00
        day-month-name 16-Jan-2025 05:25
    Parsing each explicitly and coalescing is safer than one blind cast: anything
    matching neither pattern lands as NULL and is caught by a test, rather than
    silently becoming a wrong date.
#}
{% macro parse_mixed_timestamp(column_name) %}
    case
        when {{ column_name }} ~ '^\d{4}-\d{2}-\d{2}'
            then to_timestamp({{ column_name }}, 'YYYY-MM-DD HH24:MI:SS')::timestamp
        when {{ column_name }} ~ '^\d{2}-[A-Za-z]{3}-\d{4}'
            then to_timestamp({{ column_name }}, 'DD-Mon-YYYY HH24:MI')::timestamp
    end
{% endmacro %}
