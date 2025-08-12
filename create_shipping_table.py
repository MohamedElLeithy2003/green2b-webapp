from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE shipping (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL UNIQUE,
                    address_line1 VARCHAR(255),
                    address_line2 VARCHAR(255),
                    city VARCHAR(100),
                    state VARCHAR(100),
                    zip_code VARCHAR(20),
                    status VARCHAR(50),
                    estimated_delivery DATE,
                    current_location VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES "order"(id)
                );
            """))
            print("Shipping table created successfully.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("Shipping table already exists.")
            else:
                print("Error creating shipping table:", e)