import sqlite3

DB_PATH = "dades.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Update type_c values with old spelling to new spelling
cur.execute("UPDATE Correction SET type_c = 'MISIDENTITY' WHERE type_c = 'MISSIDENTITY'")
cur.execute("UPDATE Correction SET type_c = 'MISPLACED'   WHERE type_c = 'MISSPLACED'")

conn.commit()

conn.close()
