"""
Simulate a real-world event: the directorate revises two SLA targets.

Run this BETWEEN two `dbt snapshot` calls to watch a Type 2 slowly changing
dimension do its job.

    dbt snapshot                  # first capture: 10 rows, none closed
    python simulate_sla_revision.py
    dbt seed --select services    # reload the revised catalogue
    dbt snapshot                  # second capture: history preserved

Run with --revert to put the original targets back.
"""
import sys
from pathlib import Path
import pandas as pd

SEED = Path(__file__).resolve().parent / "dbt_project" / "seeds" / "services.csv"

# Water Supply Fault tightened 24h -> 12h; Road Maintenance relaxed 72h -> 96h
REVISIONS = {10: (24, 12), 13: (72, 96)}

revert = "--revert" in sys.argv
df = pd.read_csv(SEED)

for service_id, (original, revised) in REVISIONS.items():
    old, new = (revised, original) if revert else (original, revised)
    mask = df["service_id"] == service_id
    name = df.loc[mask, "service_name"].iloc[0]
    df.loc[mask, "target_resolution_hours"] = new
    print(f"  {name:24s} target {old}h -> {new}h")

df.to_csv(SEED, index=False)
print(f"\n{'Reverted' if revert else 'Revised'} {SEED}")
print("Next: dbt seed --select services  &&  dbt snapshot")
