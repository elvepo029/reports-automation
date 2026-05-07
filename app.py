from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import json
from io import BytesIO
from pdfGeneratorHelper import html_to_pdf, generate_pdf_from_json
from correctionToReport import runCorrectionsProcessor
from openpyxl import Workbook
import os
import base64
import sys

from migrations import ensure_correction_drop_live_game_manager

if sys.platform == "win32":
    os.add_dll_directory(r"C:\msys64\ucrt64\bin")

app = Flask(__name__)


def get_app_version() -> str:
    path = os.path.join(app.root_path, "VERSION")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "unknown"


@app.context_processor
def inject_app_version():
    return {"app_version": get_app_version()}


DB = "dades_staging.db" #PROVES
#DB = "dades_prod.db" #PRODUCCIó


def get_db():
    conn = sqlite3.connect(DB)
    ensure_correction_drop_live_game_manager(conn)
    return conn


def get_logo_data_uri():
    """PNG incrustat en base64 perquè WeasyPrint mostri el logo (evita alt text si falla el fitxer)."""
    logo_path = os.path.join(app.root_path, "static", "logo.png")
    try:
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


def ensure_game_logistics_columns(conn):
    """
    Garanteix que la taula Game tingui les columnes de logística necessàries.
    Afegim les columnes només si no existeixen (per compatibilitat amb BDs antigues).
    """
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(Game)")
    existing_cols = {row[1] for row in cur.fetchall()}

    needed_columns = [
        ("arrival_time", "TEXT"),
        ("checklist_on_time", "TEXT"),
        ("communication", "TEXT"),
        ("corrections_speed", "TEXT"),
        ("rescouted", "TEXT"),
        # Camps addicionals per guardar informació del report
        ("total_actions", "INTEGER"),
        ("total_corrections", "INTEGER"),
        ("lgm_comment", "TEXT"),
        ("result", "REAL"),
        ("live_game_manager", "TEXT"),
    ]

    for col_name, col_type in needed_columns:
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE Game ADD COLUMN {col_name} {col_type}")

    conn.commit()

@app.route("/")
def index():
    return render_template("home.html")


@app.route("/report-generator")
def report_generator():
    return render_template("report_generator.html")


@app.route("/corrections-analysis")
def corrections_analysis():
    return render_template("corrections_analysis.html")


@app.route("/uscs-analysis")
def uscs_analysis():
    return render_template("uscs_analysis.html")


FILTERABLE_CORRECTION_COLUMNS = (
    "game_code", "time", "quarter", "points_h", "points_a", "action_num",
    "b_ss", "team", "type_c", "category",
)

# live_game_manager és camp de Game; no incloem C.live_game_manager per evitar duplicar el nom.
CORRECTION_ROW_SELECT = (
    "C.rowid, C.game_code, C.time, C.quarter, C.points_h, C.points_a, C.action_num, "
    "C.b_ss, C.team, C.type_c, C.category, C.thread_name, C.correction, "
    "G.live_game_manager AS live_game_manager"
)


@app.route("/api/corrections")
def api_corrections_paginated():
    """Paginated list of Correction records, most recent first. Supports filters via query params."""
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 50, type=int)))

    # filters on Correction table
    filters = {}
    for col in FILTERABLE_CORRECTION_COLUMNS:
        val = request.args.get(col, "").strip()
        if val:
            filters[col] = val

    # filters on Game table
    game_filters = {}
    game_filter_names = [
        "home_team",
        "away_team",
        "data_entry",
        "caller_1",
        "caller_2",
        "timer",
        "shot_clock_operator",
        "irs_operator",
        "arrival_time",
        "checklist_on_time",
        "communication",
        "corrections_speed",
        "rescouted",
        "live_game_manager",
    ]
    for key in game_filter_names:
        val = request.args.get(key, "").strip()
        if val:
            game_filters[key] = val

    competition = request.args.get("competition", "").strip()
    season = request.args.get("season", "").strip()

    # Always join Game so we can enforce Game.is_processed = 1
    join_game = True

    where_parts = []
    params = []

    # Base constraint: only processed games
    where_parts.append("G.is_processed = 1")

    # Correction filters
    if filters:
        for col, val in filters.items():
            where_parts.append(f"C.{col} = ?")
            params.append(val)

    # Game filters
    # home/away team_code
    if "home_team" in game_filters:
        where_parts.append("G.code_h = ?")
        params.append(game_filters["home_team"])
    if "away_team" in game_filters:
        where_parts.append("G.code_a = ?")
        params.append(game_filters["away_team"])
    # USCs
    for field in ("data_entry", "caller_1", "caller_2", "timer", "shot_clock_operator", "irs_operator"):
        if field in game_filters:
            where_parts.append(f"G.{field} = ?")
            params.append(game_filters[field])
    # logistics
    for field in ("arrival_time", "checklist_on_time", "communication", "corrections_speed", "rescouted"):
        if field in game_filters:
            where_parts.append(f"G.{field} = ?")
            params.append(game_filters[field])
    # live game manager (ara és camp de Game, no de Correction)
    if "live_game_manager" in game_filters:
        where_parts.append("G.live_game_manager = ?")
        params.append(game_filters["live_game_manager"])

    # virtual filters (competition, season)
    if competition:
        # game_code starts with competition letter, e.g. 'E' or 'U'
        where_parts.append("C.game_code LIKE ?")
        params.append(f"{competition}%")

    if season:
        # season is in format '2025-2026' → use the first part '2025'
        season_year = season.split("-")[0].strip()
        if season_year:
            where_parts.append("C.game_code LIKE ?")
            params.append(f"%{season_year}%")

    where_clause = ""
    if where_parts:
        where_clause = " WHERE " + " AND ".join(where_parts)

    from_clause = " FROM Correction C"
    if join_game:
        from_clause += " JOIN Game G ON C.game_code = G.game_code"

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total" + from_clause + where_clause, params)
    total = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(DISTINCT C.game_code) AS total_games" + from_clause + where_clause, params)
    total_games = cur.fetchone()["total_games"]

    # Denominator for percent calculation:
    # - If no USC filter selected: total corrections overall
    # - If any USC filter selected: total corrections where home_team == selected home team (Game.code_h)
    usc_filter_fields = ["data_entry", "caller_1", "caller_2", "timer", "shot_clock_operator", "irs_operator"]
    usc_selected = any(field in game_filters for field in usc_filter_fields)

    denom_total = 0
    if not usc_selected:
        cur.execute("SELECT COUNT(*) AS total FROM Correction C JOIN Game G ON C.game_code = G.game_code WHERE G.is_processed = 1")
        denom_total = cur.fetchone()["total"]
    else:
        home_team_code = game_filters.get("home_team", "").strip()
        if home_team_code:
            cur.execute(
                "SELECT COUNT(*) AS total FROM Correction C JOIN Game G ON C.game_code = G.game_code WHERE G.is_processed = 1 AND G.code_h = ?",
                (home_team_code,),
            )
            denom_total = cur.fetchone()["total"]
        else:
            # fallback: if no home_team selected, use overall total
            cur.execute("SELECT COUNT(*) AS total FROM Correction C JOIN Game G ON C.game_code = G.game_code WHERE G.is_processed = 1")
            denom_total = cur.fetchone()["total"]

    percent_of_total = (float(total) / float(denom_total) * 100.0) if denom_total else 0.0
    offset = (page - 1) * per_page
    select_params = params + [per_page, offset]
    cur.execute(
        "SELECT " + CORRECTION_ROW_SELECT + from_clause + where_clause + " ORDER BY C.rowid DESC LIMIT ? OFFSET ?",
        select_params,
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    total_pages = (total + per_page - 1) // per_page if total else 0
    return jsonify({
        "items": rows,
        "total": total,
        "total_games": total_games,
        "denom_total": denom_total,
        "percent_of_total": percent_of_total,
        "percent_scope": "home_team_with_selected_uscs" if usc_selected else "all_corrections",
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    })


@app.route("/api/corrections_export.xlsx")
def api_corrections_export_excel():
    """Export filtered corrections grouped by game_code for charts (.xlsx)."""
    breakdown = request.args.get("breakdown", "type_c").strip().lower()
    if breakdown not in ("type_c", "b_ss", "team", "category", "live_game_manager"):
        return jsonify({"error": "invalid breakdown"}), 400
    filters = {}
    for col in FILTERABLE_CORRECTION_COLUMNS:
        val = request.args.get(col, "").strip()
        if val:
            filters[col] = val

    game_filters = {}
    game_filter_names = [
        "home_team", "away_team",
        "data_entry", "caller_1", "caller_2", "timer",
        "shot_clock_operator", "irs_operator",
        "arrival_time", "checklist_on_time", "communication",
        "corrections_speed", "rescouted",
        "live_game_manager",
    ]
    for key in game_filter_names:
        val = request.args.get(key, "").strip()
        if val:
            game_filters[key] = val

    competition = request.args.get("competition", "").strip()
    season = request.args.get("season", "").strip()
    # Always join Game so we can enforce Game.is_processed = 1
    join_game = True

    where_parts = []
    params = []

    # Base constraint: only processed games
    where_parts.append("G.is_processed = 1")

    for col, val in filters.items():
        where_parts.append(f"C.{col} = ?")
        params.append(val)

    if "home_team" in game_filters:
        where_parts.append("G.code_h = ?")
        params.append(game_filters["home_team"])
    if "away_team" in game_filters:
        where_parts.append("G.code_a = ?")
        params.append(game_filters["away_team"])
    for field in ("data_entry", "caller_1", "caller_2", "timer", "shot_clock_operator", "irs_operator"):
        if field in game_filters:
            where_parts.append(f"G.{field} = ?")
            params.append(game_filters[field])
    for field in ("arrival_time", "checklist_on_time", "communication", "corrections_speed", "rescouted"):
        if field in game_filters:
            where_parts.append(f"G.{field} = ?")
            params.append(game_filters[field])
    # live game manager (ara és camp de Game, no de Correction)
    if "live_game_manager" in game_filters:
        where_parts.append("G.live_game_manager = ?")
        params.append(game_filters["live_game_manager"])

    if competition:
        where_parts.append("C.game_code LIKE ?")
        params.append(f"{competition}%")
    if season:
        season_year = season.split("-")[0].strip()
        if season_year:
            where_parts.append("C.game_code LIKE ?")
            params.append(f"%{season_year}%")

    where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""
    from_clause = " FROM Correction C"
    if join_game:
        from_clause += " JOIN Game G ON C.game_code = G.game_code"

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if breakdown == "type_c":
        group_select_col = "C.type_c"
    elif breakdown == "b_ss":
        group_select_col = "C.b_ss"
    elif breakdown == "category":
        group_select_col = "C.category"
    elif breakdown == "live_game_manager":
        group_select_col = "G.live_game_manager"
    else:
        group_select_col = "C.team"
    cur.execute(
        "SELECT C.game_code, "
        + group_select_col
        + " AS breakdown_value, COUNT(*) AS errors_count"
        + from_clause
        + where_clause
        + " GROUP BY C.game_code, "
        + group_select_col
        + " ORDER BY C.game_code ASC, "
        + group_select_col
        + " ASC",
        params,
    )
    grouped_rows = [dict(r) for r in cur.fetchall()]

    def resolve_team_label(team_code: str) -> str:
        code = (team_code or "").strip()
        if not code:
            return ""
        cur.execute(
            "SELECT team_name FROM Team WHERE team_code = ? LIMIT 1",
            (code,),
        )
        team_row = cur.fetchone()
        if team_row and team_row["team_name"]:
            return str(team_row["team_name"]).strip()
        return code

    selected_home_team_code = game_filters.get("home_team", "").strip()
    selected_home_team_name = resolve_team_label(selected_home_team_code)

    type_columns = sorted({
        (r.get("breakdown_value") or "").strip()
        for r in grouped_rows
        if (r.get("breakdown_value") or "").strip()
    })

    # Per al breakdown per LGM volem totes les columnes encara que un LGM
    # no tingui cap correcció (apareixerà amb 0 a cada partit).
    if breakdown == "live_game_manager":
        cur.execute("SELECT name FROM Lgm WHERE name IS NOT NULL AND name != ''")
        all_lgm_names = {(row["name"] or "").strip() for row in cur.fetchall()}
        all_lgm_names.discard("")
        type_columns = sorted(set(type_columns) | all_lgm_names)
    by_game = {}
    for r in grouped_rows:
        game_code = r.get("game_code", "")
        type_c = (r.get("breakdown_value") or "").strip()
        count = int(r.get("errors_count") or 0)
        if game_code not in by_game:
            by_game[game_code] = {"game_code": game_code, "errors_count": 0}
        by_game[game_code]["errors_count"] += count
        if type_c:
            by_game[game_code][type_c] = count

    # Per al breakdown per LGM, incloem també els partits que coincideixen amb
    # els filtres de Game però que tenen 0 correccions (no apareixen a la consulta
    # principal perquè surt de Correction). Cada partit té un únic LGM, així que
    # la seva fila quedarà amb 0 correccions a totes les columnes.
    if breakdown == "live_game_manager":
        game_where_parts = ["g.is_processed = 1"]
        game_params: list = []
        if "game_code" in filters:
            game_where_parts.append("g.game_code = ?")
            game_params.append(filters["game_code"])
        if "home_team" in game_filters:
            game_where_parts.append("g.code_h = ?")
            game_params.append(game_filters["home_team"])
        if "away_team" in game_filters:
            game_where_parts.append("g.code_a = ?")
            game_params.append(game_filters["away_team"])
        for field in ("data_entry", "caller_1", "caller_2", "timer", "shot_clock_operator", "irs_operator"):
            if field in game_filters:
                game_where_parts.append(f"g.{field} = ?")
                game_params.append(game_filters[field])
        for field in ("arrival_time", "checklist_on_time", "communication", "corrections_speed", "rescouted"):
            if field in game_filters:
                game_where_parts.append(f"g.{field} = ?")
                game_params.append(game_filters[field])
        if "live_game_manager" in game_filters:
            game_where_parts.append("g.live_game_manager = ?")
            game_params.append(game_filters["live_game_manager"])
        if competition:
            game_where_parts.append("g.game_code LIKE ?")
            game_params.append(f"{competition}%")
        if season:
            season_year = season.split("-")[0].strip()
            if season_year:
                game_where_parts.append("g.game_code LIKE ?")
                game_params.append(f"%{season_year}%")

        cur.execute(
            "SELECT g.game_code FROM Game g WHERE " + " AND ".join(game_where_parts),
            game_params,
        )
        for row in cur.fetchall():
            gc = row["game_code"]
            if gc not in by_game:
                by_game[gc] = {"game_code": gc, "errors_count": 0}

    wb = Workbook()
    ws = wb.active
    ws.title = "Errors by game"
    headers = ["GAME_CODE", "NUM CORRECTIONS"] + type_columns
    ws.append(headers)
    for game_code in sorted(by_game.keys()):
        row = by_game[game_code]
        ws.append([row.get("game_code", ""), row.get("errors_count", 0)] + [row.get(col, 0) for col in type_columns])

    total_num_corrections = 0
    totals_by_type = {col: 0 for col in type_columns}
    for row in by_game.values():
        total_num_corrections += int(row.get("errors_count", 0) or 0)
        for col in type_columns:
            totals_by_type[col] += int(row.get(col, 0) or 0)
    ws.append(["TOTAL", total_num_corrections] + [totals_by_type[col] for col in type_columns])

    def sanitize_filename_part(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (value or "").strip())
        cleaned = "_".join([p for p in cleaned.split("_") if p])
        return cleaned[:40]

    def add_named_part(parts: list[str], filter_name: str, selected_value: str) -> None:
        value_part = sanitize_filename_part(selected_value)
        name_part = sanitize_filename_part(filter_name)
        if value_part and name_part:
            parts.append(f"{value_part}_as_{name_part}")

    filename_parts = []

    if selected_home_team_name:
        add_named_part(filename_parts, "home_team", selected_home_team_name)

    away_team_code = game_filters.get("away_team", "").strip()
    if away_team_code:
        away_team_name = resolve_team_label(away_team_code)
        away_label = away_team_name or away_team_code
        add_named_part(filename_parts, "away_team", away_label)

    if competition:
        add_named_part(filename_parts, "competition", competition)
    if season:
        add_named_part(filename_parts, "season", season)

    for col in FILTERABLE_CORRECTION_COLUMNS:
        val = filters.get(col, "").strip()
        if val:
            add_named_part(filename_parts, col, val)

    for field in ("data_entry", "caller_1", "caller_2", "timer", "shot_clock_operator", "irs_operator",
                  "arrival_time", "checklist_on_time", "communication", "corrections_speed", "rescouted",
                  "live_game_manager"):
        val = game_filters.get(field, "").strip()
        if val:
            add_named_part(filename_parts, field, val)

    base_name = "_".join(filename_parts) if filename_parts else "all_corrections"
    base_name = base_name[:180].rstrip("_")
    if breakdown == "type_c":
        suffix = "corrections_by_type_breakdown"
    elif breakdown == "b_ss":
        suffix = "boxscore_scoresheet_breakdown"
    elif breakdown == "category":
        suffix = "corrections_by_category_breakdown"
    elif breakdown == "live_game_manager":
        suffix = "corrections_by_live_game_manager_breakdown"
    else:
        suffix = "corrections_by_team_breakdown"
    download_name = f"{base_name}_{suffix}.xlsx"
    conn.close()

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/team_codes")
def api_team_codes():
    """Return distinct team codes for filters."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT team_code FROM Team WHERE team_code IS NOT NULL AND team_code != '' ORDER BY team_code")
    codes = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(codes)


@app.route("/api/teams")
def api_teams():
    """Return team_code + team_name (for UI labels)."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT team_code, team_name FROM Team WHERE team_code IS NOT NULL AND team_code != '' ORDER BY team_code"
    )
    teams = [{"team_code": r["team_code"], "team_name": r["team_name"]} for r in cur.fetchall()]
    conn.close()
    return jsonify(teams)


@app.route("/api/uscs_for_team/<team_code>")
def api_uscs_for_team(team_code: str):
    """Return USC names for a given team_code (for filters)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT name FROM Usc WHERE team_code = ? AND name IS NOT NULL AND name != '' ORDER BY name",
        (team_code,),
    )
    names = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(names)


@app.route("/api/uscs")
def api_uscs():
    """Return all USC names from Usc table (independent from team)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT name FROM Usc WHERE name IS NOT NULL AND name != '' ORDER BY name"
    )
    names = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(names)


USC_ROLE_COLUMNS = (
    "data_entry",
    "caller_1",
    "caller_2",
    "timer",
    "shot_clock_operator",
    "irs_operator",
)


@app.route("/api/usc_role_options")
def api_usc_role_options():
    """Return distinct USC names for the selected role column in Game."""
    role = request.args.get("role", "").strip()
    if role != "any" and role not in USC_ROLE_COLUMNS:
        return jsonify({"error": "invalid role"}), 400

    conn = get_db()
    cur = conn.cursor()
    if role == "any":
        name_set = set()
        for col in USC_ROLE_COLUMNS:
            query = f"SELECT DISTINCT {col} FROM Game WHERE is_processed = 1 AND {col} IS NOT NULL AND {col} != ''"
            cur.execute(query)
            name_set.update(row[0] for row in cur.fetchall())
        names = sorted(name_set)
    else:
        query = f"SELECT DISTINCT {role} FROM Game WHERE is_processed = 1 AND {role} IS NOT NULL AND {role} != '' ORDER BY {role}"
        cur.execute(query)
        names = [row[0] for row in cur.fetchall()]
    conn.close()
    return jsonify(names)


@app.route("/api/usc_role_result_average")
def api_usc_role_result_average():
    """Return AVG(Game.result) and games count for one USC in one role (read-only)."""
    role = request.args.get("role", "").strip()
    usc_name = request.args.get("usc_name", "").strip()

    if role != "any" and role not in USC_ROLE_COLUMNS:
        return jsonify({"error": "invalid role"}), 400
    if not usc_name:
        return jsonify({"error": "usc_name is required"}), 400

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if role == "any":
        any_role_where = " OR ".join([f"{col} = ?" for col in USC_ROLE_COLUMNS])
        params = tuple(usc_name for _ in USC_ROLE_COLUMNS)
        query = f"""
            SELECT
                COUNT(*) AS games_count,
                AVG(result) AS avg_result
            FROM Game
            WHERE is_processed = 1
              AND ({any_role_where})
              AND result IS NOT NULL
        """
        cur.execute(query, params)
    else:
        query = f"""
            SELECT
                COUNT(*) AS games_count,
                AVG(result) AS avg_result
            FROM Game
            WHERE is_processed = 1
              AND {role} = ?
              AND result IS NOT NULL
        """
        cur.execute(query, (usc_name,))
    row = cur.fetchone()
    conn.close()

    games_count = int(row["games_count"] or 0)
    avg_result = float(row["avg_result"]) if row["avg_result"] is not None else None
    return jsonify({
        "role": role,
        "usc_name": usc_name,
        "games_count": games_count,
        "avg_result": avg_result,
    })


@app.route("/api/uscs_result_average")
def api_uscs_result_average():
    """Return averages and games count for combined USC role filters (read-only)."""
    role_filters = {}
    for col in USC_ROLE_COLUMNS:
        val = request.args.get(col, "").strip()
        if val:
            role_filters[col] = val
    any_usc = request.args.get("any_usc", "").strip()
    team = request.args.get("team", "").strip()

    where_parts = []
    params = []
    for col, val in role_filters.items():
        where_parts.append(f"{col} = ?")
        params.append(val)
    if any_usc:
        any_role_where = " OR ".join([f"{col} = ?" for col in USC_ROLE_COLUMNS])
        where_parts.append(f"({any_role_where})")
        params.extend([any_usc] * len(USC_ROLE_COLUMNS))
    if team:
        # Team filter is home team only (Game.code_h)
        where_parts.append("code_h = ?")
        params.append(team)
    # Base constraint: only processed games
    where_parts.append("is_processed = 1")

    where_clause = " AND ".join(where_parts) if where_parts else "1=1"

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = f"""
        SELECT
            COUNT(*) AS games_count,
            AVG(result) AS avg_result,
            AVG(total_corrections) AS avg_total_corrections,
            AVG(total_actions) AS avg_total_actions,
            AVG(CASE WHEN game_code LIKE 'E%' THEN result END) AS avg_result_euroleague,
            AVG(CASE WHEN game_code LIKE 'U%' THEN result END) AS avg_result_eurocup,
            AVG(result) AS avg_result_general,
            AVG(CASE WHEN game_code LIKE 'E%' THEN total_corrections END) AS avg_corrections_euroleague,
            AVG(CASE WHEN game_code LIKE 'U%' THEN total_corrections END) AS avg_corrections_eurocup,
            AVG(total_corrections) AS avg_corrections_general
        FROM Game
        WHERE {where_clause}
    """
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()

    games_count = int(row["games_count"] or 0)
    avg_result = float(row["avg_result"]) if row["avg_result"] is not None else None
    avg_total_corrections = float(row["avg_total_corrections"]) if row["avg_total_corrections"] is not None else None
    avg_total_actions = float(row["avg_total_actions"]) if row["avg_total_actions"] is not None else None
    avg_result_euroleague = float(row["avg_result_euroleague"]) if row["avg_result_euroleague"] is not None else None
    avg_result_eurocup = float(row["avg_result_eurocup"]) if row["avg_result_eurocup"] is not None else None
    avg_result_general = float(row["avg_result_general"]) if row["avg_result_general"] is not None else None
    avg_corrections_euroleague = float(row["avg_corrections_euroleague"]) if row["avg_corrections_euroleague"] is not None else None
    avg_corrections_eurocup = float(row["avg_corrections_eurocup"]) if row["avg_corrections_eurocup"] is not None else None
    avg_corrections_general = float(row["avg_corrections_general"]) if row["avg_corrections_general"] is not None else None

    return jsonify({
        "filters": role_filters,
        "any_usc": any_usc,
        "team": team,
        "games_count": games_count,
        "avg_result": avg_result,
        "avg_total_corrections": avg_total_corrections,
        "avg_total_actions": avg_total_actions,
        "avg_result_euroleague": avg_result_euroleague,
        "avg_result_eurocup": avg_result_eurocup,
        "avg_result_general": avg_result_general,
        "avg_corrections_euroleague": avg_corrections_euroleague,
        "avg_corrections_eurocup": avg_corrections_eurocup,
        "avg_corrections_general": avg_corrections_general,
    })


@app.route("/api/uscs_result_by_home_team")
def api_uscs_result_by_home_team():
    """Return USC filtered averages grouped by Game.code_h (read-only)."""
    role_filters = {}
    for col in USC_ROLE_COLUMNS:
        val = request.args.get(col, "").strip()
        if val:
            role_filters[col] = val
    any_usc = request.args.get("any_usc", "").strip()
    team = request.args.get("team", "").strip()

    if not role_filters and not any_usc and not team:
        return jsonify({"error": "at least one USC filter or team is required"}), 400

    where_parts = []
    params = []
    for col, val in role_filters.items():
        where_parts.append(f"g.{col} = ?")
        params.append(val)
    if any_usc:
        any_role_where = " OR ".join([f"g.{col} = ?" for col in USC_ROLE_COLUMNS])
        where_parts.append(f"({any_role_where})")
        params.extend([any_usc] * len(USC_ROLE_COLUMNS))
    if team:
        # Team filter is home team only (Game.code_h)
        where_parts.append("g.code_h = ?")
        params.append(team)
    # Base constraint: only processed games
    where_parts.append("g.is_processed = 1")
    where_clause = " AND ".join(where_parts)

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT
            g.code_h AS home_team_code,
            t.team_name AS home_team_name,
            COUNT(*) AS games_count,
            AVG(g.result) AS avg_result,
            AVG(g.total_corrections) AS avg_corrections,
            AVG(g.total_actions) AS avg_actions
        FROM Game g
        LEFT JOIN Team t ON g.code_h = t.team_code
        WHERE {where_clause}
        GROUP BY g.code_h, t.team_name
        ORDER BY games_count DESC, g.code_h ASC
        """
        ,
        params,
    )
    rows = []
    for r in cur.fetchall():
        rows.append({
            "home_team_code": r["home_team_code"] or "",
            "home_team_name": r["home_team_name"] or "",
            "games_count": int(r["games_count"] or 0),
            "avg_result": float(r["avg_result"]) if r["avg_result"] is not None else None,
            "avg_corrections": float(r["avg_corrections"]) if r["avg_corrections"] is not None else None,
            "avg_actions": float(r["avg_actions"]) if r["avg_actions"] is not None else None,
        })
    conn.close()

    return jsonify({"items": rows})


@app.route("/api/usc_any_role_breakdown")
def api_usc_any_role_breakdown():
    """Return per-role breakdown for one USC selected in any role (read-only)."""
    usc_name = request.args.get("usc_name", "").strip()
    if not usc_name:
        return jsonify({"error": "usc_name is required"}), 400

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    items = []
    for role in USC_ROLE_COLUMNS:
        query = f"""
            SELECT
                COUNT(*) AS games_count,
                AVG(result) AS avg_result,
                AVG(total_corrections) AS avg_corrections,
                AVG(total_actions) AS avg_actions
            FROM Game
            WHERE is_processed = 1
              AND {role} = ?
        """
        cur.execute(query, (usc_name,))
        row = cur.fetchone()
        games_count = int(row["games_count"] or 0)
        if games_count == 0:
            continue
        items.append({
            "role": role,
            "games_count": games_count,
            "avg_result": float(row["avg_result"]) if row["avg_result"] is not None else None,
            "avg_corrections": float(row["avg_corrections"]) if row["avg_corrections"] is not None else None,
            "avg_actions": float(row["avg_actions"]) if row["avg_actions"] is not None else None,
        })

    conn.close()
    return jsonify({"usc_name": usc_name, "items": items})


@app.route("/api/uscs_global_split_averages")
def api_uscs_global_split_averages():
    """Return fixed global split averages (independent from any filter)."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            AVG(CASE WHEN game_code LIKE 'E%' THEN result END) AS avg_result_euroleague,
            AVG(CASE WHEN game_code LIKE 'U%' THEN result END) AS avg_result_eurocup,
            AVG(result) AS avg_result_general,
            AVG(CASE WHEN game_code LIKE 'E%' THEN total_corrections END) AS avg_corrections_euroleague,
            AVG(CASE WHEN game_code LIKE 'U%' THEN total_corrections END) AS avg_corrections_eurocup,
            AVG(total_corrections) AS avg_corrections_general
        FROM Game
        WHERE is_processed = 1
        """
    )
    row = cur.fetchone()
    conn.close()

    return jsonify({
        "avg_result_euroleague": float(row["avg_result_euroleague"]) if row["avg_result_euroleague"] is not None else None,
        "avg_result_eurocup": float(row["avg_result_eurocup"]) if row["avg_result_eurocup"] is not None else None,
        "avg_result_general": float(row["avg_result_general"]) if row["avg_result_general"] is not None else None,
        "avg_corrections_euroleague": float(row["avg_corrections_euroleague"]) if row["avg_corrections_euroleague"] is not None else None,
        "avg_corrections_eurocup": float(row["avg_corrections_eurocup"]) if row["avg_corrections_eurocup"] is not None else None,
        "avg_corrections_general": float(row["avg_corrections_general"]) if row["avg_corrections_general"] is not None else None,
    })


@app.route("/api/uscs_combinations_by_team")
def api_uscs_combinations_by_team():
    """Return USC role combinations stats for a selected home team (code_h)."""
    team = request.args.get("team", "").strip()
    if not team:
        return jsonify({"error": "team is required"}), 400

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            data_entry,
            caller_1,
            caller_2,
            timer,
            shot_clock_operator,
            irs_operator,
            COUNT(*) AS games_count,
            AVG(result) AS avg_result,
            AVG(total_corrections) AS avg_corrections,
            AVG(total_actions) AS avg_actions
        FROM Game
        WHERE is_processed = 1
          AND code_h = ?
        GROUP BY
            data_entry, caller_1, caller_2, timer, shot_clock_operator, irs_operator
        ORDER BY games_count DESC
        """,
        (team,),
    )
    items = []
    for r in cur.fetchall():
        items.append({
            "data_entry": (r["data_entry"] or "").strip(),
            "caller_1": (r["caller_1"] or "").strip(),
            "caller_2": (r["caller_2"] or "").strip(),
            "timer": (r["timer"] or "").strip(),
            "shot_clock_operator": (r["shot_clock_operator"] or "").strip(),
            "irs_operator": (r["irs_operator"] or "").strip(),
            "games_count": int(r["games_count"] or 0),
            "avg_result": float(r["avg_result"]) if r["avg_result"] is not None else None,
            "avg_corrections": float(r["avg_corrections"]) if r["avg_corrections"] is not None else None,
            "avg_actions": float(r["avg_actions"]) if r["avg_actions"] is not None else None,
        })
    conn.close()
    return jsonify({"team": team, "items": items})


@app.route("/api/game_uscs_snapshot")
def api_game_uscs_snapshot():
    """Return USC role assignments and key metrics for one game_code (read-only)."""
    game_code = request.args.get("game_code", "").strip()
    if not game_code:
        return jsonify({"error": "game_code is required"}), 400

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            g.game_code,
            g.code_h,
            g.code_a,
            th.team_name AS home_team_name,
            ta.team_name AS away_team_name,
            g.data_entry,
            g.caller_1,
            g.caller_2,
            g.timer,
            g.shot_clock_operator,
            g.irs_operator,
            g.result,
            g.total_corrections,
            g.total_actions
        FROM Game g
        LEFT JOIN Team th ON g.code_h = th.team_code
        LEFT JOIN Team ta ON g.code_a = ta.team_code
        WHERE g.is_processed = 1 AND g.game_code = ?
        LIMIT 1
        """,
        (game_code,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "game_code not found"}), 404

    home_label = (row["home_team_name"] or row["code_h"] or "").strip()
    away_label = (row["away_team_name"] or row["code_a"] or "").strip()

    return jsonify({
        "game_code": row["game_code"],
        "code_h": row["code_h"] or "",
        "code_a": row["code_a"] or "",
        "home_team_name": row["home_team_name"] or "",
        "away_team_name": row["away_team_name"] or "",
        "home_team_label": home_label,
        "away_team_label": away_label,
        "roles": {
            "data_entry": row["data_entry"] or "",
            "caller_1": row["caller_1"] or "",
            "caller_2": row["caller_2"] or "",
            "timer": row["timer"] or "",
            "shot_clock_operator": row["shot_clock_operator"] or "",
            "irs_operator": row["irs_operator"] or "",
        },
        "result": float(row["result"]) if row["result"] is not None else None,
        "total_corrections": float(row["total_corrections"]) if row["total_corrections"] is not None else None,
        "total_actions": float(row["total_actions"]) if row["total_actions"] is not None else None,
    })


@app.route("/api/logistics_counts")
def api_logistics_counts():
    """Return counts for each logistics value, given current Game-level filters."""
    # read game filters from query parameters
    game_filters = {}
    game_filter_names = [
        "home_team",
        "away_team",
        "data_entry",
        "caller_1",
        "caller_2",
        "timer",
        "shot_clock_operator",
        "irs_operator",
        "arrival_time",
        "checklist_on_time",
        "communication",
        "corrections_speed",
        "rescouted",
    ]
    for key in game_filter_names:
        val = request.args.get(key, "").strip()
        if val:
            game_filters[key] = val

    # helper to build WHERE for Game table, excluding a specific field
    def build_where(exclude_field: str):
        parts = ["is_processed = 1"]
        params_local = []
        # home/away codes
        if "home_team" in game_filters and exclude_field != "home_team":
            parts.append("code_h = ?")
            params_local.append(game_filters["home_team"])
        if "away_team" in game_filters and exclude_field != "away_team":
            parts.append("code_a = ?")
            params_local.append(game_filters["away_team"])
        # USCs
        for field in ("data_entry", "caller_1", "caller_2", "timer", "shot_clock_operator", "irs_operator"):
            if field in game_filters and exclude_field != field:
                parts.append(f"{field} = ?")
                params_local.append(game_filters[field])
        # logistics
        for field in ("arrival_time", "checklist_on_time", "communication", "corrections_speed", "rescouted"):
            if field in game_filters and exclude_field != field:
                parts.append(f"{field} = ?")
                params_local.append(game_filters[field])

        where_clause_local = ""
        if parts:
            where_clause_local = " WHERE " + " AND ".join(parts)
        return where_clause_local, params_local

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    result = {}
    logistics_fields = ["arrival_time", "checklist_on_time", "communication", "corrections_speed", "rescouted"]
    for field in logistics_fields:
        where_clause, params_local = build_where(field)
        query = f"SELECT {field} AS v, COUNT(*) AS c FROM Game{where_clause} GROUP BY {field}"
        cur.execute(query, params_local)
        counts = {}
        for row in cur.fetchall():
            val = row["v"]
            if val is None or val == "":
                continue
            counts[val] = row["c"]
        result[field] = counts

    conn.close()
    return jsonify(result)

@app.route("/run-correction", methods=["POST"])
def run_correction_route():
    try:
        data = request.get_json(silent=True) or {}
        game_code = data.get("game_code")
        alt_channel_id = data.get("alternative_channel_id")
        if not game_code:
            return jsonify({"status": "error", "message": "game_code is required"}), 400
        # Positional args to be compatible with current runCorrectionsProcessor signature
        runCorrectionsProcessor(game_code, alt_channel_id)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ----------------- Correccions -----------------
@app.route("/corrections/<game_code>")
def get_corrections(game_code):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # live_game_manager ve de Game (JOIN), no de Correction.
    cur.execute(
        """
        SELECT """
        + CORRECTION_ROW_SELECT
        + """
        FROM Correction C
        LEFT JOIN Game G ON C.game_code = G.game_code
        WHERE C.game_code = ?
        """,
        (game_code,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/update", methods=["POST"])
def update_correction():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE Correction
        SET time=?, quarter=?, points_h=?, points_a=?, action_num=?, b_ss=?, team=?,
            type_c=?, category=?
        WHERE rowid=?
    """, (
        data["time"], data["quarter"], data["points_h"], data["points_a"],
        data["action_num"], data["b_ss"], data["team"], data["type_c"],
        data["category"], data["rowid"]
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/add_correction", methods=["POST"])
def add_correction():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Correction
        (time, quarter, points_h, points_a, action_num, b_ss,
         team, type_c, category, game_code, thread_name, correction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["time"], data["quarter"], data["points_h"], data["points_a"],
        data["action_num"], data["b_ss"], data["team"], data["type_c"],
        data["category"], data["game_code"], "Correcció Manual",
        "Correcció Manual"
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/delete_correction/<int:rowid>", methods=["DELETE"])
def delete_correction(rowid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Correction WHERE rowid = ?", (rowid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ----------------- USCs per partit -----------------
@app.route("/get_game_uscs/<game_code>")
def get_game_uscs(game_code):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT data_entry, caller_1, caller_2, timer, shot_clock_operator, irs_operator
        FROM Game WHERE game_code = ?
    """, (game_code,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "game_code no trobat"}), 404
    return jsonify({
        "data_entry": row["data_entry"],
        "caller_1": row["caller_1"],
        "caller_2": row["caller_2"],
        "timer": row["timer"],
        "shot_clock_operator": row["shot_clock_operator"],
        "irs_operator": row["irs_operator"]
    })


@app.route("/game_report_data/<game_code>")
def game_report_data(game_code):
    """Dades persistides del report (Game): accions, USCs, logística, comentari LGM."""
    conn = get_db()
    ensure_game_logistics_columns(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_entry, caller_1, caller_2, timer, shot_clock_operator, irs_operator,
               arrival_time, checklist_on_time, communication, corrections_speed, rescouted,
               total_actions, lgm_comment, live_game_manager
        FROM Game WHERE game_code = ?
        """,
        (game_code,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "game not found"}), 404

    def nz(v):
        return v if v is not None else ""

    ta = row["total_actions"]
    return jsonify(
        {
            "data_entry": nz(row["data_entry"]),
            "caller_1": nz(row["caller_1"]),
            "caller_2": nz(row["caller_2"]),
            "timer": nz(row["timer"]),
            "shot_clock_operator": nz(row["shot_clock_operator"]),
            "irs_operator": nz(row["irs_operator"]),
            "arrival_time": nz(row["arrival_time"]),
            "checklist_on_time": nz(row["checklist_on_time"]),
            "communication": nz(row["communication"]),
            "corrections_speed": nz(row["corrections_speed"]),
            "rescouted": nz(row["rescouted"]),
            "total_actions": "" if ta is None else ta,
            "lgm_comment": nz(row["lgm_comment"]),
            "live_game_manager": nz(row["live_game_manager"]),
        }
    )

# ----------------- USCs temporada -----------------
@app.route("/get_uscs_for_game/<game_code>")
def get_uscs_for_game(game_code):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT code_h
        FROM Game
        WHERE game_code = ?
    """, (game_code,))
    
    row = cursor.fetchone()
    if not row:
        return jsonify([])

    code_a = row[0]

    cursor.execute("""
        SELECT name
        FROM Usc
        WHERE team_code = ?
        ORDER BY name
    """, (code_a,))

    names = [r[0] for r in cursor.fetchall()]

    return jsonify(names)


# ----------------- Live Game Managers -----------------
@app.route("/get_live_game_managers")
def get_live_game_managers():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name FROM Lgm")
    names = [row["name"] for row in cur.fetchall()]
    conn.close()
    return jsonify(names)

# ----------------- Dades Report -----------------
@app.route("/generate_report/<game_code>/<lgm>")
def generate_report(game_code, lgm):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Assegurar que la taula Game té les columnes de logística necessàries
    ensure_game_logistics_columns(conn)

    # Dades del partit
    cur.execute("SELECT * FROM Game WHERE game_code = ?", (game_code,))
    game = cur.fetchone()
    if not game:
        return "Game not found", 404

    # Crear data DD/MM/YYYY
    game_date = f"{game['day']:02d}/{game['month']:02d}/{game['year']}"
    game_round = game['round']
    code_h = game['code_h']
    code_a = game['code_a']

    # Equips
    cur.execute("SELECT team_name FROM Team WHERE team_code = ?", (game["code_h"],))
    local_team = cur.fetchone()["team_name"]
    cur.execute("SELECT team_name FROM Team WHERE team_code = ?", (game["code_a"],))
    away_team = cur.fetchone()["team_name"]

    # USCs rebuts del formulari
    data_entry = request.args.get("data_entry", "")
    caller_1 = request.args.get("caller_1", "")
    caller_2 = request.args.get("caller_2", "")
    timer = request.args.get("timer", "")
    shot_clock = request.args.get("shot_clock", "")
    irs_operator = request.args.get("irs_operator", "")

    # Logistics rebuts del formulari
    arrival_time = request.args.get("arrival_time", "")
    checklist_on_time = request.args.get("checklist_on_time", "")
    communication = request.args.get("communication", "")
    corrections_speed = request.args.get("corrections_speed", "")
    rescouted = request.args.get("rescouted", "")

    # Num accions
    raw_num_accions = request.args.get("num_accions", "")
    try:
        num_accions = int(raw_num_accions) if raw_num_accions not in ("", None) else 0
    except ValueError:
        num_accions = 0

    # Num correccions
    cur.execute("SELECT COUNT(*) as total_corr FROM Correction WHERE game_code = ?", (game_code,))
    total_corrections = cur.fetchone()["total_corr"]

    # % correccions
    percent_corrections = (total_corrections / num_accions * 100) if num_accions > 0 else 0

    # Correccions per equip (Home, Away o No Team)
    cur.execute("""
        SELECT team, COUNT(*) as total
        FROM Correction
        WHERE game_code = ?
        GROUP BY team
    """, (game_code,))

    team_counts_raw = cur.fetchall()

    team_counts = {
        "HOME TEAM": 0,
        "AWAY TEAM": 0,
        "NO TEAM": 0
    }

    for row in team_counts_raw:
        if row["team"] in team_counts:
            team_counts[row["team"]] = row["total"]

    # Correccions per quart (1, 2, 3, 4 o ET)
    cur.execute("""
        SELECT quarter, COUNT(*) as total
        FROM Correction
        WHERE game_code = ?
        GROUP BY quarter
    """, (game_code,))

    quarter_counts_raw = cur.fetchall()

    quarter_counts = {
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "ET": 0
    }

    for row in quarter_counts_raw:
        if row["quarter"] in quarter_counts:
            quarter_counts[row["quarter"]] = row["total"]

    # Num correccions (Boxscore o Scoresheet)
    # Definir grups
    scoresheet_types = ["COACH CHALLENGE", "FOULS", "IRS", "JUMP BALL", "POINTS", "SUBS", "TOUT"]
    boxscore_types = ["CRITERIA", "MISIDENTITY", "MISSING", "MISPLACED", "NOT HAPPENED", "TIMING"]

    # Comptar total per b_ss
    cur.execute("SELECT COUNT(*) as total FROM Correction WHERE game_code = ? AND b_ss = 'SCORESHEET'", (game_code,))
    total_scoresheet = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) as total FROM Correction WHERE game_code = ? AND b_ss = 'BOXSCORE'", (game_code,))
    total_boxscore = cur.fetchone()["total"]

    # Comptar dinàmicament els type_c per Scoresheet
    scoresheet_counts = {}
    for t in scoresheet_types:
        cur.execute("SELECT COUNT(*) as total FROM Correction WHERE game_code = ? AND type_c = ?", (game_code, t))
        scoresheet_counts[t] = cur.fetchone()["total"]

    # Comptar dinàmicament els type_c per Boxscore
    boxscore_counts = {}
    for t in boxscore_types:
        cur.execute("SELECT COUNT(*) as total FROM Correction WHERE game_code = ? AND type_c = ?", (game_code, t))
        boxscore_counts[t] = cur.fetchone()["total"]

    # Comentari live game manager: el preview JSON (format=json) no envia valoracions;
    # si no hi és als query params, conservem el valor persistit i no esborrem la BD.
    if "valoracions" in request.args:
        comentari = request.args.get("valoracions", "")
    else:
        prev = game["lgm_comment"]
        comentari = prev if prev is not None else ""

    # Assignació de punts segons type_c
    points_map = {
        "COACH CHALLENGE": 10,
        "FOULS": 15,
        "IRS": 10,
        "JUMPBALL": 5,
        "POINTS": 20,
        "SUBSTITUTION": 5,
        "TIME OUT": 10,
        "CRITERIA": 0.5,
        "MISIDENTITY": 1,
        "MISSING": 2.5,
        "MISPLACED": 1,
        "NOT HAPPENED": 2,
        "TIMING": 1
    }

    # Càlcul de punts de correccions
    cur.execute("SELECT type_c FROM Correction WHERE game_code = ?", (game_code,))
    type_c_list = [row["type_c"] for row in cur.fetchall()]

    total_points = sum(points_map.get(t, 0) for t in type_c_list)

    # Afegir el % de correccions respecte el total d'accions al resultat final
    if num_accions > 0:
        percent_corrections = (len(type_c_list) / num_accions) * 100
    else:
        percent_corrections = 0

    # Punts de Logistics
    logistic_points = 0
    if arrival_time == "LATE":
        logistic_points += 2
    if checklist_on_time == "NO":
        logistic_points += 5
    if communication == "OK":
        logistic_points += 1
    elif communication == "NOT FLUID":
        logistic_points += 2
    if corrections_speed == "OK":
        logistic_points += 1
    elif corrections_speed == "SLOW":
        logistic_points += 2

    resultat_final = round(total_points + percent_corrections + logistic_points, 1)

    # Només persistim a Game quan es genera el PDF final (premuda "Generate Report").
    # En mode preview (format=json) NO s'escriu res a la BD.
    is_preview = request.args.get("format") == "json"
    if not is_preview:
        cur.execute(
            """
            UPDATE Game
            SET data_entry = ?,
                caller_1 = ?,
                caller_2 = ?,
                timer = ?,
                shot_clock_operator = ?,
                irs_operator = ?,
                arrival_time = ?,
                checklist_on_time = ?,
                communication = ?,
                corrections_speed = ?,
                rescouted = ?,
                total_actions = ?,
                total_corrections = ?,
                lgm_comment = ?,
                result = ?,
                live_game_manager = ?
            WHERE game_code = ?
            """,
            (
                data_entry,
                caller_1,
                caller_2,
                timer,
                shot_clock,
                irs_operator,
                arrival_time,
                checklist_on_time,
                communication,
                corrections_speed,
                rescouted,
                num_accions,
                total_corrections,
                comentari,
                resultat_final,
                lgm,
                game_code,
            ),
        )
        conn.commit()

    # Creació de json amb dades necessàries per omplir el report
    if "E" in game_code: 
        competition = "EUROLEAGUE" 
        competition_code = "E"
    else: 
        competition = "EUROCUP"
        competition_code = "U"

    game_number = game_code.split("_")[1]

    report_data = {
        "game": f"GAME: {game_code} ({competition}, Round: {game_round})",
        "date": f"DATE: {game_date}",
        "team_h": local_team,
        "team_a": away_team,
        "data_entry": data_entry,
        "caller_1": caller_1,
        "caller_2": caller_2,
        "timer": timer,
        "shot_clock": shot_clock,
        "irs_operator": irs_operator,
        "live_game_manager": f"LGM: {lgm}",
        "arrival_time": arrival_time,
        "checklist_on_time": checklist_on_time,
        "communication": communication,
        "corrections_speed": corrections_speed,
        "rescouted": rescouted,
        "total_actions": num_accions,
        "total_corrections": total_corrections,
        "%_corrections": f"{percent_corrections:.1f}",
        "home_team": team_counts["HOME TEAM"],
        "no_team": team_counts["NO TEAM"],
        "away_team": team_counts["AWAY TEAM"],
        "quarter_1": quarter_counts["1"],
        "quarter_2": quarter_counts["2"],
        "quarter_3": quarter_counts["3"],
        "quarter_4": quarter_counts["4"],
        "et": quarter_counts["ET"],
        "boxscore_corrections": total_boxscore,
        "scoresheet_corrections": total_scoresheet,
        "comments": comentari,
        "result": f"{resultat_final:.1f}"
    }

    type_to_json_key = {
        "CRITERIA": "criteria_corrections",
        "MISIDENTITY": "misidentity_corrections",
        "MISSING": "missing_corrections",
        "NOT HAPPENED": "not_happened_corrections",
        "MISPLACED": "misplaced_corrections",
        "TIMING": "timing_corrections",
        "JUMP BALL": "jump_ball_corrections",
        "SUBSTITUTIONS": "substitution_corrections",
        "IRS/CC": "irs_cc_corrections",
        "TIME OUT": "time_out_corrections",
        "FOULS": "fouls_corrections",
        "POINTS": "points_corrections",
    }

    # Bloc per afegir el nombre de correcció per type al json
    for type_c, json_key in type_to_json_key.items():
        if type_c == "IRS/CC":
            cur.execute(
                """
                SELECT COUNT(*) as total
                FROM Correction
                WHERE game_code = ?
                AND type_c IN ('IRS', 'CC')
                """,
                (game_code,)
            )
        
        else:
            cur.execute(
                "SELECT COUNT(*) as total FROM Correction WHERE game_code = ? AND type_c = ?",
                (game_code, type_c)
            )
            
        report_data[json_key] = cur.fetchone()["total"]

    conn.close()

    # Si es demana format JSON, retornar només el resultat calculat
    if request.args.get("format") == "json":
        return jsonify({
            "result": float(f"{resultat_final:.1f}")
        })

    # Generació del report: PNG template → PDF (ReportLab)
    template_path = os.path.join(app.root_path, "static", "report_template.png")
    pdf_buffer = generate_pdf_from_json(report_data, template_path)

    return send_file(
        pdf_buffer,
        download_name=f"REPORT_{game_round}_{game_number}_{code_h}_{code_a}_{competition_code}2025.pdf",
        mimetype="application/pdf"
    )

# ----------------- Execució -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)