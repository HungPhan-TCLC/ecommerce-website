"""
app.py - Flask Application Factory
Khởi tạo app, đăng ký blueprints, context processors, template filters.
"""

import os
from flask import Flask
from flask_login import LoginManager, current_user
from dotenv import load_dotenv
from models import db, User, Category, CartItem

load_dotenv()


def create_app():
    app = Flask(__name__)

    # ── Cấu hình ──────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "luxe-fashion-secret-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── Extensions ────────────────────────────────────────
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Đăng ký Blueprints ────────────────────────────────
    from blueprints.home.routes        import home_bp
    from blueprints.auth.routes        import auth_bp
    from blueprints.product.routes     import product_bp
    from blueprints.search.routes      import search_bp
    from blueprints.cart.routes        import cart_bp
    from blueprints.checkout.routes    import checkout_bp
    from blueprints.orders.routes      import orders_bp
    from blueprints.profile.routes     import profile_bp
    from blueprints.recommendations.routes import recommendations_bp
    from blueprints.api.routes         import api_bp
    from blueprints.admin.routes       import admin_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # ── Context Processor ─────────────────────────────────
    @app.context_processor
    def inject_globals():
        """Inject biến dùng chung cho mọi template"""
        categories = Category.query.all()
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return dict(categories=categories, cart_count=cart_count)

    # ── Template Filters ──────────────────────────────────
    @app.template_filter("format_price")
    def format_price(value):
        """Format giá tiền VND: 450000 → 450.000đ"""
        if value is None:
            return "0d"
        return f"{int(value):,.0f}d".replace(",", ".")

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

    return app


# ── Chạy ứng dụng ─────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
