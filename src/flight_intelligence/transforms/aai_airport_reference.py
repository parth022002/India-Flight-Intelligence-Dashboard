"""Build a structured reference from the historical AAI airport-list PDF.

Uses layout-preserving text extracted from the two-page source PDF.
Does not modify the core airport master, facilities inventory, or database.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = PROJECT_ROOT / "data" / "reference" / "aai_airports"
DEFAULT_OUTPUT = SOURCE_DIR / "aai_airport_reference.csv"

SOURCE_DOCUMENT = "list_of_airports_aai_2020.pdf"
SOURCE_DATE = "2020-06-23"

COLUMNS = [
    "airport_name",
    "category",
    "reported_status",
    "owner",
    "source_classification",
    "source_document",
    "source_date",
    "source_page",
    "source_line",
    "source_column",
]

OWNER_PATTERN = (
    r"AAI|BIAL|CIAL|GHIAL|KIAL|MADC|BAPL|HAL|STATE|MIAPL|RADPL|JSW"
)

ROW_PATTERN = re.compile(
    rf"(?P<name>[A-Z][A-Z0-9 .()&/'-]*?)\s+"
    rf"(?P<status>OPS|NON-OPS)\s+"
    rf"(?P<owner>{OWNER_PATTERN})\s+"
    r"(?P<classification>INTL\(CE\)|CUS\(CE\)|DOM\(CE\)|INTL|CUS|DOM)(?![A-Z])",
    re.IGNORECASE,
)

EXPECTED_COUNTS = {
    "INTL": 26,
    "INTL(CE)": 3,
    "CUS": 10,
    "DOM": 91,
    "DOM(CE)": 23,
}


def category_for(classification: str, section: str) -> str:
    """Preserve the section and civil-enclave distinction from the source."""
    if classification == "DOM(CE)":
        return "domestic_civil_enclave"
    if classification == "INTL(CE)":
        return "international_civil_enclave"
    if classification == "CUS(CE)":
        return "customs_civil_enclave"

    return {
        "international": "international",
        "customs": "customs",
        "domestic": "domestic",
        "domestic_civil_enclave": "domestic_civil_enclave",
    }.get(section, "unresolved")


def parse_layout_files(source_dir: Path) -> list[dict[str, str]]:
    """Parse the two layout-preserving text files, one column at a time."""
    records: list[dict[str, str]] = []
    section_by_page = {
        1: "international",
        2: "domestic",
    }

    for page_num in (1, 2):
        path = source_dir / f"page_{page_num}_layout.txt"
        if not path.exists():
            raise FileNotFoundError(f"Required layout text is missing: {path}")

        lines = path.read_text(encoding="utf-8").splitlines()
        section = section_by_page[page_num]

        for line_num, line in enumerate(lines, start=1):
            upper = line.upper()

            if "DOMESTIC CIVIL ENCLAVES" in upper:
                section = "domestic_civil_enclave"
            elif "INTERNATIONAL AIRPORTS" in upper and "TOTAL" not in upper:
                section = "international"
            elif "CUSTOMS AIRPORTS" in upper and "TOTAL" not in upper:
                section = "customs"
            elif "DOMESTIC AIRPORTS" in upper and "TOTAL" not in upper:
                section = "domestic"

            for column_num, column_text in enumerate(
                (line[:90], line[90:]), start=1
            ):
                match = ROW_PATTERN.search(column_text)
                if not match:
                    continue

                values = {
                    key: value.strip()
                    for key, value in match.groupdict().items()
                }
                classification = values["classification"].upper()
                name = " ".join(values["name"].split())

                records.append(
                    {
                        "airport_name": name,
                        "category": category_for(classification, section),
                        "reported_status": values["status"].upper(),
                        "owner": values["owner"].upper(),
                        "source_classification": classification,
                        "source_document": SOURCE_DOCUMENT,
                        "source_date": SOURCE_DATE,
                        "source_page": str(page_num),
                        "source_line": str(line_num),
                        "source_column": str(column_num),
                    }
                )

    return records


def validate_records(records: list[dict[str, str]]) -> list[str]:
    """Return validation errors; never silently write a partial extraction."""
    errors: list[str] = []

    if len(records) != 153:
        errors.append(f"Expected 153 records, found {len(records)}.")

    names = [record["airport_name"].casefold() for record in records]
    duplicates = sorted(
        name for name, count in Counter(names).items() if count > 1
    )
    if duplicates:
        errors.append(f"Repeated airport names found: {duplicates}")

    actual_counts = Counter(
        record["source_classification"] for record in records
    )
    for classification, expected in EXPECTED_COUNTS.items():
        actual = actual_counts[classification]
        if actual != expected:
            errors.append(
                f"{classification}: expected {expected}, found {actual}."
            )

    allowed_statuses = {"OPS", "NON-OPS"}
    allowed_owners = {
        "AAI", "BIAL", "CIAL", "GHIAL", "KIAL", "MADC",
        "BAPL", "HAL", "STATE", "MIAPL", "RADPL", "JSW",
    }
    allowed_classifications = {
        "INTL", "INTL(CE)", "CUS", "CUS(CE)", "DOM", "DOM(CE)"
    }

    for index, record in enumerate(records, start=1):
        if not record["airport_name"]:
            errors.append(f"Record {index} has an empty airport name.")
        if record["reported_status"] not in allowed_statuses:
            errors.append(f"Record {index} has invalid status.")
        if record["owner"] not in allowed_owners:
            errors.append(f"Record {index} has invalid owner.")
        if record["source_classification"] not in allowed_classifications:
            errors.append(f"Record {index} has invalid classification.")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the historical AAI airport reference CSV."
    )
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        records = parse_layout_files(args.source_dir)
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}")
        print("No CSV was written.")
        return 2

    errors = validate_records(records)
    if errors:
        print("ERROR: validation failed; no CSV was written.")
        for error in errors:
            print(f"- {error}")
        return 3

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    print(f"Validated records: {len(records)}")
    print("Classification counts:")
    for classification, count in sorted(
        Counter(r["source_classification"] for r in records).items()
    ):
        print(f"  {classification}: {count}")
    print(f"Output: {args.output}")
    print("Source: historical AAI airport list; verify before current-status use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
