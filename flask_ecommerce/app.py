"""
app.py - Flask Application chính cho Fashion E-commerce Store
Bao gồm: Routes, Controllers, Authentication, Cart, Checkout
"""

import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product, Category, CartItem, Order, OrderItem, UserInteraction
from recommendation import recommendation_engine


def create_app():
    app = Flask(__name__)

    # Cấu hình
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "ecommerce.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Khởi tạo extensions
    db.init_app(app)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ========================================================
    #  CONTEXT PROCESSORS (Biến toàn cục cho template)
    # ========================================================
    @app.context_processor
    def inject_globals():
        """Inject biến dùng chung cho mọi template"""
        categories = Category.query.all()
        cart_count = 0
        if current_user.is_authenticated:
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return dict(categories=categories, cart_count=cart_count)

    # ========================================================
    #  FORMAT FILTERS
    # ========================================================
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

    # ========================================================
    #  TRANG CHỦ (HOME)
    # ========================================================
    @app.route("/")
    def index():
        # Sản phẩm nổi bật
        featured_products = Product.query.filter_by(is_featured=True).limit(8).all()

        # Sản phẩm mới nhất
        new_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()

        # Gợi ý cá nhân hóa
        personalized = []
        if current_user.is_authenticated:
            personalized = recommendation_engine.get_personalized_recommendations(
                current_user.id, top_n=8
            )
        else:
            personalized = recommendation_engine._get_popular_products(top_n=8)

        return render_template(
            "index.html",
            featured_products=featured_products,
            new_products=new_products,
            personalized=personalized,
        )

    # ========================================================
    #  DANH SÁCH SẢN PHẨM THEO CATEGORY
    # ========================================================
    @app.route("/category/<slug>")
    def category_products(slug):
        category = Category.query.filter_by(slug=slug).first_or_404()
        products = Product.query.filter_by(category_id=category.id).all()
        return render_template("category.html", category=category, products=products)

    # ========================================================
    #  CHI TIẾT SẢN PHẨM
    # ========================================================
    @app.route("/product/<int:product_id>")
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)

        # Ghi nhận lượt xem (cho recommendation)
        if current_user.is_authenticated:
            existing = UserInteraction.query.filter_by(
                user_id=current_user.id,
                product_id=product_id,
                interaction_type="view",
            ).first()
            if not existing:
                interaction = UserInteraction(
                    user_id=current_user.id,
                    product_id=product_id,
                    interaction_type="view",
                )
                db.session.add(interaction)
                db.session.commit()

        # Content-based: Sản phẩm tương tự
        similar_products = recommendation_engine.get_similar_products(product_id, top_n=4)

        # Co-purchase: Người mua cũng mua
        also_bought = recommendation_engine.get_also_bought(product_id, top_n=4)

        return render_template(
            "product_detail.html",
            product=product,
            similar_products=similar_products,
            also_bought=also_bought,
        )

    # ========================================================
    #  TÌM KIẾM SẢN PHẨM
    # ========================================================
    @app.route("/search")
    def search():
        query = request.args.get("q", "").strip()
        if not query:
            return redirect(url_for("index"))

        # Tìm kiếm trong tên, mô tả, tags
        search_term = f"%{query}%"
        products = Product.query.filter(
            db.or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
                Product.tags.ilike(search_term),
            )
        ).all()

        return render_template("search.html", products=products, query=query)

    # ========================================================
    #  ĐĂNG KÝ
    # ========================================================
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            full_name = request.form.get("full_name", "").strip()

            # Validation
            if not username or not email or not password:
                flash("Vui lòng điền đầy đủ thông tin.", "error")
                return render_template("register.html")

            if len(password) < 6:
                flash("Mật khẩu phải có ít nhất 6 ký tự.", "error")
                return render_template("register.html")

            if User.query.filter_by(username=username).first():
                flash("Tên đăng nhập đã tồn tại.", "error")
                return render_template("register.html")

            if User.query.filter_by(email=email).first():
                flash("Email đã được sử dụng.", "error")
                return render_template("register.html")

            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                full_name=full_name,
            )
            db.session.add(user)
            db.session.commit()

            flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    # ========================================================
    #  ĐĂNG NHẬP
    # ========================================================
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash(f"Chào mừng {user.full_name or user.username}!", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("index"))
            else:
                flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")

        return render_template("login.html")

    # ========================================================
    #  ĐĂNG XUẤT
    # ========================================================
    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Đã đăng xuất thành công.", "success")
        return redirect(url_for("index"))

    # ========================================================
    #  GIỎ HÀNG (CART)
    # ========================================================
    @app.route("/cart")
    @login_required
    def cart():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.product.price * item.quantity for item in cart_items)
        return render_template("cart.html", cart_items=cart_items, total=total)

    @app.route("/cart/add/<int:product_id>", methods=["POST"])
    @login_required
    def add_to_cart(product_id):
        product = Product.query.get_or_404(product_id)
        quantity = int(request.form.get("quantity", 1))

        if quantity < 1:
            quantity = 1

        # Kiểm tra đã có trong giỏ chưa
        existing = CartItem.query.filter_by(
            user_id=current_user.id, product_id=product_id
        ).first()

        if existing:
            existing.quantity += quantity
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=product_id,
                quantity=quantity,
            )
            db.session.add(cart_item)

        # Ghi nhận interaction cart (cho recommendation)
        cart_interaction = UserInteraction.query.filter_by(
            user_id=current_user.id,
            product_id=product_id,
            interaction_type="cart",
        ).first()
        if not cart_interaction:
            interaction = UserInteraction(
                user_id=current_user.id,
                product_id=product_id,
                interaction_type="cart",
            )
            db.session.add(interaction)

        db.session.commit()
        flash(f"Đã thêm \"{product.name}\" vào giỏ hàng!", "success")

        # Nếu request từ AJAX
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
            return jsonify({"success": True, "cart_count": cart_count})

        return redirect(request.referrer or url_for("index"))

    @app.route("/cart/update/<int:item_id>", methods=["POST"])
    @login_required
    def update_cart(item_id):
        cart_item = CartItem.query.get_or_404(item_id)
        if cart_item.user_id != current_user.id:
            flash("Không có quyền truy cập.", "error")
            return redirect(url_for("cart"))

        quantity = int(request.form.get("quantity", 1))
        if quantity <= 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = quantity
        db.session.commit()

        return redirect(url_for("cart"))

    @app.route("/cart/remove/<int:item_id>", methods=["POST"])
    @login_required
    def remove_from_cart(item_id):
        cart_item = CartItem.query.get_or_404(item_id)
        if cart_item.user_id != current_user.id:
            flash("Không có quyền truy cập.", "error")
            return redirect(url_for("cart"))

        db.session.delete(cart_item)
        db.session.commit()
        flash("Đã xóa sản phẩm khỏi giỏ hàng.", "success")
        return redirect(url_for("cart"))

    # ========================================================
    #  CHECKOUT (Mock)
    # ========================================================
    @app.route("/checkout", methods=["GET", "POST"])
    @login_required
    def checkout():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash("Giỏ hàng trống!", "warning")
            return redirect(url_for("cart"))

        total = sum(item.product.price * item.quantity for item in cart_items)

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()
            address = request.form.get("address", "").strip()
            note = request.form.get("note", "").strip()

            if not full_name or not phone or not address:
                flash("Vui lòng điền đầy đủ thông tin giao hàng.", "error")
                return render_template("checkout.html", cart_items=cart_items, total=total)

            # Tạo đơn hàng
            order = Order(
                user_id=current_user.id,
                total_amount=total,
                status="confirmed",
                full_name=full_name,
                phone=phone,
                address=address,
                note=note,
            )
            db.session.add(order)
            db.session.flush()

            # Tạo order items + ghi nhận purchase interaction
            for cart_item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                )
                db.session.add(order_item)

                # Ghi nhận interaction purchase (cho recommendation)
                purchase_interaction = UserInteraction(
                    user_id=current_user.id,
                    product_id=cart_item.product_id,
                    interaction_type="purchase",
                    rating=5.0,
                )
                db.session.add(purchase_interaction)

                # Xóa khỏi giỏ hàng
                db.session.delete(cart_item)

            db.session.commit()

            # Invalidate recommendation cache
            recommendation_engine.invalidate_cache()

            flash("Đặt hàng thành công! Cảm ơn bạn đã mua sắm.", "success")
            return render_template("order_success.html", order=order)

        return render_template("checkout.html", cart_items=cart_items, total=total)

    # ========================================================
    #  LỊCH SỬ ĐƠN HÀNG
    # ========================================================
    @app.route("/orders")
    @login_required
    def order_history():
        orders = Order.query.filter_by(user_id=current_user.id).order_by(
            Order.created_at.desc()
        ).all()
        return render_template("orders.html", orders=orders)

    # ========================================================
    #  TRANG GỢI Ý AI (RECOMMENDATION PAGE)
    # ========================================================
    @app.route("/recommendations")
    def recommendations():
        from sqlalchemy import func

        # Stats tổng quan
        stats = {
            "total_products": Product.query.count(),
            "total_users": User.query.count(),
            "total_interactions": UserInteraction.query.count(),
            "total_orders": Order.query.count(),
        }

        # Gợi ý cá nhân hóa (Collaborative Filtering)
        personalized = []
        user_stats = {"views": 0, "carts": 0, "purchases": 0, "total_interactions": 0}
        rated_products = []

        if current_user.is_authenticated:
            personalized = recommendation_engine.get_personalized_recommendations(
                current_user.id, top_n=8
            )
            # Thống kê user
            user_stats["views"] = UserInteraction.query.filter_by(
                user_id=current_user.id, interaction_type="view"
            ).count()
            user_stats["carts"] = UserInteraction.query.filter_by(
                user_id=current_user.id, interaction_type="cart"
            ).count()
            user_stats["purchases"] = UserInteraction.query.filter_by(
                user_id=current_user.id, interaction_type="purchase"
            ).count()
            user_stats["total_interactions"] = (
                user_stats["views"] + user_stats["carts"] + user_stats["purchases"]
            )

            # Sản phẩm đã đánh giá
            rated_interactions = (
                UserInteraction.query.filter(
                    UserInteraction.user_id == current_user.id,
                    UserInteraction.rating.isnot(None),
                )
                .order_by(UserInteraction.created_at.desc())
                .limit(12)
                .all()
            )
            rated_products = rated_interactions

        # Content-based demo: lấy 1 sản phẩm mẫu
        sample_product = Product.query.filter_by(is_featured=True).first()
        similar_products = []
        also_bought = []
        if sample_product:
            similar_products = recommendation_engine.get_similar_products(
                sample_product.id, top_n=4
            )
            also_bought = recommendation_engine.get_also_bought(
                sample_product.id, top_n=4
            )

        # Trending / Popular
        popular = recommendation_engine._get_popular_products(top_n=8)

        return render_template(
            "recommendations.html",
            stats=stats,
            personalized=personalized,
            user_stats=user_stats,
            rated_products=rated_products,
            sample_product=sample_product,
            similar_products=similar_products,
            also_bought=also_bought,
            popular=popular,
        )

    # ========================================================
    #  API: ĐÁNH GIÁ SẢN PHẨM (Rating)
    # ========================================================
    @app.route("/api/rate/<int:product_id>", methods=["POST"])
    @login_required
    def rate_product(product_id):
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        if not data or "rating" not in data:
            return jsonify({"success": False, "error": "Missing rating"}), 400

        rating = float(data["rating"])
        if rating < 1 or rating > 5:
            return jsonify({"success": False, "error": "Rating must be 1-5"}), 400

        # Tìm interaction có sẵn (ưu tiên purchase > cart > view)
        interaction = UserInteraction.query.filter_by(
            user_id=current_user.id,
            product_id=product_id,
        ).order_by(
            db.case(
                (UserInteraction.interaction_type == "purchase", 1),
                (UserInteraction.interaction_type == "cart", 2),
                else_=3,
            )
        ).first()

        if interaction:
            interaction.rating = rating
        else:
            interaction = UserInteraction(
                user_id=current_user.id,
                product_id=product_id,
                interaction_type="view",
                rating=rating,
            )
            db.session.add(interaction)

        db.session.commit()
        recommendation_engine.invalidate_cache()

        return jsonify({"success": True, "rating": rating, "product": product.name})

    # ========================================================
    #  API: GET RECOMMENDATIONS (JSON)
    # ========================================================
    @app.route("/api/recommendations/personalized")
    @login_required
    def api_personalized():
        recs = recommendation_engine.get_personalized_recommendations(
            current_user.id, top_n=8
        )
        return jsonify({
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "original_price": p.original_price,
                    "image_url": p.image_url,
                    "category": p.category.name,
                }
                for p in recs
            ],
            "algorithm": "collaborative_filtering",
        })

    @app.route("/api/recommendations/similar/<int:product_id>")
    def api_similar(product_id):
        recs = recommendation_engine.get_similar_products(product_id, top_n=8)
        return jsonify({
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "original_price": p.original_price,
                    "image_url": p.image_url,
                    "category": p.category.name,
                }
                for p in recs
            ],
            "algorithm": "content_based_tfidf",
        })

    @app.route("/api/recommendations/also-bought/<int:product_id>")
    def api_also_bought(product_id):
        recs = recommendation_engine.get_also_bought(product_id, top_n=8)
        return jsonify({
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "original_price": p.original_price,
                    "image_url": p.image_url,
                    "category": p.category.name,
                }
                for p in recs
            ],
            "algorithm": "co_purchase_analysis",
        })

    return app


# ========================================================
#  CHẠY ỨNG DỤNG
# ========================================================
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
