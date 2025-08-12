from app import app, db
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Rename old table
            conn.execute(text("ALTER TABLE cart RENAME TO cart_old;"))

            # 2. Create new table with correct schema
            conn.execute(text("""
                CREATE TABLE cart (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES user(id)
                );
            """))

            # 3. Copy data from old table to new table
            # Make sure all old carts have non-null user_id before running this
            conn.execute(text("""
                INSERT INTO cart (id, user_id)
                SELECT id, user_id FROM cart_old WHERE user_id IS NOT NULL;
            """))

            # 4. Drop old table
            conn.execute(text("DROP TABLE cart_old;"))

            trans.commit()
            print("Cart table recreated with foreign key constraint and NOT NULL user_id.")
        except Exception as e:
            trans.rollback()
            print("Migration failed:", e)
