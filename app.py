from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
DB = "dades.db"

def get_db():
    return sqlite3.connect(DB)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/corrections/<game_code>")
def get_corrections(game_code):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT rowid, * FROM Correction WHERE game_code = ?",
        (game_code,)
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
        data["time"],
        data["quarter"],
        data["points_h"],
        data["points_a"],
        data["action_num"],
        data["b_ss"],
        data["team"],
        data["type_c"],
        data["category"],
        data["rowid"]
    ))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/add_correction", methods=["POST"])
def add_correction():
    data = request.json
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Correction
        (time, quarter, points_h, points_a, action_num, b_ss,
         team, type_c, category, game_code, thread_name, correction, live_game_manager)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["time"],
        data["quarter"],
        data["points_h"],
        data["points_a"],
        data["action_num"],
        data["b_ss"],
        data["team"],
        data["type_c"],
        data["category"],
        data["game_code"],
        "Manual Correction",
        "Manual Correction",
        data["live_game_manager"]
    ))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/delete_correction/<int:rowid>", methods=["DELETE"])
def delete_correction(rowid):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM Correction WHERE rowid = ?", (rowid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/get_game_uscs/<game_code>")
def get_game_uscs(game_code):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            data_entry,
            caller_1,
            caller_2,
            timer,
            shot_clock_operator,
            irs_operator
        FROM Game
        WHERE game_code = ?
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
        "shot_clock": row["shot_clock_operator"],
        "irs_operator": row["irs_operator"]
    })

@app.route("/get_live_game_managers")
def get_live_game_managers():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name FROM Lgm")
    rows = cur.fetchall()
    names = [row["name"] for row in rows]
    conn.close()
    return jsonify(names)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)