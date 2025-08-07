
from app import app, db
from sqlalchemy import text

with app.app_context():
    db.session.execute(text('ALTER TABLE supplier ADD COLUMN reset_token VARCHAR(100);'))
    db.session.execute(text('ALTER TABLE supplier ADD COLUMN reset_token_expiry DATETIME;'))
    db.session.commit()

    print("Columns added successfully.")