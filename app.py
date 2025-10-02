import stripe
import openai
import os
import re
import secrets
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify, current_app
from flask_mail import Mail, Message
from flask_login import current_user, LoginManager, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from models import db, Product, User, Cart, CartItem, Order, OrderItem, SupplierApplication, Supplier, ProductView
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Optional
from datetime import date, datetime, timedelta
from threading import Thread
from sqlalchemy import func, cast, Date
from sqlalchemy.sql import func, expression
from types import SimpleNamespace
from dotenv import load_dotenv
from dotenv import load_dotenv
from sqlalchemy import func


load_dotenv()

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
migrate = Migrate(app, db)
profile_bp = Blueprint('profile', __name__)
orders_bp = Blueprint('orders', __name__, url_prefix='/orders')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
app.secret_key = "d11c57a2dde5240c1ba0a1bd96be6fdc979173696d613bb44342ea520a3e6379"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "green2bteam@gmail.com"
app.config['MAIL_PASSWORD'] = "ejtt rttq poqc krge"
app.config['MAIL_DEFAULT_SENDER'] = ('Green2B', 'green2bteam@gmail.com')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///green2b.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

mail = Mail(app)

db.init_app(app)
with app.app_context():
    db.create_all()
    
stripe.api_key = "sk_test_51O8jQdE43TmUArKlFz7rQnZI4yeZ9iVsoImn0Bs2wI5Bx8PqufupGZ8KZBYB00jy6h8qlI0s8hoiD1z2UOJcUPBy00CHFoTpGp"

subscribers = []

ADMIN_USERNAME = "adminuser"
ADMIN_PASSWORD = "supersecretpassword"

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, body, html=None):
    recipients = [r for r in recipients if r]
    if not recipients:
        print("No valid email recipients provided, email not sent.")
        return
    msg = Message(subject, recipients=recipients)
    msg.body = body
    if html:
        msg.html = body
    mail.send(msg)

def is_valid_input(text):
    if not text:
        return False
    if re.search(r'https?://', text):
        return False
    if re.search(r'[^\w\s.,!?@\-]', text):
        return False
    return True



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')


@admin_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')

    return render_template('admin_login.html')  # GET request


@admin_bp.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    return render_template('admin_dashboard.html')


@admin_bp.route('/products/pending')
def pending_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    pending_products = Product.query.filter_by(status='pending').all()
    return render_template('pending_products.html', products=pending_products)

@admin_bp.route('/products/<int:product_id>/approve', methods=['POST'])
def approve_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    product = Product.query.get_or_404(product_id)

    # Ensure the product has a valid supplier
    supplier = product.supplier
    if not supplier:
        flash(f'Cannot approve product "{product.name}": supplier not found.', 'danger')
        return redirect(url_for('admin.pending_products'))

    # Approve the product
    product.status = 'approved'
    db.session.commit()

    # Send email
    try:
        subject = f"{product.name} has been approved"
        recipient = supplier.user.email
        body = f"""Hello {supplier.company_name},

Your product "{product.name}" has been approved and is now live on the marketplace.

Thank you for partnering with us.

Best regards,
Green2B Team
"""
        msg = Message(subject=subject, recipients=[recipient], body=body)
        mail.send(msg)
        flash(f'Product "{product.name}" approved and supplier notified.', 'success')
    except Exception as e:
        print(str(e))
        flash("Error sending email to supplier.", 'danger')

    return redirect(url_for('admin.pending_products'))

@admin_bp.route('/products/<int:product_id>/reject', methods=['POST'])
def reject_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    product = Product.query.get_or_404(product_id)
    product.status = 'rejected'
    db.session.commit()
    flash(f'Product {product.name} rejected successfully.', 'warning')
    return redirect(url_for('admin.pending_products'))


@admin_bp.route('/products')
def admin_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    all_products = Product.query.all()

    return render_template('admin_products.html', products=all_products)


@admin_bp.route('/products/<product_id>', methods=['GET', 'POST'])
def admin_product_detail(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    # Check if this is a dummy product (starts with 'd')
    if str(product_id).startswith('d'):
        try:
            dummy_id = int(product_id[1:])
        except ValueError:
            abort(404)
        from types import SimpleNamespace
        product_data = next((p for idx, p in enumerate(products_data, start=10000) if idx == dummy_id), None)
        if not product_data:
            abort(404)
        product = SimpleNamespace(**product_data)
        return render_template('admin_product_detail.html', product=product, is_dummy=True)

    # Otherwise, treat it as a DB product ID
    try:
        pid = int(product_id)
    except ValueError:
        abort(404)

    product = Product.query.get(pid)
    if not product:
        abort(404)

    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.image_url = request.form['image_url']
        product.category = request.form['category']
        db.session.commit()
        flash('Product updated successfully')
        return redirect(url_for('admin.admin_products'))

    return render_template('admin_product_detail.html', product=product, is_dummy=False)


@admin_bp.route('/products/<int:product_id>/request-change', methods=['POST'])
def request_change(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    product = Product.query.get_or_404(product_id)
    change_note = request.form.get('change_note')

    supplier = product.supplier
    if not supplier or not supplier.user:
        flash("Supplier not found for this product.", "danger")
        return redirect(url_for('admin.admin_products', product_id=product_id))

    subject = f"Change Request for Your Product: {product.name}"
    recipient = supplier.user.email
    body = f"""Hello {supplier.company_name},

Your product "{product.name}" requires some changes.

Requested Change:
{change_note}

Please make the necessary updates in your supplier dashboard.

Regards,
Green2B Admin Team
"""
    try:
        msg = Message(subject=subject, recipients=[recipient], body=body)
        mail.send(msg)
        flash(f'Requested changes for "{product.name}": {change_note}, info')
    except Exception as e:
        print(str(e))
        flash("Error sending email to supplier", 'danger')
    return redirect(url_for('admin.admin_products', product_id=product_id))

@admin_bp.route('/products/<int:product_id>/remove', methods=['POST'])
def remove_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'Product {product.name} has been deleted', 'danger')
    return redirect(url_for('admin.admin_products'))

@admin_bp.route('/users')
def admin_users():
    users = User.query.filter_by(role='buyer').all()
    return render_template('admin_users.html', users=users)

@admin_bp.route('/users/<int:user_id>/activity')
def user_activity(user_id):
    user = User.query.get_or_404(user_id)
    orders = user.orders  # example
    return render_template('admin_user_activity.html', user=user, orders=orders)

@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
def block_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = True
    db.session.commit()
    flash(f"{user.email} has been blocked.")
    return redirect(url_for('admin_bp.user_activity', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
def unblock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = False
    db.session.commit()
    flash(f"{user.email} has been unblocked.")
    return redirect(url_for('admin_bp.user_activity', user_id=user_id))

@admin_bp.route('/orders/')
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@admin_bp.route('/orders/<int:order_id>')
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin_order_detail.html', order=order)

@admin_bp.route('/suppliers/')
def admin_suppliers():
    suppliers = Supplier.query.filter_by(verified=True).all()
    return render_template('admin_suppliers.html', suppliers=suppliers)

@admin_bp.route('/suppliers/<int:supplier_id>/activity')
def supplier_activity(supplier_id):
    supplier = Supplier.query.filter_by(id=supplier_id, verified=True).first_or_404()
    products = supplier.products
    orders = supplier.orders if hasattr(supplier, 'orders') else[]
    return render_template('admin_supplier_activity.html', supplier=supplier, products=products, orders=orders)

@admin_bp.route('/suppliers/<int:supplier_id>/block', methods=['POST'])
def block_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier.is_blocked = True
    db.session.commit()
    flash(f"{supplier.company_name} has been blocked.", "warning")
    return redirect(url_for('admin.admin_suppliers'))

@admin_bp.route('/suppliers/<int:supplier_id>/unblock', methods=['POST'])
def unblock_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier.is_blocked = False
    db.session.commit()
    flash(f"{supplier.company_name} has been unblocked.", "success")
    return redirect(url_for('admin.admin_suppliers'))

@admin_bp.route('/supplier-applications')
def supplier_applications():
    applications = SupplierApplication.query.order_by(SupplierApplication.created_at.desc()).all()
    return render_template('supplier_applications.html', applications=applications)

@admin_bp.route('/supplier-approve/<int:app_id>', methods=['POST'])
def supplier_approve(app_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    application = SupplierApplication.query.get_or_404(app_id)
    user = User.query.get(application.user_id)
    if not user:
        flash(f'No user found for application #{application.id}', 'danger')
        return redirect(url_for('admin.supplier_applications'))

    # Approve application
    application.status = 'Approved'

    # Update supplier record
    supplier = Supplier.query.filter_by(user_id=user.id).first()
    if supplier:
        supplier.verified = True
    else:
        supplier = Supplier(
            user_id=user.id,
            company_name=application.company,
            verified=True
        )
        db.session.add(supplier)

    db.session.commit()

    # Send approval email

    try:
        login_url = url_for('supplier_login', _external=True)
        msg = Message(
            "Supplier Application Approved",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.email]
        )
        msg.body = f"""Hi {user.name},

Your supplier application has been approved. Welcome aboard!

You can log in here: {login_url}

Best regards,
The Green2B Team
"""
        mail.send(msg)
    except Exception as e:
        print(str(e))
        flash("Error sending supplier approval email.", 'danger')

    flash('Supplier application approved successfully.', 'success')
    return redirect(url_for('admin.supplier_applications'))

@admin_bp.route('/supplier-reject/<int:app_id>', methods=['POST'])
def supplier_reject(app_id):
    application = SupplierApplication.query.get_or_404(app_id)
    application.status = 'Rejected'
    db.session.commit()

    # Send rejection email
    try:
        if application.user and application.user.email:
            subject = "Your Supplier Application Has Been Rejected"
            recipient = application.user.email
            body = f"""Hello {application.company},

We regret to inform you that your supplier application has been rejected after review.

If you believe this was a mistake or would like to reapply in the future, feel free to reach out to us.

Regards,  
Green2B Admin Team
"""
            msg = Message(subject=subject, recipients=[recipient], body=body)
            mail.send(msg)
            flash(f'Supplier application #{application.id} rejected and email sent.', 'warning')
        else:
            flash(f'Supplier application #{application.id} rejected (email not sent: user missing)', 'warning')
    except Exception as e:
        print(str(e))
        flash("Error sending rejection email to supplier", 'danger')

    return redirect(url_for('admin.supplier_applications'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        address_street = request.form.get('address_street', '')
        address_city = request.form.get('address_city', '')
        address_state = request.form.get('address_state', '')
        address_postcode = request.form.get('address_postcode', '')
        address_country = request.form.get('address_country', '')

        billing_street = request.form.get('billing_street', '')
        billing_city = request.form.get('billing_city', '')
        billing_state = request.form.get('billing_state', '')
        billing_postcode = request.form.get('billing_postcode', '')
        billing_country = request.form.get('billing_country', '')

        if not is_valid_input(name):
            flash('Name contains invalid characters on links', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        new_user = User(name=name, email=email, role=role, address_street=address_street,
            address_city=address_city,
            address_state=address_state,
            address_postcode=address_postcode,
            address_country=address_country,
            billing_street=billing_street,
            billing_city=billing_city,
            billing_state=billing_state,
            billing_postcode=billing_postcode,
            billing_country=billing_country,
            )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        subject = "Welcome to Green2B"
        body = f"Hello {name},\n\nThank you for registering on Green2B. Your account has been created successfully.\n\nBest regards,\nGreen2B Team"
        send_email(subject, [email], body)

        flash('Registration successful. You can now login')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@profile_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])

    if not user or user.role != 'buyer':
        return redirect(url_for('home'))

    return render_template('profile.html', user=user)


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('New Password', validators=[Optional()])

    address_street = StringField('Shipping Street', validators=[Optional()])
    address_city = StringField('Shipping City', validators=[Optional()])
    address_state = StringField('Shipping State', validators=[Optional()])
    address_postcode = StringField('Shipping Postcode', validators=[Optional()])
    address_country = StringField('Shipping Country', validators=[Optional()])

    billing_street = StringField('Billing Street', validators=[Optional()])
    billing_city = StringField('Billing City', validators=[Optional()])
    billing_state = StringField('Billing State', validators=[Optional()])
    billing_postcode = StringField('Billing Postcode', validators=[Optional()])
    billing_country = StringField('Billing Country', validators=[Optional()])

@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'buyer':
        return redirect(url_for('home'))

    form = EditProfileForm()

    if form.validate_on_submit():
        user.name = form.username.data
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)

        user.address_street = form.address_street.data
        user.address_city = form.address_city.data
        user.address_state = form.address_state.data
        user.address_postcode = form.address_postcode.data
        user.address_country = form.address_country.data
        
        user.billing_street = form.billing_street.data
        user.billing_city = form.billing_city.data
        user.billing_state = form.billing_state.data
        user.billing_postcode = form.billing_postcode.data
        user.billing_country = form.billing_country.data
        
        try:
            db.session.commit()
            flash('Profile updated successfully.')
            return redirect(url_for('profile.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile.')

    if request.method == 'GET':
        form.username.data = user.name
        form.email.data = user.email

        form.address_street.data = user.address_street
        form.address_city.data = user.address_city
        form.address_state.data = user.address_state
        form.address_postcode.data = user.address_postcode
        form.address_country.data = user.address_country

        form.billing_street.data = user.billing_street
        form.billing_city.data = user.billing_city
        form.billing_state.data = user.billing_state
        form.billing_postcode.data = user.billing_postcode
        form.billing_country.data = user.billing_country

    return render_template('edit_profile.html', form=form, user=user)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            
            if user.role == 'supplier':
                return redirect(url_for('supplier_products'))
            else:
                return redirect(url_for('home'))

        flash('Invalid credentials')
    return render_template('auth/login.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(16)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            reset_link = url_for('reset_password', token=token, _external=True)
            subject = "Password Reset Request"
            body = f"Click the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
            send_email(subject, [email], body)

            flash('Password reset link sent to your email.')
            return redirect(url_for('login'))
        else:
            flash('Email not found')
            return redirect(url_for('forgot_password'))
    return render_template('auth/forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired token')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        subject = "Your password has been reset"
        body = f"""
        Hi {user.name}, your password has been reset due to a password reset request. If you did not make this change, contact us immediately.

        Thank you,
        Green2B Team
        """
        send_email(subject, [user.email], body)
        flash('Password reset successfully. You can now login.')
        return redirect(url_for('login'))

    return render_template('auth/reset_password.html', token=token)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('home'))


@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email')
    if not email:
        flash("Please enter a valid email address.")
        return redirect(url_for('home'))
    
    if email in subscribers:
        flash("You are already subscribed")
        return redirect(url_for('home'))
    
    subscribers.append(email)
    flash("Thank you for subscribing!")
    msg = Message("Thank you for subscribing to Green2B", recipients=[email])
    msg.html = f"""
        <html>
        <body>
            <p>Hello,</p>
            <p>Thank you for subscribing to Green2B! We will keep you updated with our latest products and sustainability initiatives.</p>
            <hr>
            <footer>
            <img src="cid:green2b_logo" alt="Green2B Logo" width="150">
            <p>Green2B - Connecting sustainable suppliers with businesses</p>
            </footer>
        </body>
        </html>
        """

    with app.open_resource("static/images/green2b_new.png") as img:
            msg.attach(
                "green2b_new.png",
                "image/png",
                img.read(),
                'inline',
                headers={"Content-ID": "<green2b_logo>"}
            )

    mail.send(msg)

    return redirect(url_for('home'))


@orders_bp.route('/')
def orders_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    orders = Order.query.filter(Order.buyer_id == user.id).order_by(Order.created_at.desc()).all()

    return render_template('orders.html', orders=orders)

@orders_bp.route('/<int:order_id>')
def order_detail(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = Order.query.get(order_id)
    if not order or (order.buyer_id != session.get('user_id') and order.email != session.get('user_email')):
        return redirect(url_for('orders.orders_list'))

    order_items = OrderItem.query.filter_by(order_id=order.id).all()

    return render_template('order_detail.html', order=order, order_items=order_items)


@orders_bp.route('/<int:order_id>/track')
def track_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    order = Order.query.get(order_id)
    if not order or order.buyer_id != session['user_id']:
        return redirect(url_for('order.orders_list'))

    tracking_info = None
    if order.shipping:
        tracking_info = {
            'status': order.shipping.status,
            'estimated_delivery': order.shipping.estimated_delivery.strftime('%B %d, %Y'),
            'current_location': order.shipping.current_location,
            'shipping_address': {
                'name': order.shipping.recipient_name,
                'street': order.shipping.street,
                'city': order.shipping.city,
                'postcode': order.shipping.postcode,
                'country': order.shipping.country
            }
        }  # <-- This closing brace was missing
    else:
        tracking_info = {
            'status': 'Processing',
            'estimated_delivery': 'TBD',
            'current_location': 'Warehouse',
            'shipping_address': {
                'name': order.buyer.name,
                'street': order.buyer.address_street or 'Not Provided',
                'city': order.buyer.address_city or '',
                'postcode': order.buyer.address_postcode or '',
                'country': order.buyer.address_country or ''
            }
        }

    return render_template('track_order.html', order=order, order_id=order.id, tracking_info=tracking_info)



@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/about/overview')
def about_overview():
    return render_template('about_overview.html')



@app.route('/about/challenges-and-solutions')
def about_challenges_and_solutions():
    return render_template('about_challenges_and_solutions.html')

@app.route('/about/stakeholders')
def about_stakeholders():
    return render_template('about_stakeholders.html')

@app.route('/about/team')
def about_team():
    return render_template('about_team.html')



products_data = [
    {
        'id': 10000,
        'supplier': 'Smaart Rice Straw',
        'name': 'Rice Starch Straw',
        'image': 'images/starch_straw.png',
        'category': 'ecofriendly',
        'quantity': 50000,
        'minimum_quantity': 500,
        'price': 0.017,
        'score': "95/100",
        'description': "Made from food-grade rice & tapioca starch, holds strong in cold drinks, resists for 45+ minutes, 100% biodegradable and compostable, odourless, tasteless, and chemical-free"
    },
    {
        'id': 10001,
        'supplier': 'GreenR by BioMandi',
        'name': 'Paper made out of Cigarette Buds',
        'image': 'images/greenR_paper.png',
        'category': 'recycled',
        'quantity': 100000,
        'minimum_quantity:': 2,
        'price': 4.70,
        'score': "85/100",
        'description': "75 GSM A4-size paper made from 8000 cigarette butts, repurposed waste into usable stationary"
    },
    {
        'id': 10002,
        'supplier': 'Mesrii Private Limited',
        'name': 'Business Gift Hamper',
        'image': 'images/Gift Hamper .jpeg.jpg',
        'category': 'organic',
        'quantity': 1000000,
        'minimum_quantity': 10,
        'price': 10.00,
        'score': "90/100",
        'description': "Includes Cork Diary, Mug, Card Holder, Pen, and Keychain – all sustainably made from cork"
    },
    {
        'id': 10003,
        'supplier': 'GreenR by BioMandi',
        'name': 'Jute Folder',
        'image': 'images/Jute Folder .jpeg.jpg',
        'category': 'organic',
        'quantity': 100000,
        'minimum_quantity': 100,
        'price': 0.8,
        'score': "80/100",
        'description': "Made from natural jute, biodegradable and reusable alternative to plastic folders"
    },
    {
        'id': 10004,
        'supplier': 'Mesrii Private Limited',
        'name': 'Bamboo Bottle and 2 Mugs',
        'image': 'images/bamboo_bottle_mugs.png',
        'category': 'organic',
        'quantity': 100000,
        'minimum_quantity': 10,
        'price': 10.00,
        'score': "85/100",
        'description': "Natural color bottle and mugs crafted from sustainable bamboo"
    },
    {
        'id': 10005,
        'supplier': 'Note',
        'name': 'Plantable Pens',
        'image': 'images/plantable_pen.jpeg',
        'category': 'recycled',
        'quantity': 10000,
        'minimum_quantity': 100,
        'price': 0.1,
        'description': "100% recyclable"
    },
    {
        'id': 10006,
        'supplier': 'Note',
        'name': 'Bamboo Pens',
        'image': 'images/bamboo_pen.jpeg',
        'category': 'organic',
        'quantity': 10000,
        'minimum_quantity': 100,
        'price': 0.4,
        'description': "Pens made out of bamboo"
    }
]

@app.route('/products')
def products():
    query = request.args.get('q', '').lower()
    filter_category = request.args.get('category', '').lower()
    filter_impact = request.args.get('impact', '').lower()

    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    try:
        min_price = float(min_price) if min_price else None
    except ValueError:
        min_price = None
    
    try:
        max_price = float(max_price) if max_price else None
    except ValueError:
        max_price = None

    # Fetch approved products from DB
    db_products = Product.query.filter_by(status='approved').all()

    db_products_list = []
    for p in db_products:
        db_products_list.append({
            'id': p.id,
            'supplier': p.supplier.id if p.supplier else "Unknown",  # assuming relationship .supplier.name
            'name': p.name or "",
            'image': p.image_url or 'default_image.png',
            'category': (p.category or "").lower(),
            'quantity': getattr(p, 'quantity', 100),
            'price': float(p.price) if p.price else 0,
            'score': getattr(p, 'score', 'N/A'),
            'description': p.description or "",
            'impact': (p.impact or "").lower(),
            'is_dummy': False
        })

    # Add impact key to dummy products and give them unique IDs
    dummy_products = []
    start_id = 10000
    for idx, p in enumerate(products_data, start=start_id):
        p_copy = p.copy()
        if 'impact' not in p_copy:
            p_copy['impact'] = ''
        p_copy['category'] = p_copy.get('category', '').lower()
        p_copy['impact'] = p_copy.get('impact', '').lower()
        p_copy['id'] = idx  # Assign unique high ID to avoid DB conflicts
        p_copy['is_dummy'] = True
        dummy_products.append(p_copy)

    all_products = dummy_products + db_products_list

    # Filter by search query in name or score
    if query:
        all_products = [
            p for p in all_products
            if query in p.get('name', '').lower() or query in p.get('score', '').lower()
        ]

    # Filter by category
    if filter_category:
        all_products = [
            p for p in all_products
            if p.get('category', '') == filter_category
        ]

    # Filter by impact substring
    if filter_impact:
        all_products = [
            p for p in all_products
            if filter_impact in p.get('impact', '')
        ]

    # Filter by min_price
    if min_price is not None:
        all_products = [
            p for p in all_products
            if p.get('price') is not None and p['price'] >= min_price
        ]

    # Filter by max_price
    if max_price is not None:
        all_products = [
            p for p in all_products
            if p.get('price') is not None and p['price'] <= max_price
        ]

    return render_template(
        'products.html',
        products=all_products,
        query=query,
        filter_category=filter_category,
        filter_impact=filter_impact,
        min_price=min_price,
        max_price=max_price
    )


@app.route('/products/<int:product_id>')
def product_detail(product_id):
    # First try the database product:
    product_db = Product.query.filter_by(id=product_id, status='approved').first()
    if product_db:
        # Track the view (assuming you have a supplier_id)
        new_view = ProductView(
            product_id=product_db.id,
            supplier_id=current_user.id  # or some supplier/user id
        )
        db.session.add(new_view)
        db.session.commit()

        return render_template('product_details.html', product=product_db, is_dummy=False)


    # If not found in DB, try dummy data fallback:
    product = next((p for p in products_data if p['id'] == product_id), None)
    if product:
        return render_template('product_details.html', product=product, is_dummy=True)

    # Not found anywhere:
    return "Product not found", 404

collections_list = [
    {
        'name': 'Eco-Friendly',
        'slug': 'ecofriendly',
        'products': [p for p in products_data if p['category'] == 'ecofriendly'],
        'cover_image': 'images/eco-friendly-removebg-preview.png',
        'product_count': sum(1 for p in products_data if p['category'] == 'ecofriendly')
    },
    {
        'name': 'Organic',
        'slug': 'organic',
        'products': [p for p in products_data if p['category'] == 'organic'],
        'cover_image': 'images/organic_new.png',
        'product_count': sum(1 for p in products_data if p['category'] == 'organic')
    }
    ,
    {
        'name': 'Recycled',
        'slug': 'recycled',
        'products': [p for p in products_data if p['category'] == 'recycled'],
        'cover_image': 'images/recycled-removebg-preview.png',
        'product_count': sum(1 for p in products_data if p['category'] == 'recycled')
    }
]
@app.route('/collections')
def collections():
    collections = {}

    for product in products_data:
        category = product['category']
        if category not in collections:
            collections[category] = []
        collections[category].append(product)

    collection_covers = {
        'ecofriendly': 'images/eco-friendly-removebg-preview.png',
        'organic': 'images/organic-removebg-preview.png',
        'recycled': 'images/recycled-removebg-preview.png'
    }

    collections_list = []
    for cat, prods in collections.items():
        collections_list.append({
            'name': cat.capitalize(),
            'slug': cat,
            'products': prods,
            'cover_image': collection_covers.get(cat, 'images/default_collection.jpg'),
            'product_count': len(prods)
        })

    return render_template('collections.html', collections=collections_list)

@app.route('/collections/<category_name>')
def collection_page(category_name):
    category = category_name.lower()
    filtered_products = [
        p for p in products_data
        if p['category'].lower() == category
    ]

    collection_covers = {
        'ecofriendly': 'images/eco-friendly-removebg-preview.png',
        'organic': 'images/organic-removebg-preview.png',
        'recycled': 'images/recycled-removebg-preview.png'
    }

    cover_image = collection_covers.get(category, 'images/default_collection.jpg')

    if not filtered_products:
        return "Collection not found", 404
    
    return render_template('collection_page.html', products=filtered_products, category=category, cover_image=cover_image)


@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product_db = Product.query.filter_by(id=product_id, status='approved').first()
    
    if product_db:
        product = {
            'id': product_db.id,
            'name': product_db.name or "",
            'price': float(product_db.price or 0)
        }
    else:
        product = next((p for p in products_data if p['id'] == product_id), None)
        if product:
            product['price'] = float(product['price'] or 0)

    if not product:
        flash("Product not found")
        return redirect(url_for('products'))

    try:
        quantity = max(1, int(request.form.get('quantity', 1)))
    except ValueError:
        quantity = 1

    if current_user.is_authenticated:
        if not current_user.cart:
            new_cart = Cart(user_id=current_user.id)
            db.session.add(new_cart)
            db.session.commit()
            current_user.cart = new_cart

        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product['id']).first()
        if item:
            item.quantity += quantity
        else:
            item = CartItem(
                user_id=current_user.id,
                cart_id=current_user.cart.id,
                product_id=product['id'],
                product_name=product['name'],
                price=product['price'],
                quantity=quantity
            )
            db.session.add(item)
        db.session.commit()
    else:
        cart = session.get('cart', [])
        for item in cart:
            if item['id'] == product['id']:
                item['quantity'] += quantity
                break
        else:
            cart.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity
            })
        session['cart'] = cart
        session.modified = True

    flash("Added to cart")
    return redirect(url_for('products'))


# View cart
@app.route('/cart')
def cart():
    cart_items = []

    if current_user.is_authenticated:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        for i in items:
            cart_items.append({
                'id': i.product_id,
                'name': i.product_name,
                'price': float(i.price),
                'quantity': i.quantity,
                'subtotal': float(i.price) * i.quantity,
                'image_url': getattr(i, 'image_url', '/static/images/default.jpg')
            })
    else:
        for item in session.get('cart', []):
            price = float(item['price'])
            quantity = int(item.get('quantity', 1))
            cart_items.append({
                'id': item['id'],
                'name': item['name'],
                'price': price,
                'quantity': quantity,
                'subtotal': price * quantity,
                'image_url': item.get('image_url', '/static/images/default.jpg')
            })

    total = sum(item['subtotal'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)


# Update cart quantity
@app.route('/update-cart-quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    try:
        new_quantity = max(1, int(request.form.get('quantity', 1)))
    except ValueError:
        new_quantity = 1

    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if item:
            item.quantity = new_quantity
            db.session.commit()
            flash(f"Updated quantity for {item.product_name}")
        else:
            flash("Item not found in your cart")
    else:
        cart = session.get('cart', [])
        for item in cart:
            if item['id'] == product_id:
                item['quantity'] = new_quantity
                break
        session['cart'] = cart
        session.modified = True
        flash("Updated quantity in your cart")

    return redirect(url_for('cart'))


# Remove from cart
@app.route('/remove-from-cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            flash("Item removed from cart")
        else:
            flash("Item not found in cart")
    else:
        cart = session.get('cart', [])
        session['cart'] = [item for item in cart if item['id'] != product_id]
        session.modified = True
        flash("Item removed from cart")

    return redirect(url_for('cart'))


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    # Determine cart items based on user authentication
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart = [{
            'id': item.product_id,
            'name': item.product_name,
            'price': float(item.price),
            'quantity': item.quantity
        } for item in cart_items]
    else:
        cart = session.get('cart', [])

    if not cart:
        flash("Cart is empty")
        return redirect(url_for('products'))

    # Save temp order for later use
    session['temp_order'] = cart.copy()

    # Create Stripe checkout session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'gbp',
                'product_data': {'name': item['name']},
                'unit_amount': int(item['price'] * 100),
            },
            'quantity': item['quantity'],
        } for item in cart],
        mode='payment',
        success_url=url_for('checkout_success', _external=True),
        cancel_url=url_for('cart', _external=True),
    )
    return redirect(checkout_session.url, code=303)


# Checkout success
@app.route('/checkout-success')
def checkout_success():
    cart = session.get('temp_order', [])
    buyer_info = session.get('buyer_info', {})

    if not cart:
        flash("Cart is empty")
        return redirect(url_for('products'))

    total = sum(float(item['price']) * int(item.get('quantity', 1)) for item in cart)
    buyer_email = buyer_info.get('email')

    # create the order
    new_order = Order(
        buyer_id=session.get('user_id'),
        email=buyer_email,
        total_price=total,
        status='Completed'
    )
    db.session.add(new_order)
    db.session.commit()

    # create order items
    for item in cart:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item['id'],  # assuming cart item has product ID
            quantity=int(item.get('quantity', 1)),
            unit_price=float(item['price'])
        )
        db.session.add(order_item)
    db.session.commit()

    # send confirmation email
    subject = "Order Confirmation"
    body = f"Hi {buyer_info.get('name', 'Customer')},\n\nYour order #{new_order.id} for ${total:.2f} was successful.\nItems:\n"
    for item in cart:
        body += f"- {item['name']} x{item.get('quantity', 1)} - ${float(item['price']) * int(item.get('quantity', 1)):.2f}\n"
    body += "\nThank you for shopping with us!\nGreen2B Team"
    send_email(subject, [buyer_email], body)

    admin_email = "green2bteam@gmail.com"
    subject_admin = f"New Order Received: #{new_order.id}"
    body_admin = f"A new order has been placed.\n\nOrder ID: {new_order.id}\nBuyer: {buyer_info.get('name', 'Guest')} ({buyer_email})\nTotal: ${total:.2f}\nItems:\n"
    for item in cart:
        body_admin += f"- {item['name']} x{int(item.get('quantity', 1))} - ${float(item['price']) * int(item.get('quantity', 1)):.2f}\n"
    send_email(subject_admin, [admin_email], body_admin)

    # store last order in session
    session['last_order'] = {'order_id': new_order.id, 'total_price': total, 'items': cart, **buyer_info}

    # clear cart and buyer info
    session.pop('temp_order', None)
    session.pop('buyer_info', None)
    if current_user.is_authenticated:
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

    return render_template('checkout_success.html', order=new_order)



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not all([is_valid_input(name), is_valid_input(message)]):
            flash("Your message contains invalid characters or links.", 'danger')
            return redirect(url_for('contact'))

        flash("Thank you for reaching out! We'll get back to you soon.")

        subject = "New Contact Form Submission"
        body = f"Name: {name}\nEmail: {email}\nMessage: {message}"
        recipients = ['green2bteam@gmail.com']  # your support email

        send_email(subject, recipients, body)

        msg = Message("Contact Form Submission", recipients=[email])
        msg.html = f"""
        <html>
        <body>
            <p>Hello {name},</p>
            <p>Thank you for reaching out to us. We have received your message and will get back to you shortly.</p>
             <p>Best regards,<br>Green2B Team</p>
            <hr>
            <footer>
            <img src="cid:green2b_logo" alt="Green2B Logo" width="150">
            </footer>
        </body>
        </html>
        """

        with app.open_resource("static/images/green2b_new.png") as img:
            msg.attach(
                "green2b_new.png",
                "image/png",
                img.read(),
                'inline',
                headers={"Content-ID": "<green2b_logo>"}
            )

        mail.send(msg)

        flash("Thank you for your message! We'll get back to you soon.")

        return redirect('/contact-success')

    return render_template('contact.html')
@app.route('/contact-success')
def contact_success():
    return render_template('contact_success.html')

@app.route('/supplier/register', methods=['GET', 'POST'])
def supplier_register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        company = request.form.get('company')
        website = request.form.get('website')
        products = request.form.get('products')
        message = request.form.get('message')

        # Check if supplier already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('supplier_register'))

        # Create user account
        user = User(name=name, email=email, role='supplier')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get user.id before commit

        # Create supplier profile (verified=False by default)
        supplier = Supplier(user_id=user.id, company_name=company, verified=False)
        db.session.add(supplier)

        # Create application record
        application = SupplierApplication(
            user_id=user.id,
            name=name,
            email=email,
            company=company,
            website=website,
            products=products,
            message=message,
            status='Pending'
        )
        db.session.add(application)

        db.session.commit()

        # Send admin notification
        subject = "New Supplier Registration"
        body = f"""
        A new supplier has registered:
        Name: {name}
        Company: {company}
        Email: {email}
        Website: {website}
        Products: {products}
        Message: {message}
        """
        send_email(subject, ['green2bteam@gmail.com'], body)

        flash('Registration successful! Please wait for approval.', 'success')
        return redirect(url_for('supplier_success'))

    return render_template('supplier_register.html')

@app.route('/supplier-success')
def supplier_success():
    return render_template('supplier_success.html')


def get_current_supplier_id():
    if not current_user.is_authenticated:
        abort(401, description="User not logged in")
    if current_user.role != 'supplier':
        abort(403, description="Access denied: Not a supplier")

    supplier = Supplier.query.filter_by(user_id=current_user.id).first()
    if not supplier:
        abort(404, description="Supplier not found")

    return supplier.id


@app.route('/supplier_login', methods=['GET', 'POST'])
def supplier_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()  # remove role filter
        if user and user.check_password(password):
            supplier = Supplier.query.filter_by(user_id=user.id).first()
            if supplier:
                if supplier.verified:
                    user.role = 'supplier'  # ensure role is correct
                    db.session.commit()
                    login_user(user)
                    return redirect(url_for('supplier_products'))
                else:
                    # still pending approval
                    flash('Your supplier account is still pending approval.', 'warning')
                    return redirect(url_for('supplier_register'))
        flash('Invalid email or password', 'danger')
    return render_template('supplier_login.html')

@app.route('/supplier/forgot-password', methods=['GET', 'POST'])
def supplier_forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        supplier = Supplier.query.filter_by(email=email).first()
        if supplier:
            token = secrets.token_urlsafe(16)
            supplier.reset_token = token
            supplier.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            reset_link = url_for('supplier_reset_password', token=token, _external=True)
            subject = "Supplier Password Reset Request"
            body = f"Click the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
            send_email(subject, [email], body)

            flash('Password reset link sent to your email')
            return redirect(url_for('supplier_login'))
        else:
            flash('Email not found')
            return redirect(url_for('supplier_forgot_password'))
    return render_template('supplier_forgot_password.html')

@app.route('/supplier/reset_password/<token>', methods=['GET', 'POST'])
def supplier_reset_password(token):
    supplier = Supplier.query.filter_by(reset_token=token).first()
    if not supplier or supplier.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired token')
        return redirect(url_for('supplier_forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        supplier.set_password(new_password)
        supplier.reset_token = None
        supplier.reset_token_expiry = None
        db.session.commit()
        flash('Password reset successfully. You can now login.')
        return redirect(url_for('supplier_login'))

    return render_template('supplier_reset_password.html', token=token)

@app.route('/supplier/logout')
def supplier_logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('supplier_login'))
            

@app.route('/supplier/products')
def supplier_products():
    supplier_id = get_current_supplier_id()
    # Fetch all products for this supplier
    products = Product.query.filter_by(supplier_id=supplier_id).all()
    product_ids = [p.id for p in Product.query.filter_by(supplier_id=supplier_id).all()]

    today = date.today()
    start_date = today - timedelta(days=6)

    # Placeholder analytics
    analytics_data = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')

        orders_for_day = (
            db.session.query(Order)
            .join(OrderItem)
            .filter(
                OrderItem.product_id.in_(product_ids),
                func.date(Order.created_at) == day
            )
            .all()
        )

        orders_count = len(orders_for_day)
        sales_sum = sum(
            float(oi.quantity * oi.unit_price)
            for order in orders_for_day
            for oi in order.items if oi.product_id in product_ids
        )

        analytics_data.append({
            'day': day_str,
            'orders': orders_count,
            'sales': sales_sum,
        })


    return render_template('supplier_products.html', products=products, analytics_data=analytics_data)

@app.route('/supplier/analytics')
def supplier_analytics():
    supplier_id = get_current_supplier_id()

    product_ids = [p.id for p in Product.query.filter_by(supplier_id=supplier_id).all()]
    today = date.today()
    start_date = today - timedelta(days=6)

    analytics_data = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')

        orders_for_day = (
            db.session.query(Order)
            .join(OrderItem)
            .filter(
                OrderItem.product_id.in_(product_ids),
                func.date(Order.created_at) == day
            )
            .all()
        )

        orders_count = len(orders_for_day)
        sales_sum = sum(
            float(oi.quantity * oi.unit_price)
            for order in orders_for_day
            for oi in order.items if oi.product_id in product_ids
        )

        analytics_data.append({
            'day': day_str,
            'orders': orders_count,
            'sales': sales_sum,
        })

    # Top products
    recent_orders_query = (
        db.session.query(Order)
        .join(OrderItem)
        .filter(OrderItem.product_id.in_(product_ids))
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    recent_orders = []
    for order in recent_orders_query:
        order_items = [
            {
                'id': oi.id,
                'order_id': order.id,
                'quantity': oi.quantity,
                'unit_price': oi.unit_price,
                'status': oi.status
            }
            for oi in order.items if oi.product_id in product_ids
        ]
        if order_items:
            recent_orders.append({
                'id': order.id,
                'order_items': order_items,
                'date': order.created_at,
                'status': order.status
            })


    return render_template(
        'supplier_analytics.html',
        analytics_data=analytics_data,
        recent_orders=recent_orders,
        supplier_id=supplier_id
    )

@app.route('/supplier/products/add', methods=['GET', 'POST'])
def add_product():
    supplier_id = get_current_supplier_id()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        description = request.form.get('description')
        impact = request.form.get('impact')
        minimum_quantity = request.form.get('minimum_quantity', 1)

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            upload_folder = os.path.join(app.root_path, 'static/images')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, image_filename)
            image_file.save(image_path)
            image_url = f'images/{image_filename}'
        else:
            image_url = None

        new_product = Product(
            name=name,
            category=category,
            price=price,
            supplier_id=supplier_id,  # Make sure this is the correct ID
            image_url=image_url,
            status='pending',         # Keep pending for admin approval
            description=description,
            impact=impact,
            minimum_quantity=minimum_quantity
        )
        db.session.add(new_product)
        db.session.commit()

        # Flash a confirmation so you instantly know it worked
        flash(f"Product '{new_product.name}' added successfully!", "success")
        return redirect(url_for('supplier_products'))

    return render_template('add_products.html')


@app.route('/supplier/products/<int:product_id>')
def supplier_product_detail(product_id):
    supplier_id = get_current_supplier_id()
    product = Product.query.filter_by(id=product_id, supplier_id=supplier_id).first()
    if not product:
        return "Product not found or access denied", 404

    today = date.today()
    start_date = today - timedelta(days=6)

    views = 10
    orders_count = db.session.query(OrderItem).join(Order).filter(
        OrderItem.product_id == product_id,
        Order.created_at >= start_date
    ).count() or 0

    total_sales = db.session.query(
        db.func.sum(OrderItem.quantity * OrderItem.unit_price)).join(Order).filter(
        OrderItem.product_id == product_id,
        Order.created_at >= start_date
    ).scalar() or 0

    stats = {
        'views': views,
        'orders': orders_count,
        'sales': total_sales
    }

    return render_template('supplier_product_details.html', product=product, stats=stats)


@app.route('/supplier/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    supplier_id = get_current_supplier_id()
    product = Product.query.filter_by(id=product_id, supplier_id=supplier_id).first_or_404()

    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.price = float(request.form['price'])
        product.description = request.form.get('description')
        product.impact = request.form.get('impact')
        image_file = request.files.get('image')
        product.minimum_quantity = int(request.form.get('minimum_quantity', 1)) 
        
        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            upload_folder = os.path.join(app.root_path, 'static/images')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, image_filename)
            image_file.save(image_path)
            product.image_url = f'static/images/{image_filename}'

        db.session.commit()
        flash('Product updated successfully', 'success')
        return redirect(url_for('supplier_products'))
    
    return render_template('edit_product.html', product=product)

@app.route('/supplier/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    supplier_id = get_current_supplier_id()
    product = Product.query.filter_by(id=product_id, supplier_id=supplier_id).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('supplier_products'))


@app.route('/supplier/orders/recent')
def supplier_recent_orders():
    supplier_id = get_current_supplier_id()

    product_ids = [p.id for p in Product.query.filter_by(supplier_id=supplier_id).all()]

    recent_orders_query = (
        db.session.query(Order)
        .join(OrderItem)
        .filter(OrderItem.product_id.in_(product_ids))
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    recent_orders = []
    for order in recent_orders_query:
        order_items = [
            {
                'id': oi.id,
                'order_id': order.id,
                'quantity': oi.quantity,
                'unit_price': oi.unit_price,
                'status': oi.status
            }
            for oi in order.items if oi.product_id in product_ids
        ]
        if order_items:
            recent_orders.append({
                'id': order.id,
                'order_items': order_items,
                'date': order.created_at,
                'status': order.status
            })

    return render_template('supplier_recent_orders.html', recent_orders=recent_orders)


@app.route('/supplier/update-status/<int:item_id>', methods=['POST'])
def update_order_status(item_id):
    new_status = request.form.get('status')

    order_item = OrderItem.query.get_or_404(item_id)
    order_item.status = new_status
    db.session.commit()

    flash("Order status updated!", "success")
    return redirect(url_for('supplier_recent_orders'))


#def ai_sustainability_score(product):

 #   prompt = f"""
  #  Given the product details below, provide a sustainability score from 0 to 100, where higher is more sustainable.

   # Name: {product['name']}
    #Category: {product['category']}
    #Description: {product['description']}
    #Supplier: {product['supplier']}

    #Return only the numeric score.
    #"""

    #try:
     #   response = openai.ChatCompletion.create(
      #      model="gpt-4",
       #     messages=[
        #        {"role": "system", "content": "You are a sustainability expert."},
         #       {"role": "user", "content": prompt}
          #  ]
        #)
        #score = response['choices'][0]['message']['content'].strip()
        #return score
    #except Exception as e:
     #   print(f"AI scoring error: {e}")
      #  return None



def get_faqs():
    return [
        {
            "question": "What is Green2B?",
            "answer": "Green2B is a platform that connects businesses with eco-friendly and sustainable products, helping them meet their environmental goals."
        },
        {
            "question": "How does Green2B ensure product sustainability?",
            "answer": "We vet our suppliers and products to ensure they meet strict sustainability criteria, including low carbon footprint, recyclable materials, and ethical sourcing."
        },
        {
            "question": "Can I bulk order products?",
            "answer": "Yes, Green2B supports bulk ordering to help businesses save costs and reduce their environmental impact through aggregated shipments."
        },
        {
            "question": "What is the AI driven sustainability score?",
            "answer": "Our AI-driven sustainability score evaluates products based on various factors such as materials used, production methods, and overall environmental impact. This score helps businesses make informed decisions when sourcing products."
        },
    ]

@app.route('/faq')
def faq():
    faqs = get_faqs()
    return render_template('faq.html', faqs=faqs)

@app.context_processor
def inject_faqs():
    faqs = get_faqs()
    return dict(faqs=faqs[:3])

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

def get_product_by_id(product_id):
    return Product.query.get(product_id)

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = 'your-webhook-secret'

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        customer_email = session.get('customer_details', {}).get('email')
        shipping = session.get('shipping', {})
        metadata = session.get('metadata', {})

        new_order = Order(
            buyer_email=customer_email,
            status='paid',
            total_amount=session['amount_total'] / 100,  # convert pence to GBP
            currency='gbp',  # optional but good to save currency
            stripe_session_id=session['id'],
            created_at=datetime.utcnow(),
            
            shipping_name = shipping.get('name'),
            shipping_street=shipping.get('address', {}).get('line1'),
            shipping_city=shipping.get('address', {}).get('city'),
            shipping_postcode=shipping.get('address', {}).get('postal_code'),
            shipping_country=shipping.get('address', {}).get('country'),


        )
        db.session.add(new_order)
        db.session.commit()

    return jsonify(success=True)



@app.route('/buy-now', methods=['POST'])
def buy_now():
    try:
        product_id = int(request.form.get('product_id'))
    except (TypeError, ValueError):
        flash("Invalid product ID")
        return redirect(url_for('products'))

    quantity = int(request.form.get('quantity', 1))

    # Replace with your actual product lookup
    product = next((p for p in products_data if p['id'] == product_id), None)
    if not product:
        flash("Product not found")
        return redirect(url_for('products'))

    session['cart'] = [{
        'id': product['id'],
        'name': product['name'],
        'price': product['price'],
        }]

    try:
        session_stripe = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {'name': product['name']},
                    'unit_amount': int(product['price'] * 100),
                },
                'quantity': quantity,
            }],
            mode='payment',
            success_url=url_for('checkout_success', _external=True),
            cancel_url=url_for('product_detail', product_id=product_id, _external=True),
        )
        return redirect(session_stripe.url, code=303)

    except Exception as e:
        flash("Error creating Stripe session: " + str(e))
        print(f"Stripe Error: {e}")
        return redirect(url_for('products'))


app.register_blueprint(profile_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(admin_bp)
if __name__ == '__main__':
    app.run(debug=True)