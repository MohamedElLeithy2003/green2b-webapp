from app import app, db
from sqlalchemy import text

columns_to_add = [
    ("is_blocked", "BOOLEAN DEFAULT FALSE")
]

with app.app_context():
    with db.engine.connect() as conn:
        for column_name, column_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE user ADD COLUMN {column_name} {column_type};"))
                print(f"Added column: {column_name}")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"Column '{column_name}' already exists.")
                else:
                    print(f"Error adding '{column_name}':", e)