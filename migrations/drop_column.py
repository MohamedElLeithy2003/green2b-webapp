from app import app, db
from sqlalchemy import text, inspect

with app.app_context():
    inspector = inspect(db.engine)

    # Check if 'password' column exists in 'supplier' table
    columns = [col['name'] for col in inspector.get_columns('supplier')]
    if 'password' in columns:
        with db.engine.connect() as conn:
            try:
                conn.execute(text('ALTER TABLE supplier DROP COLUMN password;'))
                print("Dropped 'password' column from 'supplier' table.")
            except Exception as e:
                print("Error dropping 'password' column:", e)
    else:
        print("'password' column does not exist in 'supplier' table, nothing to drop.")