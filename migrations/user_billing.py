from app import app, db
from sqlalchemy import text

columns_to_add = [
    ("billing_street", "VARCHAR(255)"),
    ("billing_city", "VARCHAR(100)"),
    ("billing_state", "VARCHAR(100)"),
    ("billing_postcode", "VARCHAR(20)"),
    ("billing_country", "VARCHAR(100)")
]

with app.app_context():
    with db.engine.connect() as conn:
        for column_name, column_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE user ADD COLUMN {column_name} {column_type};"))
                print(f"Added column: {column_name}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column '{column_name}' already exists.")
                else:
                    print(f"Error adding '{column_name}':", e)