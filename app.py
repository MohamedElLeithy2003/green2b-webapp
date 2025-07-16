import stripe
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from flask_login import current_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
from models import db, Product, User, CartItem
from flask_migrate import Migrate



app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
migrate = Migrate(app, db)
app.secret_key = 'd11c57a2dde5240c1ba0a1bd96be6fdc979173696d613bb44342ea520a3e6379'


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'
app.config['MAIL_DEFAULT_SENDER'] = ('Green2B', 'your-email@gmail.com')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///green2b.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

mail = Mail(app)

stripe.api_key = "sk_test_51O8jQdE43TmUArKlFz7rQnZI4yeZ9iVsoImn0Bs2wI5Bx8PqufupGZ8KZBYB00jy6h8qlI0s8hoiD1z2UOJcUPBy00CHFoTpGp"

subscribers = []

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
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

        flash('Registration successful. You can now login')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

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


@app.route('/logout')
def logout():
    session.pop('user_email', None)
    session.clear()
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

    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html')


products_data = [
    {
        'id': 1,
        'supplier': 'Smaart Rice Straw',
        'name': 'Rice Starch Straw',
        'image': 'images/starch_straw.png',
        'category': 'ecofriendly',
        'quantity': 100,
        'price': 1.73,
        'score': "100/100",
        'description': "Made from food-grade rice & tapioca starch, holds strong in cold drinks, resists for 45+ minutes, 100% biodegradable and compostable, odourless, tasteless, and chemical-free"
    },
    {
        'id': 2,
        'supplier': 'Chuk eat safe',
        'name': 'Dine-in Bagasse Container',
        'image': 'images/chuck_eat_safe.png',
        'category': 'ecofriendly',
        'quantity': 100,
        'price': 10.00,
        'score': "100/100",
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
        'score': "100/100",
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
        'score': "100/100",
        'description': "Bagasse lid for spill-free dining, perfect for curries and salads, fully compostable and eco-friendly"
    },
    {
        'id': 5,
        'supplier': 'GreenR by BioMandi',
        'name': 'Paper made out of Cigarette Buds',
        'image': 'images/greenR_paper.png',
        'category': 'recycled',
        'quantity': 1,
        'price': 4.70,
        'score': "100/100",
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
        'score': "100/100",
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
        'score': "100/100",
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
        'score': "100/100",
        'description': "Natural color bottle and mugs crafted from sustainable bamboo"
    }
]

@app.route('/products')
def products():
    query = request.args.get('q', '').lower()
    filter_category = request.args.get('category', '').lower()
    filter_impact = request.args.get('impact', '').lower()

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
    return render_template('products.html', products=filtered_products, query=query, filter_category=filter_category, filter_impact=filter_impact)

@app.route('/products/<int:product_id>')
def product_detail(product_id):
    product = next((p for p in products_data if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404
    return render_template('product_details.html', product=product)

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    product = next((p for p in products_data if p['id'] == product_id), None)
    if not product:
        flash("Product not found")
        return redirect(url_for('products'))

    if current_user.is_authenticated:
        item = CartItem(
            user_id = current_user.id,
            product_id = product['id'],
            product_name = product['name'],
            price = product['price']
        )
        db.session.add(item)
        db.session.commit()
    else:

        if not isinstance(session.get('cart'), list):
            session['cart'] = []

        session['cart'].append(product)
        session.modified = True
        flash(f"{product['name']} added to cart.")
    return redirect(url_for('products'))

@app.route('/cart')
def cart():
    if current_user.is_authenticated:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_items = [{'name': i.product_name, 'price': i.price} for i in items]
    else:
        cart_items = session.get('cart', [])

    total = sum(item['price'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        postcode = request.form.get('postcode')
        country = request.form.get('country')

        cart = session.get('cart', [])

        order_details = "Order details:\n"
        for item in cart:
            order_details += f"- {item['name']} (${item['price']})\n"
        
        order_summary = f"""
        Order received from: {name}, ({email})
        Shipping to: {address}, {city}, {postcode}, {country}
        Phone: {phone}
        
        {order_details}
        
        """
        msg = Message(subject=f"New order from {name}",
                      recipients = ['your-business-email@example.com'],
                      body=order_summary)
        #mail.send(msg)

        confirm_msg = Message(subject="Your Green2B Order Confirmation",
                      recipients = [email],
                      body=f"Hi {name},\n\n Thank you for placing and order with Green2B. \n\n{order_details}\n\nWe will process your order shortly")
        #mail.send(confirm_msg)

        session['last_order'] = {
            'name': name,
            'email': email,
            'phone': phone,
            'address': address,
            'city': city,
            'postcode': postcode,
            'country': country,
            'items': session.get('cart', [])
        }

        print(f"Order received from: {name} ({email})")
        print(f"Shipping to: {address}, {city}, {postcode}, {country}")
        print(f"Phone: {phone}")
        
        session.pop('cart', None)
        flash("Order placed successfully!")
        return redirect(url_for('checkout_success'))
    return render_template('checkout.html', cart=session.get('cart', []), publishable_key="pk_test_51O8jQdE43TmUArKlpffHWwtJ8w8poxqLbjyBFa2Ot2ZvEyqgqFrsPKyHyySRdrgelYHik3uQCmtst66eHHRECu0o008aBTzQVL")

@app.route('/checkout-success')
def checkout_success():
    return render_template('checkout_success.html')



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        print(f"Received message from {name} ({email}): {message}")
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

        print(f"New supplier application: \nName: {name}\nCompany: {company}\nEmail: {email}\nWebsite: {website}\nProducts: {products}\nMessage: {message}")
        
        return redirect('/supplier-success')
    return render_template('supplier_apply.html')

@app.route('/supplier-success')
def supplier_success():
    return render_template('supplier_success.html')


def get_current_supplier_id():
    return session.get('user_id')

@app.route('/supplier/products')
def supplier_products():

    supplier_id = get_current_supplier_id()
    products = Product.query.filter_by(supplier_id=supplier_id).all()
    return render_template('supplier_products.html', products=products)

@app.route('/supplier/products/add', methods=['GET', 'POST'])
def add_product():
    supplier_id = get_current_supplier_id()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])

        new_product = Product(
            name=name,
            category=category,
            price=price,
            supplier_id=supplier_id,
            status='pending'
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

        db.session.commit()
        flash('Product updated successfully', 'success')
        return redirect(url_for(supplier_products))
    
    return render_template('edit_product.html', product=product)

@app.route('/supplier/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    supplier_id = get_current_supplier_id()
    product = Product.query.filter_by(id=product_id, supplier_id=supplier_id).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('supplier_products'))




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

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    cart = session.get('cart', [])
    if not cart:
        flash("Cart is empty")
        return redirect(url_for('cart'))

    line_items = [
        {
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': item['name']},
                'unit_amount': int(item['price'] * 100),  
            },
            'quantity': 1,
        }
        for item in cart
    ]
    try:
        session_stripe = stripe.checkout.Session.create(
            payment_method_types = ['card'],
            line_items=line_items,
            mode='payment',
            success_url = url_for('checkout_success', _external=True),
            cancel_url = url_for('cart', _external=True),
        )
        return redirect(session_stripe.url, code=303)
    except Exception as e:
        flash("Error creating Stripe session")
        print(f"Stripe Error: {e}")
        return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True)