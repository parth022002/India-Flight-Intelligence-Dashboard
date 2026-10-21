"""Command-line entry point for the India airport-master builder."""
import argparse
from pathlib import Path
from flight_intelligence.transforms.airport_master import build_master
DEFAULT_SOURCE = Path("data/reference/ourairports_airports.csv")
DEFAULT_OUTPUT = Path("data/processed/india_airport_master.csv")
DEFAULT_REPORT = Path("reports/airport_master_build_report.json")
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = build_master(args.source, args.output, args.report)
    print("Airport master build completed.")
    print(f"Source India records: {report['source_rows_india']}")
    print(f"Candidates: {report['candidate_count']}")
    print(f"Rejected candidates: {report['rejected_candidate_count']}")
    print(f"Accepted master records: {report['accepted_master_count']}")
    print(f"Master CSV: {args.output}")
    print(f"Build report: {args.report}")
if __name__ == "__main__":
    main()
