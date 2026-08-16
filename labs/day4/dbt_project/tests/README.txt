LAB 3, STEPS 2 AND 3.  Write your singular tests in this folder.

A singular test is any SELECT that returns the rows which should not exist.
If it returns nothing, the test passes. That is the whole mechanism.

You need four:
  assert_no_zero_hour_resolutions.sql   resolution_hours must be above zero
  assert_sla_met_agrees_with_target.sql sla_met must be reproducible from its inputs
  assert_backlog_spine_is_dense.sql     every department in every month
  assert_resolution_after_submission.sql  resolved_at must not precede submitted_at

Run the last one at DEFAULT severity first. It will return 20 rows and break
your build. Read them, understand why they cannot be repaired, and only then
downgrade it to a warning WITH a written justification in the file.
