import sqlite3

conn = sqlite3.connect(r'C:\Users\moham\OneDrive\Green2B_Website\instance\green2b.db')
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS _alembic_tmp_supplier_application')
conn.commit()
conn.close()
print("Dropped _alembic_tmp_supplier_application if it existed.")