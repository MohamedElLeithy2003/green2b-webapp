from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("""
            ALTER TABLE order_item
            ADD COLUMN status VARCHAR(50) DEFAULT 'Pending';
        """))
        db.session.commit()
        print("✅ Status column added successfully.")
    except Exception as e:
        print(f"⚠️ Error: {e}")