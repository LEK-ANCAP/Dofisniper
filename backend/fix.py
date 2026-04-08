import sqlite3

conn = sqlite3.connect('dofimall_sniper.db')
cursor = conn.cursor()
cursor.execute("UPDATE products SET status = 'monitoring' WHERE status NOT IN ('monitoring', 'paused')")
conn.commit()
conn.close()
print("Fixed db")
