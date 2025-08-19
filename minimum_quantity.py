from app import app, db
from sqlalchemy import text, inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if 'product' in tables:
        print("Products table exists.")
    else:
        print("Products table does not exist. Cannot add column.")
        exit()

    # Column we want to ensure exists
    column_name = "minimum_quantity"
    column_type = "INTEGER DEFAULT 1"

    existing_columns = [col['name'] for col in inspector.get_columns('product')]

    if column_name not in existing_columns:
        try:
            with db.engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE product ADD COLUMN {column_name} {column_type};"))
                print(f"Column '{column_name}' added successfully.")
        except Exception as e:
            print(f"Error adding column '{column_name}':", e)
    else:
        print(f"Column '{column_name}' already exists.")