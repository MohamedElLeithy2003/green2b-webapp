from app import app, db
from sqlalchemy import text

columns_to_add = [
    ("email", "VARCHAR(120)"),
    ("password", "VARCHAR(200)")
]

with app.app_context():
    with db.engine.connect() as conn:
        for column_name, column_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE supplier ADD COLUMN {column_name} {column_type};"))
                print(f"Added column: {column_name}")
            except Exception as e:
                if "duplicate column name" in str(e):
                    print(f"Column '{column_name}' already exists.")
                else:
                    print(f"Error adding '{column_name}':", e)