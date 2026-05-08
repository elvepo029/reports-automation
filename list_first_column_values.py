import argparse
import csv
import json
import sqlite3
from pathlib import Path

NAME_REPLACEMENTS = {
    "Eloi": "ELOI VERGE",
    "Oscar": "OSCAR CUESTA",
    "Xavi": "XAVIER MATEU",
    "Héctor": "HECTOR GUILLEN",
    "Oriol": "ORIOL GARCIA",
    "Marc": "MARC VENTURA",
    "Mario": "MARIO ENJUANES",
    "Pablo": "PABLO CAMPOY",
    "Nerea": "NEREA FRAILE",
    "Lucas": "ORIOL GARCIA",
}


def normalize_name(value: str) -> str:
    return " ".join((value or "").strip().upper().split())


def read_csv_game_lgm_assignments(csv_path: Path) -> dict:
    last_error = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with csv_path.open("r", encoding=encoding, newline="") as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)
                except StopIteration:
                    return {"column_name": "", "values": []}

                if not header:
                    return {"column_name": "", "values": []}

                first_col_name = header[0]
                try:
                    game_code_idx = header.index("GAMECODE")
                except ValueError as exc:
                    raise ValueError("CSV must contain a 'GAMECODE' column.") from exc

                assignments = {}
                seen_game_codes = set()
                duplicated_game_codes = set()
                values_by_game_code = {}

                for row in reader:
                    if not row:
                        continue
                    if len(row) <= game_code_idx:
                        continue
                    csv_lgm = row[0].strip()
                    game_code = row[game_code_idx].strip()
                    if not csv_lgm or not game_code:
                        continue
                    csv_lgm = NAME_REPLACEMENTS.get(csv_lgm, csv_lgm)
                    if game_code in seen_game_codes:
                        duplicated_game_codes.add(game_code)
                    seen_game_codes.add(game_code)
                    values_by_game_code.setdefault(game_code, [])
                    values_by_game_code[game_code].append(csv_lgm)
                    assignments[game_code] = csv_lgm

                duplicated_items = []
                for game_code in sorted(duplicated_game_codes):
                    unique_lgms = []
                    for name in values_by_game_code.get(game_code, []):
                        if name not in unique_lgms:
                            unique_lgms.append(name)
                    duplicated_items.append({
                        "game_code": game_code,
                        "csv_live_game_managers": unique_lgms,
                    })

                duplicated_counts_by_lgm = {}
                for item in duplicated_items:
                    for lgm_name in item["csv_live_game_managers"]:
                        duplicated_counts_by_lgm[lgm_name] = duplicated_counts_by_lgm.get(lgm_name, 0) + 1
                duplicated_counts_items = [
                    {"csv_live_game_manager": name, "duplicated_games_count": count}
                    for name, count in sorted(duplicated_counts_by_lgm.items(), key=lambda x: x[0])
                ]

            return {
                "column_name": first_col_name,
                "assignments": assignments,
                "duplicated_game_codes": sorted(duplicated_game_codes),
                "duplicated_items": duplicated_items,
                "duplicated_counts_by_lgm": duplicated_counts_items,
            }
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    raise ValueError(f"Could not decode CSV file: {csv_path}") from last_error


def read_db_game_lgm_assignments(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT game_code, live_game_manager
        FROM Game
        WHERE game_code IS NOT NULL
          AND game_code != ''
        """
    )
    rows = cur.fetchall()
    conn.close()
    return {str(game_code).strip(): (live_game_manager or "").strip() for game_code, live_game_manager in rows}


def find_mismatches(csv_assignments: dict, db_assignments: dict) -> list:
    mismatches = []
    for game_code, csv_lgm in csv_assignments.items():
        if game_code not in db_assignments:
            continue
        db_lgm = db_assignments[game_code]
        if normalize_name(csv_lgm) != normalize_name(db_lgm):
            mismatches.append({
                "game_code": game_code,
                "csv_live_game_manager": csv_lgm,
                "db_live_game_manager": db_lgm,
            })
    return sorted(mismatches, key=lambda x: x["game_code"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare CSV nominations against Game.live_game_manager and return mismatched game_codes."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="game_nominations_25_26.csv",
        help="Path to CSV file (default: game_nominations_25_26.csv)",
    )
    parser.add_argument(
        "--db-path",
        default="dades_prod.db",
        help="Path to SQLite DB file (default: dades_prod.db)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print result as JSON.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise SystemExit(f"File not found: {csv_path}")
    db_path = Path(args.db_path)
    if not db_path.exists():
        raise SystemExit(f"File not found: {db_path}")

    csv_data = read_csv_game_lgm_assignments(csv_path)
    db_assignments = read_db_game_lgm_assignments(db_path)
    mismatches = find_mismatches(csv_data["assignments"], db_assignments)
    result = {
        "column_name": csv_data["column_name"],
        "mismatches": mismatches,
        "duplicated_game_codes": csv_data["duplicated_game_codes"],
        "duplicated_items": csv_data["duplicated_items"],
        "duplicated_counts_by_lgm": csv_data["duplicated_counts_by_lgm"],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Column: {result['column_name']}")
    print("Duplicated game_codes in CSV:")
    if result["duplicated_items"]:
        for item in result["duplicated_items"]:
            lgms = ", ".join(item["csv_live_game_managers"]) or "(empty)"
            print(f"{item['game_code']} | CSV LGM(s): {lgms}")
    else:
        print("(none)")
    print("")
    print("Duplicated games count by CSV LGM:")
    if result["duplicated_counts_by_lgm"]:
        for item in result["duplicated_counts_by_lgm"]:
            print(f"{item['csv_live_game_manager']}: {item['duplicated_games_count']}")
    else:
        print("(none)")
    print("")
    print("Mismatches:")
    for item in result["mismatches"]:
        print(
            f"{item['game_code']} | CSV: {item['csv_live_game_manager']} | DB: {item['db_live_game_manager']}"
        )


if __name__ == "__main__":
    main()
