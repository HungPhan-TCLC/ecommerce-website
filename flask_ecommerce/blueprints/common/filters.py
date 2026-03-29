"""
blueprints/common/filters.py
Template filters và context processors dùng chung cho toàn bộ app.
"""

from flask import Blueprint
from flask_login import current_user
from models import Category, CartItem

common_bp = Blueprint("common", __name__)


def register_common(app):
    """Đăng ký context processors và template filters vào app."""

    # ── Context Processor: Biến toàn cục cho mọi template ──
    @app.context_processor
    def inject_globals():
        """Inject categories và cart_count vào mọi template."""
        categories = Category.query.all()
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return dict(categories=categories, cart_count=cart_count)

    # ── Template Filters ──
    @app.template_filter("format_price")
    def format_price(value):
        """Format giá tiền VND: 450000 → 450.000₫"""
        if value is None:
            return "0₫"
        return f"{int(value):,.0f}₫".replace(",", ".")

    @app.template_filter("discount_percent")
    def discount_percent(value):
        """Tính % giảm giá. Nhận tuple (price, original_price)"""
        if isinstance(value, (list, tuple)) and len(value) == 2:
            price, original_price = value
        else:
            return 0
        if not original_price or original_price <= price:
            return 0
        return int(((original_price - price) / original_price) * 100)
