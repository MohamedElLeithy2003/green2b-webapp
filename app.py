import stripe
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'd11c57a2dde5240c1ba0a1bd96be6fdc979173696d613bb44342ea520a3e6379'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'
app.config['MAIL_DEFAULT_SENDER'] = ('Green2B', 'your-email@gmail.com')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///green2b.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()

mail = Mail(app)

stripe.api_key = "sk_test_51O8jQdE43TmUArKlFz7rQnZI4yeZ9iVsoImn0Bs2wI5Bx8PqufupGZ8KZBYB00jy6h8qlI0s8hoiD1z2UOJcUPBy00CHFoTpGp"

subscribers = []

@app.route('/')
def home():
    return render_template('home.html')

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
    {'id': 1, 'name': 'Product 1', 'category': 'ecofriendly', 'price': 24.99, 'score': "85/100", "impact": "Low carbon footprint, recyclable materials"},
    {'id': 2, 'name': 'Product 2', 'category': 'organic', 'price': 29.99, 'score': "90/100", "impact": "Made from organic materials, biodegradable package"},
    {'id': 3, 'name': 'Product 3', 'category': 'recycled', 'price': 19.99, 'score': "80/100", "impact": "Made from recycled materials, energy-efficient production"},
    {'id': 4, 'name': 'Product 4', 'category': 'organic and recycled', 'price': 34.99, 'score': "95/100", "impact": "Made from organic and recycled materials" }
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

    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append(product)
    session.modified = True
    flash(f"{product['name']} added to cart.")
    return redirect(url_for('products'))

@app.route('/cart')
def cart():
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



@app.route('/faq')
def faq():
    faqs = [
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
    return render_template('faq.html', faqs=faqs)


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