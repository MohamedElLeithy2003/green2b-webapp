from app import app, db
from models import Supplier  # Replace with your actual model import

with app.app_context():
    # Create a test supplier or query an existing one
    supplier = Supplier.query.first()  # or create new Supplier(...)
    if supplier:
        supplier.reset_token = 'test-token'
        from datetime import datetime, timedelta
        supplier.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        print("Reset token fields updated successfully!")
    else:
        print("No supplier found to test.")