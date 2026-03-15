"""
models.py - Database Models cho E-commerce Fashion Store
Sử dụng Flask-SQLAlchemy + Flask-Login
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


# ==================== USER MODEL ====================
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)
    interactions = db.relationship('UserInteraction', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)


# ==================== CATEGORY MODEL ====================
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)


# ==================== PRODUCT MODEL ====================
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float, nullable=True)  # Giá gốc (để hiển thị giảm giá)
    image_url = db.Column(db.String(500), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    tags = db.Column(db.String(500), nullable=False)  # Tags phân tách bằng dấu phẩy (cho recommendation)
    gender = db.Column(db.String(20), nullable=False)  # 'nam', 'nu', 'unisex'
    material = db.Column(db.String(100), nullable=True)
    style = db.Column(db.String(100), nullable=True)  # 'casual', 'formal', 'streetwear', 'sporty'
    is_featured = db.Column(db.Boolean, default=False)
    stock = db.Column(db.Integer, default=50)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    interactions = db.relationship('UserInteraction', backref='product', lazy=True)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)


# ==================== CART ITEM MODEL ====================
class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== ORDER MODEL ====================
class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, shipped, delivered
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True)


# ==================== ORDER ITEM MODEL ====================
class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Giá tại thời điểm đặt hàng


# ==================== USER INTERACTION MODEL (cho Recommendation) ====================
class UserInteraction(db.Model):
    """
    Lưu lại tương tác của user với sản phẩm.
    interaction_type: 'view', 'cart', 'purchase', 'wishlist'
    Dữ liệu này được dùng cho Collaborative Filtering / User-based Recommendation.
    """
    __tablename__ = 'user_interactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    interaction_type = db.Column(db.String(20), nullable=False)  # view, cart, purchase
    rating = db.Column(db.Float, nullable=True)  # Rating 1-5 (optional)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
