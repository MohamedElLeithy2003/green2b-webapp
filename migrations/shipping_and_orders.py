from app import app, db
from sqlalchemy import text, inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if 'shipping' in tables:
        print("Shipping table already exists.")
    else:
        try:
            # Create shipping table
            db.engine.execute(text('''
                CREATE TABLE shipping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER UNIQUE NOT NULL,
                    status VARCHAR(50),
                    tracking_number VARCHAR(100),
                    estimated_delivery VARCHAR(100),
                    shipping_address TEXT,
                    FOREIGN KEY(order_id) REFERENCES "order"(id)
                );
            '''))
            print("Shipping table created successfully.")
        except Exception as e:
            print("Error creating shipping table:", e)

    # Check if columns exist, add if missing (optional)
    columns_to_add = [
        ("status", "VARCHAR(50)"),
        ("tracking_number", "VARCHAR(100)"),
        ("estimated_delivery", "VARCHAR(100)"),
        ("shipping_address", "TEXT")
    ]

    # Only try to add columns if table exists
    if 'shipping' in tables:
        existing_columns = [col['name'] for col in inspector.get_columns('shipping')]
        with db.engine.connect() as conn:
            for column_name, column_type in columns_to_add:
                if column_name not in existing_columns:
                    try:
                        conn.execute(text(f"ALTER TABLE shipping ADD COLUMN {column_name} {column_type};"))
                        print(f"Added column: {column_name}")
                    except Exception as e:
                        print(f"Error adding column {column_name}:", e)
                else:
                    print(f"Column '{column_name}' already exists.")