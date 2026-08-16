{% snapshot scd_services %}
{{
    config(
      target_schema='snapshots',
      unique_key='service_id',
      strategy='check',
      check_cols=['service_name', 'category', 'target_resolution_hours'],
      invalidate_hard_deletes=True
    )
}}

/*
    A Type 2 slowly changing dimension over the service catalogue.

    Why this one matters more than most SCD examples: target_resolution_hours IS
    the SLA. Every sla_met value in the warehouse is computed against it. Revise a
    target and, without this snapshot, you have not merely lost history, you have
    silently rewritten two years of reported performance. Last quarter's board
    pack stops reproducing and nobody can say why.

    Strategy is 'check' rather than 'timestamp' because the seed carries no
    updated_at column, which is the common real-world case for reference data
    maintained by hand.
*/

select * from {{ ref('stg_services') }}

{% endsnapshot %}
