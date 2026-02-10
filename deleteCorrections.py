import sqlite3

def clear_corrections_table():
    conn = sqlite3.connect("dades.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Correction WHERE b_ss IS NULL OR b_ss = ''")
    conn.commit()   
    conn.close()

    print("Taula Correction buidada correctament.")

clear_corrections_table()             