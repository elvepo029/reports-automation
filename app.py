from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import io
import pdfkit  # Assegura’t de tenir pdfkit i wkhtmltopdf instal·lats

app = Flask(__name__)
DB = "dades.db"

def get_db():
    return sqlite3.connect(DB)

@app.route("/")
def index():
    return render_template("index.html")

# ----------------- Correccions -----------------
@app.route("/corrections/<game_code>")
def get_corrections(game_code):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM Correction WHERE game_code = ?", (game_code,))
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
         team, type_c, category, game_code, thread_name, correction, live_game_manager)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["time"], data["quarter"], data["points_h"], data["points_a"],
        data["action_num"], data["b_ss"], data["team"], data["type_c"],
        data["category"], data["game_code"], "Manual Correction",
        "Manual Correction", data["live_game_manager"]
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

# ----------------- Generació de PDF -----------------
@app.route("/generate_report/<game_code>/<lgm>")
def generate_report(game_code, lgm):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    #Dades del partit
    cur.execute("SELECT * FROM Game WHERE game_code = ?", (game_code,))
    game = cur.fetchone()
    if not game:
        return "Game not found", 404

    #Crear data DD/MM/YYYY
    game_date = f"{game['day']:02d}/{game['month']:02d}/{game['year']}"

    #Equips
    cur.execute("SELECT team_name FROM Team WHERE team_code = ?", (game["code_h"],))
    local_team = cur.fetchone()["team_name"]
    cur.execute("SELECT team_name FROM Team WHERE team_code = ?", (game["code_a"],))
    away_team = cur.fetchone()["team_name"]

    #Dades USCs
    data_entry = game["data_entry"]
    caller_1 = game["caller_1"]
    caller_2 = game["caller_2"]
    timer = game["timer"]
    shot_clock = game["shot_clock_operator"]
    irs_operator = game["irs_operator"]  # opcional

    # ----------------- Bloc Game Info -----------------
    html = f"""
    <h1>Game Report - {game_code}</h1>
    <h2>Game Information</h2>
    <ul>
      <li><b>Game Code:</b> {game_code}</li>
      <li><b>Jornada:</b> {game['round']}</li>
      <li><b>Data:</b> {game_date}</li>
      <li><b>Equip Local:</b> {local_team}</li>
      <li><b>Equip Visitant:</b> {away_team}</li>
      <li><b>Data Entry:</b> {data_entry}</li>
      <li><b>Caller 1:</b> {caller_1}</li>
      <li><b>Caller 2:</b> {caller_2}</li>
      <li><b>Timer:</b> {timer}</li>
      <li><b>Shot Clock Operator:</b> {shot_clock}</li>
      <li><b>IRS Operator:</b> {irs_operator or ""}</li>
      <li><b>Live Game Manager:</b> {lgm}</li>
    </ul>
    """

    # ----------------- Bloc Logistics -----------------
    arrival_time = request.args.get("arrival_time", "")
    checklist_on_time = request.args.get("checklist_on_time", "")
    communication = request.args.get("communication", "")
    corrections_speed = request.args.get("corrections_speed", "")

    html += f"""
    <h2>Logistics</h2>
    <ul>
        <li><b>Arrival Time:</b> {arrival_time}</li>
        <li><b>Check List On Time:</b> {checklist_on_time}</li>
        <li><b>Communication:</b> {communication}</li>
        <li><b>Corrections:</b> {corrections_speed}</li>
    </ul>
    """

    # ----------------- Bloc Scouting - Corrections -----------------
    # Recollir num_accions de query params
    num_accions = int(request.args.get("num_accions", 0))

    # Comptar correccions a la base de dades
    cur.execute("SELECT COUNT(*) as total_corr FROM Correction WHERE game_code = ?", (game_code,))
    total_corrections = cur.fetchone()["total_corr"]

    # Calcular % de correccions respecte el total d'accions
    percent_corrections = (total_corrections / num_accions * 100) if num_accions > 0 else 0

    html += f"""
    <h2>Scouting</h2>
    <h3>Corrections</h3>
    <ul>
        <li><b>Num d'accions:</b> {num_accions}</li>
        <li><b>Nombre de correccions:</b> {total_corrections}</li>
        <li><b>% de correccions respecte el total d'accions:</b> {percent_corrections:.2f}%</li>
    </ul>
    """

    # -------- Corrections by Team --------
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

    html += f"""
    <h3>Corrections by Team</h3>
    <ul>
        <li><b>Home Team:</b> {team_counts["HOME TEAM"]}</li>
        <li><b>Away Team:</b> { team_counts["AWAY TEAM"]}</li>
        <li><b>No Team:</b> { team_counts["NO TEAM"]}</li>
    </ul>
    """

    # -------- Corrections by Quarter --------
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

    html += f"""
    <h3>Corrections by Quarter</h3>
    <ul>
        <li><b>Q1:</b> {quarter_counts["1"]}</li>
        <li><b>Q2:</b> {quarter_counts["2"]}</li>
        <li><b>Q3:</b> {quarter_counts["3"]}</li>
        <li><b>Q4:</b> {quarter_counts["4"]}</li>
        <li><b>ET:</b> {quarter_counts["ET"]}</li>
    </ul>
    """

    # ----------------- Bloc Scouting - Scoresheet i Boxscore -----------------
    # Definir grups
    scoresheet_types = ["COACH CHALLENGE", "FOULS", "IRS", "JUMP BALL", "POINTS", "SUBS", "TOUT"]
    boxscore_types = ["CRITERIA", "MISSIDENTITY", "MISSING", "MISSPLACED", "NOT HAPPENED", "TIMING"]

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

    # Afegir al HTML
    html += f"<h3>Scoresheet: {total_scoresheet}</h3><ul>"
    for t, c in scoresheet_counts.items():
        html += f"<li><b>{t.title()}:</b> {c}</li>"
    html += "</ul>"

    html += f"<h3>Boxscore: {total_boxscore}</h3><ul>"
    for t, c in boxscore_counts.items():
        html += f"<li><b>{t.title()}:</b> {c}</li>"
    html += "</ul>"

    # ----------------- Bloc Final Valorations -----------------
    # Recollir comentari de l'usuari (frontend)
    comentari = request.args.get("valoracions", "")

    # Assignació de punts segons type_c
    points_map = {
        "COACH CHALLENGE": 10,
        "FOULS": 15,
        "IRS": 10,
        "JUMP BALL": 5,
        "POINTS": 20,
        "SUBS": 5,
        "TOUT": 10,
        "CRITERIA": 0.5,
        "MISSIDENTITY": 1,
        "MISSING": 2.5,
        "MISSPLACED": 1,
        "NOT HAPPENED": 2,
        "TIMING": 1
    }

    # Comptar total punts de les correccions
    cur.execute("SELECT type_c FROM Correction WHERE game_code = ?", (game_code,))
    type_c_list = [row["type_c"] for row in cur.fetchall()]

    total_points = sum(points_map.get(t, 0) for t in type_c_list)

    # Afegir el % de correccions respecte el total d'accions al resultat final
    if num_accions > 0:
        percent_corrections = (len(type_c_list) / num_accions) * 100
    else:
        percent_corrections = 0

    # Punts segons Logistics
    logistic_points = 0
    if arrival_time == "Late":
        logistic_points += 2
    if checklist_on_time == "No":
        logistic_points += 5
    if communication == "Ok":
        logistic_points += 1
    elif communication == "Not Fluid":
        logistic_points += 2
    if corrections_speed == "Ok":
        logistic_points += 1
    elif corrections_speed == "Slow":
        logistic_points += 2

    resultat_final = total_points + percent_corrections + logistic_points

    # Afegir al HTML
    html += f"""
    <h2>Final Valorations</h2>
    <ul>
        <li><b>Comentari:</b> {comentari}</li>
        <li><b>Resultat Final:</b> {resultat_final:.2f}</li>
    </ul>
    """

    #Convertir a PDF
    #adreça mac
    #config = pdfkit.configuration(wkhtmltopdf="/usr/local/bin/wkhtmltopdf")
    #adreça windows
    config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
    pdf = pdfkit.from_string(html, False, configuration=config)

    conn.close()

    return send_file(
        io.BytesIO(pdf),
        download_name=f"Report_{game_code}.pdf",
        mimetype="application/pdf"
    )

# ----------------- Execució -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)