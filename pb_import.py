# /// script
# dependencies = ["requests"]
# ///
"""
PocketBase auto-importer — reads any SQLite file, creates collections, imports all data.

Usage:
  uv run pb_import.py --db nba.sqlite --url https://db.el-stats.net --email x@x.com --password secret
  uv run pb_import.py --db nba.sqlite --url https://db.el-stats.net --email x@x.com --password secret --skip play_by_play,inactive_players
  uv run pb_import.py --db nba.sqlite --url https://db.el-stats.net --email x@x.com --password secret --only team,player,game
"""

import sqlite3
import requests
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- Type detection ----------

def sqlite_to_pb_type(col_name: str, declared_type: str) -> str:
    dt = (declared_type or "").upper()
    cn = col_name.lower()

    if "INT" in dt:
        return "number"
    if any(x in dt for x in ["REAL", "FLOAT", "DOUBLE", "NUMERIC", "DECIMAL"]):
        return "number"
    if "BOOL" in dt:
        return "bool"
    if any(x in dt for x in ["DATETIME", "TIMESTAMP"]):
        return "text"   # keep as text — PB date format is strict (RFC3339)
    if "DATE" in dt:
        return "text"
    return "text"       # safe default for everything else

def get_fields(con, table):
    cols = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    # (cid, name, type, notnull, dflt_value, pk)
    fields = []
    for col in cols:
        name, dtype = col[1], col[2]
        if name == "id":
            continue    # PocketBase manages its own id
        fields.append({
            "name": name,
            "type": sqlite_to_pb_type(name, dtype),
            "required": False,
        })
    return fields

# ---------- PocketBase helpers ----------

def authenticate(url, email, password):
    # PocketBase v0.23+ renamed admins → _superusers
    r = requests.post(f"{url}/api/collections/_superusers/auth-with-password",
                      json={"identity": email, "password": password}, timeout=10)
    if not r.ok:
        print(f"Auth failed: {r.status_code} {r.text}")
        sys.exit(1)
    return r.json()["token"]

def create_collection(url, token, name, fields):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{url}/api/collections",
                      json={"name": name, "type": "base", "fields": fields},
                      headers=headers, timeout=15)
    if r.ok:
        print(f"  [+] Collection created")
        return True
    if r.status_code in (400, 409) and ("exists" in r.text.lower() or "unique" in r.text.lower()):
        print(f"  [=] Collection already exists — will append data")
        return True
    print(f"  [!] Could not create collection: {r.status_code} {r.text[:200]}")
    return False

def post_record(url, token, collection, payload):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{url}/api/collections/{collection}/records",
                      json=payload, headers=headers, timeout=15)
    return r.ok, r.status_code, r.text[:120] if not r.ok else ""

# ---------- Main import ----------

def import_table(url, token, con, table, workers=4):
    con2 = sqlite3.connect(con)   # own connection per thread context
    c2 = con2.cursor()
    c2.row_factory = sqlite3.Row

    rows = c2.execute(f'SELECT * FROM "{table}"').fetchall()
    total = len(rows)
    if total == 0:
        print(f"  (empty — skipped)")
        con2.close()
        return

    print(f"  Importing {total:,} rows with {workers} workers...")

    ok = fail = 0
    start = time.time()

    def send(row):
        payload = dict(row)
        payload.pop("id", None)
        # sanitize None → keep as null (requests handles it)
        return post_record(url, token, table, payload)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(send, row): i for i, row in enumerate(rows)}
        for f in as_completed(futures):
            success, code, err = f.result()
            if success:
                ok += 1
            else:
                fail += 1
                if fail <= 3:
                    print(f"  [!] FAIL {code}: {err}", file=sys.stderr)
            done = ok + fail
            if done % 500 == 0 or done == total:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed else 0
                eta = (total - done) / rate if rate else 0
                print(f"  {done:,}/{total:,}  ok={ok:,}  fail={fail}  {rate:.0f} rec/s  ETA {eta:.0f}s")

    con2.close()
    elapsed = time.time() - start
    print(f"  Done in {elapsed:.1f}s — {ok:,} imported, {fail} failed")

# ---------- Entry point ----------

def main():
    p = argparse.ArgumentParser(description="Import SQLite → PocketBase")
    p.add_argument("--db",       required=True,  help="Path to SQLite file")
    p.add_argument("--url",      required=True,  help="PocketBase URL (no trailing slash)")
    p.add_argument("--email",    required=True,  help="Admin email")
    p.add_argument("--password", required=True,  help="Admin password")
    p.add_argument("--skip",     default="",     help="Comma-separated tables to skip")
    p.add_argument("--only",     default="",     help="Comma-separated tables to import (all if omitted)")
    p.add_argument("--workers",  type=int, default=4, help="Parallel upload threads (default 4)")
    args = p.parse_args()

    skip = {t.strip() for t in args.skip.split(",") if t.strip()}
    only = {t.strip() for t in args.only.split(",") if t.strip()}

    print(f"\nConnecting to {args.url} ...")
    token = authenticate(args.url, args.email, args.password)
    print("Authenticated OK\n")

    con = sqlite3.connect(args.db)
    tables = [t[0] for t in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]

    if only:
        tables = [t for t in tables if t in only]
    tables = [t for t in tables if t not in skip]

    print(f"Tables to import ({len(tables)}): {', '.join(tables)}\n")

    for table in tables:
        row_count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f"\n── {table} ({row_count:,} rows) ──")

        fields = get_fields(con, table)
        if not create_collection(args.url, token, table, fields):
            continue

        import_table(args.url, token, args.db, table, workers=args.workers)

    con.close()
    print("\n\nAll done.")

if __name__ == "__main__":
    main()
