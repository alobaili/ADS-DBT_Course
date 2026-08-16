"""
Build the public holiday reference feed served by the course mock API.

The feed covers the full span of the service request data, January 2024 to
February 2025, so it can be joined against the marts without gaps.

The holidays are civic and generic by design. This is a fictional municipality,
so the calendar is deliberately neutral rather than tied to any one country.

Run:
    python generate_holidays.py
Writes:
    public_holidays.json
"""
import json
from pathlib import Path

# One row per holiday. Kept as literal data rather than computed, so the feed is
# identical on every machine and the pipeline is reproducible.
HOLIDAYS = [
    ("2024-01-01", "New Year's Day", "national"),
    ("2024-02-19", "Founders Day", "national"),
    ("2024-04-01", "Spring Public Holiday", "national"),
    ("2024-05-06", "Labour Day", "national"),
    ("2024-05-27", "Late Spring Holiday", "national"),
    ("2024-08-26", "Summer Public Holiday", "national"),
    ("2024-09-23", "National Day", "national"),
    ("2024-10-14", "Civic Holiday", "regional"),
    ("2024-11-11", "Remembrance Day", "regional"),
    ("2024-12-25", "Winter Public Holiday", "national"),
    ("2024-12-26", "Winter Public Holiday (second day)", "national"),
    ("2025-01-01", "New Year's Day", "national"),
    ("2025-02-17", "Founders Day", "national"),
]


def main():
    feed = {
        "feed": "public_holidays",
        "version": "1.0.0",
        "coverage": {"from": "2024-01-01", "to": "2025-02-28"},
        "count": len(HOLIDAYS),
        "holidays": [
            {"date": d, "name": n, "scope": s} for d, n, s in HOLIDAYS
        ],
    }
    out = Path(__file__).resolve().parent / "public_holidays.json"
    out.write_text(json.dumps(feed, indent=2), encoding="utf-8")
    print("wrote %s with %d holidays" % (out, len(HOLIDAYS)))


if __name__ == "__main__":
    main()
