
"""Command-line entry point for the India aviation-facilities builder."""
import argparse
from pathlib import Path

from flight_intelligence.transforms.aviation_facilities import build_facilities

DEFAULT_SOURCE = Path("data/reference/ourairports_airports.csv")
DEFAULT_OUTPUT = Path("data/processed/india_aviation_facilities.csv")
DEFAULT_REPORT = Path("reports/generated/aviation_facilities_build_report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    report = build_facilities(args.source, args.output, args.report)
    print("Aviation facilities build completed.")
    print(f"India source records: {report['source_rows_india']}")
    print(f"Candidates: {report['candidate_count']}")
    print(f"Rejected candidates: {report['rejected_candidate_count']}")
    print(f"Accepted facilities: {report['accepted_facility_count']}")
    print(f"Facilities CSV: {args.output}")
    print(f"Build report: {args.report}")


if __name__ == "__main__":
    main()
