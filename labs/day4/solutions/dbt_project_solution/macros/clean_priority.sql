{#
    priority arrives in 13 spellings: case variants, wrapping whitespace, and a
    stray '2' from a mis-keyed entry. Day 1 collapsed these in Pandas; this is the
    same decision expressed once, in version control, applied everywhere.
#}
{% macro clean_priority(column_name) %}
    case
        when trim({{ column_name }}) = '2' then 'Medium'
        else initcap(trim({{ column_name }}))
    end
{% endmacro %}
