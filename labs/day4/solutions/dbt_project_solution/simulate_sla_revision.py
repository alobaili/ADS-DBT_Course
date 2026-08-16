r"""
Simulate a real-world event: the directorate revises two SLA targets.

Run this BETWEEN two `dbt snapshot` calls to watch a Type 2 slowly changing
dimension do its job.

    dbt snapshot                      # first capture
    python ..\..\simulate_sla_revision.py
    dbt seed --select services        # reload the revised catalogue
    dbt snapshot                      # second capture

Run with --revert to put the original targets back.

The script edits the services.csv of the dbt project you run it against. It
finds that project by looking, in order:
  1. a --project PATH you pass explicitly
  2. a dbt project in the current working directory (its seeds/services.csv)
  3. the sibling dbt_project / dbt_project_solution folders next to this script
This means it works whether you run the demo from the solution project or the
delegate project, without editing the wrong file.
"""
import sys
from pathlib import Path
import pandas as pd

# Water Supply Fault tightened 24h -> 12h; Road Maintenance relaxed 72h -> 96h
REVISIONS = {10: (24, 12), 13: (72, 96)}
revert = "--revert" in sys.argv


def find_seed():
    # 1. explicit --project PATH
    if "--project" in sys.argv:
        base = Path(sys.argv[sys.argv.index("--project") + 1]).resolve()
        cand = base / "seeds" / "services.csv"
        if cand.exists():
            return cand

    # 2. a project rooted at the current working directory
    cwd_seed = Path.cwd() / "seeds" / "services.csv"
    if (Path.cwd() / "dbt_project.yml").exists() and cwd_seed.exists():
        return cwd_seed

    # 3. sibling project folders next to this script
    here = Path(__file__).resolve().parent
    for rel in ["solutions/dbt_project_solution", "dbt_project"]:
        cand = here / rel / "seeds" / "services.csv"
        if cand.exists():
            return cand

    raise FileNotFoundError(
        "Could not find a services.csv to edit. Run this from inside a dbt "
        "project folder, or pass --project PATH_TO_PROJECT."
    )


SEED = find_seed()
df = pd.read_csv(SEED)

for service_id, (original, revised) in REVISIONS.items():
    old, new = (revised, original) if revert else (original, revised)
    mask = df["service_id"] == service_id
    name = df.loc[mask, "service_name"].iloc[0]
    df.loc[mask, "target_resolution_hours"] = new
    print(f"  {name:24s} target {old}h -> {new}h")

df.to_csv(SEED, index=False)
print(f"\n{'Reverted' if revert else 'Revised'} {SEED}")
print("Next: dbt seed --select services  then  dbt snapshot")
