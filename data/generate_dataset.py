"""
Generate the teaching dataset for the Applied Data Science & ML with Python and dbt course.

Domain: e-government citizen service requests (a "Unified Services Portal").
One fact table (service_requests) plus dimensions (services, channels,
districts, departments). The raw fact table is deliberately seeded with
realistic data-quality problems for the Day 1 cleaning work, and carries a
clean classification target (SLA met) and a regression target
(resolution_hours) used from Day 3 onward.

Reproducible: fixed seed. UK English throughout.
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(2026)
N = 12000  # number of service requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SEEDS = HERE / "seeds"
RAW.mkdir(parents=True, exist_ok=True)
SEEDS.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Dimensions (clean; these become dbt seeds later in the week)
# ---------------------------------------------------------------------------
services = pd.DataFrame({
    "service_id": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    "service_name": [
        "Water Supply Fault", "Street Lighting Fault", "Waste Collection",
        "Road Maintenance", "Building Permit", "Business Licence Renewal",
        "Property Tax Enquiry", "Public Transport Card", "Noise Complaint",
        "Parks and Recreation",
    ],
    "category": [
        "Utilities", "Utilities", "Utilities", "Infrastructure",
        "Permits", "Permits", "Finance", "Transport", "Environment", "Environment",
    ],
    # Target resolution time in hours, per service (the SLA)
    "target_resolution_hours": [24, 48, 24, 72, 240, 120, 48, 24, 72, 96],
})

channels = pd.DataFrame({
    "channel_id": [1, 2, 3, 4, 5],
    "channel_name": ["Web Portal", "Mobile App", "Call Centre", "Walk-in Centre", "WhatsApp"],
    "is_digital": [True, True, False, False, True],
})

districts = pd.DataFrame({
    "district_id": [100, 101, 102, 103, 104, 105],
    "district_name": ["Al Olaya", "Al Malaz", "Al Naseem", "Irqah", "Al Aziziyah", "Diriyah"],
    "region": ["Central", "Central", "East", "West", "South", "North West"],
    "population": [210000, 185000, 240000, 96000, 158000, 74000],
})

departments = pd.DataFrame({
    "department_id": [1, 2, 3, 4, 5],
    "department_name": [
        "Utilities Directorate", "Infrastructure Directorate",
        "Licensing and Permits", "Revenue and Finance", "Environment and Parks",
    ],
})

# Map each service to the department that owns it
service_to_dept = {10: 1, 11: 1, 12: 1, 13: 2, 14: 3, 15: 3, 16: 4, 17: 2, 18: 5, 19: 5}


# ---------------------------------------------------------------------------
# Fact table (clean core, then we inject dirt)
# ---------------------------------------------------------------------------
service_ids = RNG.choice(services["service_id"], size=N,
                         p=np.array([0.16, 0.12, 0.15, 0.10, 0.06, 0.07, 0.09, 0.08, 0.09, 0.08]))
channel_ids = RNG.choice(channels["channel_id"], size=N, p=[0.34, 0.28, 0.16, 0.07, 0.15])
district_ids = RNG.choice(districts["district_id"], size=N)
priority = RNG.choice(["Low", "Medium", "High"], size=N, p=[0.45, 0.40, 0.15])

# Submitted timestamps across ~14 months
start = pd.Timestamp("2024-01-01")
minutes = RNG.integers(0, 60 * 24 * 425, size=N)
submitted_at = start + pd.to_timedelta(minutes, unit="m")

# Resolution time depends on service target, priority, channel and some noise
target_lookup = services.set_index("service_id")["target_resolution_hours"].to_dict()
base = np.array([target_lookup[s] for s in service_ids], dtype=float)
prio_factor = np.where(priority == "High", 0.6, np.where(priority == "Medium", 0.95, 1.25))
digital_lookup = channels.set_index("channel_id")["is_digital"].to_dict()
digital = np.array([digital_lookup[c] for c in channel_ids])
digital_factor = np.where(digital, 0.85, 1.2)
noise = RNG.lognormal(mean=0.0, sigma=0.45, size=N)
resolution_hours = base * prio_factor * digital_factor * noise
resolution_hours = np.round(resolution_hours, 1)

# Status: most resolved, some still open, a few reopened
status = RNG.choice(["Resolved", "Open", "Reopened"], size=N, p=[0.82, 0.13, 0.05])
resolved_at = submitted_at + pd.to_timedelta(resolution_hours, unit="h")
resolved_at = resolved_at.where(status != "Open")  # open requests have no resolved_at

# Satisfaction score 1-5, only for resolved/reopened, and often missing (non-response)
satisfaction = RNG.integers(1, 6, size=N).astype(float)
satisfaction[status == "Open"] = np.nan
missing_sat = RNG.random(N) < 0.35
satisfaction[missing_sat] = np.nan

citizen_age_band = RNG.choice(
    ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"], size=N,
    p=[0.14, 0.28, 0.24, 0.16, 0.11, 0.07])

df = pd.DataFrame({
    "request_id": np.arange(1_000_000, 1_000_000 + N),
    "submitted_at": submitted_at,
    "service_id": service_ids,
    "channel_id": channel_ids,
    "district_id": district_ids,
    "department_id": [service_to_dept[s] for s in service_ids],
    "priority": priority,
    "status": status,
    "resolved_at": resolved_at,
    "resolution_hours": resolution_hours,
    "satisfaction_score": satisfaction,
    "citizen_age_band": citizen_age_band,
})

# Clean modelling targets (kept correct for teaching ML later in the week)
df["sla_met"] = ((df["resolution_hours"] <= base) & (df["status"] != "Open")).astype("Int64")
df.loc[df["status"] == "Open", "sla_met"] = pd.NA


# ---------------------------------------------------------------------------
# Inject realistic dirt into a RAW copy (this is what Day 1 cleans)
# ---------------------------------------------------------------------------
raw = df.copy()

# 1) Inconsistent categorical text on priority (case + whitespace)
mask = RNG.random(N) < 0.12
raw.loc[mask, "priority"] = raw.loc[mask, "priority"].str.upper()
mask = RNG.random(N) < 0.08
raw.loc[mask, "priority"] = " " + raw.loc[mask, "priority"] + " "

# 2) Missing citizen_age_band as empty strings and literal "Unknown"
mask = RNG.random(N) < 0.06
raw.loc[mask, "citizen_age_band"] = ""
mask = RNG.random(N) < 0.03
raw.loc[mask, "citizen_age_band"] = "Unknown"

# 3) Outliers / data-entry errors in resolution_hours
err_idx = RNG.choice(N, size=45, replace=False)
raw.loc[err_idx, "resolution_hours"] = RNG.choice([9999.0, 99999.0, -5.0, 0.0], size=45)

# 4) A handful of resolved_at earlier than submitted_at (impossible, teaches validation)
bad_idx = RNG.choice(raw.index[raw["status"] == "Resolved"], size=20, replace=False)
raw.loc[bad_idx, "resolved_at"] = raw.loc[bad_idx, "submitted_at"] - pd.to_timedelta(3, unit="h")

# 5) Duplicate rows (full duplicates, as if double-submitted)
dupes = raw.sample(60, random_state=7)
raw = pd.concat([raw, dupes], ignore_index=True)

# 6) priority stored with an occasional numeric-looking string to break naive typing
mask = RNG.random(len(raw)) < 0.01
raw.loc[mask, "priority"] = "2"

# 7) Mixed date presentation: write submitted_at in two formats. The second is
#    day-month-name-year (e.g. 08-Jul-2024), which is unambiguous, so the fault
#    is genuinely "mixed formats" without an accidental day/month trap.
raw["submitted_at"] = raw["submitted_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
half = RNG.random(len(raw)) < 0.30
raw.loc[half, "submitted_at"] = pd.to_datetime(
    raw.loc[half, "submitted_at"]).dt.strftime("%d-%b-%Y %H:%M")
raw["resolved_at"] = pd.to_datetime(raw["resolved_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

# Shuffle so duplicates are not adjacent
raw = raw.sample(frac=1, random_state=11).reset_index(drop=True)

# Drop the leaked clean target from the RAW file (learners derive it themselves)
raw = raw.drop(columns=["sla_met"])


# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------
raw.to_csv(RAW / "service_requests_raw.csv", index=False)
df.to_csv(RAW / "service_requests_clean_reference.csv", index=False)  # instructor reference

services.to_csv(SEEDS / "services.csv", index=False)
channels.to_csv(SEEDS / "channels.csv", index=False)
districts.to_csv(SEEDS / "districts.csv", index=False)
departments.to_csv(SEEDS / "departments.csv", index=False)

print(f"Raw fact rows (with {len(raw) - N} injected duplicates): {len(raw):,}")
print(f"Clean reference rows: {len(df):,}")
print("Dimensions:", {k: len(v) for k, v in {
    "services": services, "channels": channels,
    "districts": districts, "departments": departments}.items()})
print("Wrote to:", RAW, "and", SEEDS)
