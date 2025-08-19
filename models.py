from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))  # Keep password hash here only
    role = db.Column(db.String(50), default='buyer')  # 'buyer' or 'supplier'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    supplier = db.relationship('Supplier', backref='user', uselist=False)
    cart = db.relationship('Cart', backref='buyer', uselist=False)
    orders = db.relationship('Order', backref='buyer', lazy=True)

    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    address_street = db.Column(db.String(255), nullable=True)
    address_city = db.Column(db.String(100), nullable=True)
    address_state = db.Column(db.String(100), nullable=True)
    address_postcode = db.Column(db.String(20), nullable=True)
    address_country = db.Column(db.String(100), nullable=True)

    billing_street = db.Column(db.String(255), nullable=True)
    billing_city = db.Column(db.String(100), nullable=True)
    billing_state = db.Column(db.String(100), nullable=True)
    billing_postcode = db.Column(db.String(20), nullable=True)
    billing_country = db.Column(db.String(100), nullable=True)

    is_blocked = db.Column(db.Boolean, default=False)



    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class EmailSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Supplier(db.Model):
    __tablename__ = 'supplier'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Fix here
    email = db.Column(db.String(120), unique=True, nullable=False)
    company_name = db.Column(db.String(120))
    verified = db.Column(db.Boolean, default=False)
    sustainability_score = db.Column(db.Float)

    products = db.relationship('Product', backref='supplier', lazy=True)
    views = db.relationship('ProductView', back_populates='supplier', cascade='all, delete-orphan')

    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

class SupplierApplication(db.Model):
    __tablename__ = 'supplier_application'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # This column should reference User.id with a ForeignKey!
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship back to User
    user = db.relationship('User', backref='supplier_applications')
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    website = db.Column(db.String(200))
    products = db.Column(db.String(300))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProductView(db.Model):
    __tablename__ = 'product_views'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)

    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship('Product', back_populates='views')
    supplier = db.relationship('Supplier', back_populates='views')


class Product(db.Model):

    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(80))
    description = db.Column(db.Text)
    impact = db.Column(db.Text)
    status = db.Column(db.String(50))
    image_url = db.Column(db.String(255))
    minimum_quantity = db.Column(db.Integer, default=1)

    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    views = db.relationship('ProductView', back_populates='product', cascade='all, delete-orphan')

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('CartItem', backref='cart', cascade="all, delete-orphan")

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(255))
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    quantity = db.Column(db.Integer, default=1)


class Shipping(db.Model):
    __tablename__ = 'shipping'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), unique=True, nullable=False)
    status = db.Column(db.String(50))
    estimated_delivery = db.Column(db.Date)
    current_location = db.Column(db.String(100))

    recipient_name = db.Column(db.String(100))
    street = db.Column(db.String(100))
    city = db.Column(db.String(100))
    postcode = db.Column(db.String(20))
    country = db.Column(db.String(100))

    order = db.relationship('Order', back_populates='shipping')
    

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum('pending', 'shipped', 'delivered', 'Completed', name='order_status'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shipping = db.relationship('Shipping', back_populates='order')
    items = db.relationship('OrderItem', backref='order', lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default="Pending")
    
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

