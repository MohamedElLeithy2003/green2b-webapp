import stripe
import openai
import os
import secrets
from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify, current_app
from flask_mail import Mail, Message
from flask_login import current_user, LoginManager, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from models import db, Product, User, CartItem, Order, OrderItem, SupplierApplication, Supplier, ProductView
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Optional
from datetime import date, datetime, timedelta
from threading import Thread
from sqlalchemy import func, cast, Date
from sqlalchemy.sql import func, expression



app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
migrate = Migrate(app, db)
profile_bp = Blueprint('profile', __name__)
orders_bp = Blueprint('orders', __name__, url_prefix='/orders')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
app.secret_key = 'd11c57a2dde5240c1ba0a1bd96be6fdc979173696d613bb44342ea520a3e6379'


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'green2bteam@gmail.com'
app.config['MAIL_PASSWORD'] = 'ejtt rttq poqc krge'
app.config['MAIL_DEFAULT_SENDER'] = ('Green2B', 'green2bteam@gmail.com')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///green2b.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

mail = Mail(app)

db.init_app(app)
with app.app_context():
    db.create_all()
    
stripe.api_key = "sk_test_51O8jQdE43TmUArKlFz7rQnZI4yeZ9iVsoImn0Bs2wI5Bx8PqufupGZ8KZBYB00jy6h8qlI0s8hoiD1z2UOJcUPBy00CHFoTpGp"

subscribers = []

ADMIN_USERNAME = 'adminuser'
ADMIN_PASSWORD = 'supersecretpassword'

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
    product.status = 'approved'
    db.session.commit()
    flash(f'Product {product.name} approved successfully.', 'success')
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

    products = products_data
    return render_template('admin_products.html', products=products)


@admin_bp.route('/products/<product_id>', methods=['GET', 'POST'])
def admin_product_detail(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))

    # Dummy product (starts with 'd')
    if str(product_id).startswith('d'):
        dummy_id = int(str(product_id)[1:])
        from types import SimpleNamespace
        match = next((p for p in products_data if p['id'] == dummy_id), None)
        if not match:
            abort(404)
        product = SimpleNamespace(**match)
        return render_template('admin_product_detail.html', product=product, is_dummy=True)

    # Real DB product
    product = Product.query.get_or_404(int(product_id))

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
        return redirect(url_for('admin.admin_product_detail', product_id=product_id))

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
    return redirect(url_for('admin.admin_product_detail', product_id=product_id))

@admin_bp.route('/products/<int:product_id>/remove', methods=['POST'])
def remove_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_login'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'Product {product.name} has been deleted', 'danger')
    return redirect(url_for('admin.admin_products'))

@admin_bp.route('/supplier-applications')
def supplier_applications():
    applications = SupplierApplication.query.order_by(SupplierApplication.created_at.desc()).all()
    return render_template('supplier_applications.html', applications=applications)

@admin_bp.route('/supplier-approve/<int:app_id>', methods=['POST'])
def supplier_approve(app_id):
    application = SupplierApplication.query.get_or_404(app_id)
    if not application.user:
        flash(f'Error: No user found for this application #{application.id}', 'danger')
        return redirect(url_for('admin.supplier_applications'))

    application.status = 'Approved'

    user = application.user
    user.role = 'supplier'

    supplier = Supplier.query.filter_by(user_id=user.id).first()
    if not supplier:
        supplier = Supplier(user_id=user.id, company_name=application.company, verified=True, sustainability_score=0.0)
        db.session.add(supplier)
    else:
        supplier.verified = True

    db.session.commit()

    try:
        subject = "Your Supplier Application Has Been Approved"
        recipient = user.email
        body = f"""Hello {application.company},

Congratulations! Your supplier application has been approved.

You can now log in to your supplier dashboard and start listing your sustainable products.

Login here: {url_for('supplier.supplier_login', _external=True)}

Regards,  
Green2B Admin Team
"""
        msg = Message(subject=subject, recipients=[recipient], body=body)
        mail.send(msg)
        flash(f'Supplier application #{application.id} approved and email sent.', 'success')
    except Exception as e:
        print(str(e))
        flash("Error sending approval email to supplier", 'danger')

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

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        new_user = User(email=email, role=role)
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
    subject = "Thank you for subscribing to Green2B"
    body = "Thank you for subscribing to Green2B! We will keep you updated with our latest products and sustainability initiatives."
    send_email(subject, [email], body)

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
        'id': 1,
        'supplier': 'Smaart Rice Straw',
        'name': 'Rice Starch Straw',
        'image': 'images/starch_straw.png',
        'category': 'ecofriendly',
        'quantity': 100,
        'price': 1.73,
        'score': "95/100",
        'description': "Made from food-grade rice & tapioca starch, holds strong in cold drinks, resists for 45+ minutes, 100% biodegradable and compostable, odourless, tasteless, and chemical-free"
    },
    {
        'id': 2,
        'supplier': 'Chuk eat safe',
        'name': 'Dine-in Bagasse Container',
        'image': 'images/chuck_eat_safe.png',
        'category': 'ecofriendly',
        'quantity': 100,
        'price': 0.10,
        'score': "80/100",
        'description': "Made from eco-friendly sugarcane bagasse, reheatable and freezer-safe, suitable for all applications"
    },
    {
        'id': 3,
        'supplier': 'Chuk eat safe',
        'name': 'Disposable Wooden Spoon',
        'image': 'images/takeaway_spoon (1).png',
        'category': 'organic',
        'quantity': 100,
        'price': 1.20,
        'score': "80/100",
        'description': "Made from birchwood, sturdy even in hot gravy, ideal for parties, picnics, events, and gatherings"
    },
    {
        'id': 4,
        'supplier': 'Chuk eat safe',
        'name': 'Container Lids',
        'image': 'images/container_lid.png',
        'category': 'ecofriendly',
        'quantity': 100,
        'price': 8.00,
        'score': "80/100",
        'description': "Bagasse lid for spill-free dining, perfect for curries and salads, fully compostable and eco-friendly"
    },
    {
        'id': 5,
        'supplier': 'GreenR by BioMandi',
        'name': 'Paper made out of Cigarette Buds',
        'image': 'images/greenR_paper.png',
        'category': 'recycled',
        'quantity': 500,
        'price': 4.70,
        'score': "85/100",
        'description': "75 GSM A4-size paper made from 8000 cigarette butts, repurposed waste into usable stationary"
    },
    {
        'id': 6,
        'supplier': 'Mesrii Private Limited',
        'name': 'Business Gift Hamper',
        'image': 'images/Gift Hamper .jpeg.jpg',
        'category': 'organic',
        'quantity': 10,
        'price': 130.00,
        'score': "90/100",
        'description': "Includes Cork Diary, Mug, Card Holder, Pen, and Keychain – all sustainably made from cork"
    },
    {
        'id': 7,
        'supplier': 'GreenR by BioMandi',
        'name': 'Jute Folder',
        'image': 'images/Jute Folder .jpeg.jpg',
        'category': 'organic',
        'quantity': 100,
        'price': 9.00,
        'score': "80/100",
        'description': "Made from natural jute, biodegradable and reusable alternative to plastic folders"
    },
    {
        'id': 8,
        'supplier': 'Mesrii Private Limited',
        'name': 'Bamboo Bottle and 2 Mugs',
        'image': 'images/bamboo_bottle_mugs.png',
        'category': 'organic',
        'quantity': 10,
        'price': 100.00,
        'score': "85/100",
        'description': "Natural color bottle and mugs crafted from sustainable bamboo"
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
    except(ValueError):
        min_price = None
    
    try:
        max_price = float(max_price) if max_price else None
    except(ValueError):
        max_price = None

    filtered_products = products_data

    if query:
        filtered_products = [
            p for p in filtered_products
            if query in p['name'].lower() or query in p['score'].lower()
        ]
    
    if filter_category:
        filtered_products = [
            p for p in filtered_products
            if filter_category == p['category'].lower()
        ]
    
    if filter_impact:
        filtered_products = [
            p for p in filtered_products
            if filter_impact in p['impact'].lower()
        ]

    if min_price is not None:
        filtered_products = [
            p for p in filtered_products
            if p.get('price') is not None and p['price'] >= min_price
        ]

    if max_price is not None:
        filtered_products = [
            p for p in filtered_products
            if p.get('price') is not None and p['price'] <= max_price
        ]

    return render_template('products.html', products=filtered_products, query=query, filter_category=filter_category, filter_impact=filter_impact, min_price=min_price, max_price=max_price)

@app.route('/products/<int:product_id>')
def product_detail(product_id):
    product = next((p for p in products_data if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404
    return render_template('product_details.html', product=product)

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
        'cover_image': 'images/organic-removebg-preview.png',
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


@app.route('/add-to-cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    product = next((p for p in products_data if p['id'] == product_id), None)
    if not product:
        flash("Product not found")
        return redirect(url_for('products'))

    # Read quantity from form, default 1 if invalid
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity < 1:
            quantity = 1
    except ValueError:
        quantity = 1

    if current_user.is_authenticated:
        existing_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product['id']).first()
        if existing_item:
            existing_item.quantity += quantity
        else:
            item = CartItem(
                user_id=current_user.id,
                product_id=product['id'],
                product_name=product['name'],
                price=product['price'],
                quantity=quantity
            )
            db.session.add(item)
        db.session.commit()

    else:
        if not isinstance(session.get('cart'), list):
            session['cart'] = []

        for item in session['cart']:
            if item['id'] == product['id']:
                # Ensure quantity key exists and is an int
                if 'quantity' not in item or not isinstance(item['quantity'], int):
                    item['quantity'] = 0
                item['quantity'] += quantity
                break
        else:
            # This else belongs to the for loop: runs if break never happens
            session['cart'].append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'image_url': product.get('image_url', '/static/images/default.jpg')
            })

        session.modified = True
        flash(f"{product['name']} added to cart.")

    return redirect(url_for('products'))
@app.route('/cart')
def cart():
    if current_user.is_authenticated:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_items = [
            {
                'id': i.product_id,
                'name': i.product_name,
                'price': i.price,
                'quantity': i.quantity,
                'subtotal': i.price * i.quantity,
                'image_url': i.image_url if hasattr(i, 'image_url') and i.image_url else '/static/images/default.jpg'
            }
            for i in items
        ]
    else:
        cart_items = []
        for item in session.get('cart', []):
            quantity = item.get('quantity', 1)
            price = item['price']
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

@app.route('/update-cart-quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    new_quantity = request.form.get('quantity', '1')  
    try:
        new_quantity = int(new_quantity)
    except ValueError:
        new_quantity = 1  

    if new_quantity < 1:
        new_quantity = 1
    cart = session.get('cart', [])
    for item in cart:
        if item['id'] == product_id:
            item['quantity'] = new_quantity
            item['subtotal'] = item['price'] * new_quantity
            break

    session['cart'] = cart
    return redirect(url_for('cart'))





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




@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Save buyer info in session
        session['buyer_info'] = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'postcode': request.form.get('postcode'),
            'country': request.form.get('country'),
        }
        return redirect(url_for('create_checkout_session'))

    return render_template('checkout.html', cart=session.get('cart', []))




@app.route('/checkout-success')
def checkout_success():
    cart = session.get('cart', [])
    buyer_info = session.get('buyer_info', {})

    if not cart:
        flash("Cart is empty")
        return redirect(url_for('products'))

    total = sum(item['price'] * item.get('quantity', 1) for item in cart)

    buyer_email = buyer_info.get('email')

    new_order = Order(
        buyer_id=session.get('user_id') if 'user_id' in session else None,
        email=buyer_email,  # Store buyer email here
        total_price=total,
        status='Completed',
        # add any other fields you need
    )
    db.session.add(new_order)
    db.session.commit()

    # Build email content
    subject = "Order Confirmation"
    body = (
        f"Hi {buyer_info.get('name', 'Customer')},\n\n"
        f"Thank you for your order! Here are the details:\n\n"
        f"Order ID: {new_order.id}\n"
        f"Total Price: ${total:.2f}\n"
        f"Items:\n"
    )
    for item in cart:
        quantity = item.get('quantity', 1)
        body += f"- {item['name']} (x{quantity}) - ${item['price'] * quantity:.2f}\n"

    body += (
        "\nWe will process your order shortly.\n"
        "Thank you for shopping with us!\n\n"
        "Best regards,\n"
        "Green2B Team"
    )

    # Send confirmation email using the saved email in order
    send_email(subject, [buyer_email], body)

    # Save order info in session for further use
    session['last_order'] = {
        'order_id': new_order.id,
        'total_price': total,
        'items': cart,
        **buyer_info
    }

    # Clear cart and buyer info after order completion
    session.pop('cart', None)
    session.pop('buyer_info', None)

    return render_template('checkout_success.html')




@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        flash("Thank you for reaching out! We'll get back to you soon.")

        subject = "New Contact Form Submission"
        body = f"Name: {name}\nEmail: {email}\nMessage: {message}"
        recipients = ['green2bteam@gmail.com']  # your support email

        send_email(subject, recipients, body)

        subject_user = "Thank you for contacting Green2B"
        body_user = f"Hello {name},\n\nThank you for reaching out to us. We have received your message and will get back to you shortly.\n\nBest regards,\nGreen2B Team"
        send_email(subject_user, [email], body_user)

        flash("Thank you for your message! We'll get back to you soon.")

        return redirect('/contact-success')

    return render_template('contact.html')
@app.route('/contact-success')
def contact_success():
    return render_template('contact_success.html')

@app.route('/supplier-apply', methods=['GET', 'POST'])
def supplier_apply():
    if request.method == 'POST':
        name = request.form.get('name')
        company = request.form.get('company')
        email = request.form.get('email')
        website = request.form.get('website')
        products = request.form.get('products')
        message = request.form.get('message')

        user_id = current_user.id if current_user.is_authenticated else None
        
        new_app = SupplierApplication(
            user_id=user_id,
            name=name,
            company=company,
            email=email,
            website=website,
            products=products,
            message=message,
            status='pending'
        )
        db.session.add(new_app)
        db.session.commit()
        
        print(f"New supplier application: \nName: {name}\nCompany: {company}\nEmail: {email}\nWebsite: {website}\nProducts: {products}\nMessage: {message}")
        
        subject = "New Supplier Application Received"
        body = f"""
        A new supplier application has been submitted:\n
        Name: {name}\n
        Company: {company}\n
        Email: {email}\n
        Website: {website}\n
        Products: {products}\n
        Message: {message}
        """
        recipients = ['green2bteam@gmail.com']
        send_email(subject, recipients, body)
        
        return redirect('/supplier-success')
    return render_template('supplier_apply.html')

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



@app.route('/supplier/register', methods=['GET', 'POST'])
def supplier_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        company = request.form['company']

        if User.query.filter_by(email=email, role='supplier').first():
            flash('Email already registered as a supplier', 'danger')
            return redirect(url_for('supplier_register'))

        user = User(name=name, email=email, role='supplier')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        supplier = Supplier(user_id=user.id, company_name=company, verified=False)
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier registration successful. Please wait for approval.', 'success')
        return redirect(url_for('supplier_login'))
    
    return render_template('supplier_register.html')


@app.route('/supplier_login', methods=['GET', 'POST'])
def supplier_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email, role='supplier').first()
        if user and user.check_password(password):
            supplier = Supplier.query.filter_by(user_id=user.id).first()
            if supplier:
                if supplier.verified:
                    login_user(user)
                    return redirect(url_for('supplier_products'))
                else:
                    flash('Your supplier account is not verified yet. Please wait for approval.', 'warning')
                    login_user(user)
                    return redirect(url_for('supplier_apply'))

                    subject = "Supplier Account Pending Approval"
                    body = f"Hello {user.name},\n\nThank you for registering as a supplier on Green2B. Your account is currently pending approval. We will notify you once your account is verified.\n\nBest regards,\nGreen2B Team"
                    send_email(subject, [email], body)
        
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
    products = Product.query.filter_by(supplier_id=supplier_id).all()

    today = date.today()
    start_date = today - timedelta(days=6)

    # Just create empty analytics data with zeros
    analytics_data = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        analytics_data.append({
            'day': day_str,
            'views': 0,
            'orders': 0,
            'sales': 0.0,
        })

    return render_template('supplier_products.html', products=products, analytics_data=analytics_data)

@app.route('/supplier/products/add', methods=['GET', 'POST'])
def add_product():
    supplier_id = get_current_supplier_id()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        description = request.form.get('description')
        impact = request.form.get('impact')

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            upload_folder = os.path.join(app.root_path, 'static/images')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, image_filename)
            image_file.save(image_path)
            
            image_url = f'static/images/{image_filename}'
        
        else:
            image_url = None
        

        new_product = Product(
            name=name,
            category=category,
            price=price,
            supplier_id=supplier_id,
            image_url=image_url,
            status='pending',
            description=description,
            impact=impact
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully and is pending approval.', 'success')
        return redirect(url_for('supplier_products'))

    return render_template('add_products.html')

@app.route('/supplier/products/<int:product_id>')
def supplier_product_detail(product_id):
    supplier_id = get_current_supplier_id()
    product = Product.query.filter_by(id=product_id, supplier_id=supplier_id).first()
    if not product:
        return "Product not found or access denied", 404
    return render_template('supplier_product_details.html', product=product)

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
        metadata = session.get('metadata', {})

        new_order = Order(
            buyer_email=customer_email,
            status='paid',
            total_amount=session['amount_total'] / 100,  # convert pence to GBP
            currency='gbp',  # optional but good to save currency
            stripe_session_id=session['id'],
            created_at=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.commit()

    return jsonify(success=True)

    
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))

    cart = session.get('cart', [])
    buyer_info = session.get('buyer_info', {})

    if product_id:
        product = get_product_by_id(int(product_id))
        if not product:
            flash("Product not found")
            return redirect(url_for('products'))

        # Add or update item in cart
        for item in cart:
            if item['id'] == product.id:
                item['quantity'] += quantity
                break
        else:
            cart.append({
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'quantity': quantity
            })

    if not cart:
        flash("Cart is empty")
        return redirect(url_for('products'))

    session['cart'] = cart

    line_items = [
        {
            'price_data': {
                'currency': 'gbp',
                'product_data': {'name': item['name']},
                'unit_amount': int(item['price'] * 100),
            },
            'quantity': item['quantity'],
        }
        for item in cart
    ]

    try:
        stripe_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=buyer_info.get('email'), 
            success_url=url_for('checkout_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cart', _external=True),
        )
        return redirect(stripe_session.url, code=303)

    except Exception as e:
        flash("Error creating Stripe session")
        print(f"Stripe Error: {e}")
        return redirect(url_for('cart'))


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