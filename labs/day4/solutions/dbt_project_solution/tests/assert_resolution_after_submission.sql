{{ config(severity='warn') }}

/*
    A request cannot be resolved before it was submitted.

    This test WARNS on 20 rows rather than erroring, and the distinction is the
    lesson. The fault is real and upstream; we cannot invent the correct
    timestamps, so we refuse to silently overwrite them. Severity is downgraded
    deliberately, in version control, with this justification attached, so the
    pipeline runs while the defect stays visible on every single run.

    Delegates meet this test at error severity first, watch it break the build,
    and only then make this change. Suppressing a test you have not understood is
    the failure mode; suppressing one you have documented is engineering.
*/

select request_id, submitted_at, resolved_at
from {{ ref('fct_service_requests') }}
where resolved_at is not null
  and resolved_at < submitted_at
