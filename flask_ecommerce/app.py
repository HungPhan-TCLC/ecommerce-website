"""
app.py - Flask Application chính cho Fashion E-commerce Store
Bao gồm: Routes, Controllers, Authentication, Cart, Checkout
"""

import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from models import db, User, Product, Category, CartItem, Order, OrderItem, UserInteraction
from recommendation import recommendation_engine
from payment import (
    vnpay_create_payment_url, vnpay_verify_return, VNPAY_RESPONSE_CODES,
    momo_create_payment, momo_verify_return,
)

load_dotenv()


def create_app():
    app = Flask(__name__)

    # Cấu hình
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "luxe-fashion-secret-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
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
        q = request.args.get("q", "").strip()

        # ── Filter params ──
        category_filter = request.args.get("category", "").strip()
        gender_filter   = request.args.get("gender", "").strip()
        style_filter    = request.args.get("style", "").strip()
        price_min_raw   = request.args.get("price_min", "").strip()
        price_max_raw   = request.args.get("price_max", "").strip()
        sort_by         = request.args.get("sort", "relevant")

        try:
            price_min = float(price_min_raw) if price_min_raw else None
        except ValueError:
            price_min = None
        try:
            price_max = float(price_max_raw) if price_max_raw else None
        except ValueError:
            price_max = None

        # ── Bắt đầu build query ──
        product_query = Product.query

        # Tìm theo từ khoá (bắt buộc nếu có q)
        if q:
            search_term = f"%{q}%"
            product_query = product_query.filter(
                db.or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.tags.ilike(search_term),
                )
            )

        # Filter theo danh mục
        if category_filter:
            try:
                product_query = product_query.filter(
                    Product.category_id == int(category_filter)
                )
            except ValueError:
                pass

        # Filter theo giới tính
        if gender_filter in ("nam", "nu", "unisex"):
            product_query = product_query.filter(Product.gender == gender_filter)

        # Filter theo phong cách
        if style_filter:
            product_query = product_query.filter(
                Product.style.ilike(f"%{style_filter}%")
            )

        # Filter theo khoảng giá
        if price_min is not None:
            product_query = product_query.filter(Product.price >= price_min)
        if price_max is not None:
            product_query = product_query.filter(Product.price <= price_max)

        # ── Sắp xếp ──
        if sort_by == "price_asc":
            product_query = product_query.order_by(Product.price.asc())
        elif sort_by == "price_desc":
            product_query = product_query.order_by(Product.price.desc())
        elif sort_by == "newest":
            product_query = product_query.order_by(Product.created_at.desc())
        else:
            # Mặc định: relevant (theo tên)
            product_query = product_query.order_by(Product.name.asc())

        products = product_query.all()

        # ── Dữ liệu cho sidebar filter ──
        all_categories = Category.query.order_by(Category.name).all()
        gender_options = [
            {"value": "nam",    "label": "Nam"},
            {"value": "nu",     "label": "Nữ"},
            {"value": "unisex", "label": "Unisex"},
        ]
        style_options = [
            {"value": "casual",     "label": "Casual"},
            {"value": "formal",     "label": "Formal"},
            {"value": "streetwear", "label": "Streetwear"},
            {"value": "sporty",     "label": "Sporty"},
        ]

        # Tổng hợp filter đang active (để hiển thị badges)
        active_filters = {}
        if category_filter:
            cat_obj = Category.query.get(int(category_filter)) if category_filter.isdigit() else None
            if cat_obj:
                active_filters["category"] = {"label": cat_obj.name, "value": category_filter}
        if gender_filter:
            label_map = {"nam": "Nam", "nu": "Nữ", "unisex": "Unisex"}
            active_filters["gender"] = {"label": label_map.get(gender_filter, gender_filter), "value": gender_filter}
        if style_filter:
            active_filters["style"] = {"label": style_filter.capitalize(), "value": style_filter}
        if price_min is not None:
            active_filters["price_min"] = {"label": f"Từ {int(price_min):,}₫".replace(",", "."), "value": price_min_raw}
        if price_max is not None:
            active_filters["price_max"] = {"label": f"Đến {int(price_max):,}₫".replace(",", "."), "value": price_max_raw}

        return render_template(
            "search.html",
            products=products,
            query=q,
            all_categories=all_categories,
            gender_options=gender_options,
            style_options=style_options,
            active_filters=active_filters,
            # current filter values (để giữ trạng thái form)
            category_filter=category_filter,
            gender_filter=gender_filter,
            style_filter=style_filter,
            price_min=price_min_raw,
            price_max=price_max_raw,
            sort_by=sort_by,
        )

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
        from sqlalchemy import func

        status_filter = request.args.get("status", "all").strip()

        # ── Đếm theo từng status bằng SQL GROUP BY (chính xác 100%) ──
        raw_counts = db.session.query(
            Order.status,
            func.count(Order.id).label("cnt")
        ).filter(
            Order.user_id == current_user.id
        ).group_by(Order.status).all()

        # Tổng hợp thành dict, mọi status không được map sẽ vào "other"
        status_map = {row.status: row.cnt for row in raw_counts}
        total = sum(status_map.values())

        counts = {
            "all":             total,
            "pending_payment": status_map.get("pending_payment", 0),
            "payment_failed":  status_map.get("payment_failed",  0),
            "confirmed":       status_map.get("confirmed",       0),
            "shipped":         status_map.get("shipped",         0),
            "delivered":       status_map.get("delivered",       0),
            # Gộp "pending" (legacy) vào "cancelled" để không mất đơn
            "cancelled": status_map.get("cancelled", 0) + status_map.get("pending", 0),
        }

        # ── Lấy danh sách đơn hàng theo filter ──
        base_q = Order.query.filter_by(user_id=current_user.id)

        if status_filter == "cancelled":
            # Gộp cả "pending" legacy vào tab Đã hủy
            orders = base_q.filter(
                Order.status.in_(["cancelled", "pending"])
            ).order_by(Order.created_at.desc()).all()
        elif status_filter != "all":
            orders = base_q.filter_by(
                status=status_filter
            ).order_by(Order.created_at.desc()).all()
        else:
            orders = base_q.order_by(Order.created_at.desc()).all()

        return render_template(
            "orders.html",
            orders=orders,
            status_filter=status_filter,
            counts=counts,
        )


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

        # Hybrid Recommendation
        hybrid_products = []
        hybrid_algo = "popular"
        if current_user.is_authenticated:
            hybrid_products, hybrid_algo = recommendation_engine.get_hybrid_recommendations(
                current_user.id, top_n=8
            )

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
            hybrid_products=hybrid_products,
            hybrid_algo=hybrid_algo,
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


    # ========================================================
    #  TRANG THÔNG TIN TÀI KHOẢN
    # ========================================================
    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            action = request.form.get("action")

            # ── Cập nhật thông tin cá nhân ──
            if action == "update_info":
                full_name = request.form.get("full_name", "").strip()
                email     = request.form.get("email", "").strip()

                if not email:
                    flash("Email không được để trống.", "error")
                    return redirect(url_for("profile"))

                # Kiểm tra email trùng với user khác
                existing = User.query.filter(
                    User.email == email,
                    User.id != current_user.id
                ).first()
                if existing:
                    flash("Email này đã được sử dụng bởi tài khoản khác.", "error")
                    return redirect(url_for("profile"))

                current_user.full_name = full_name
                current_user.email     = email
                db.session.commit()
                flash("Cập nhật thông tin thành công!", "success")

            # ── Đổi mật khẩu ──
            elif action == "change_password":
                current_pw  = request.form.get("current_password", "")
                new_pw      = request.form.get("new_password", "")
                confirm_pw  = request.form.get("confirm_password", "")

                if not check_password_hash(current_user.password_hash, current_pw):
                    flash("Mật khẩu hiện tại không đúng.", "error")
                    return redirect(url_for("profile"))

                if len(new_pw) < 6:
                    flash("Mật khẩu mới phải có ít nhất 6 ký tự.", "error")
                    return redirect(url_for("profile"))

                if new_pw != confirm_pw:
                    flash("Mật khẩu xác nhận không khớp.", "error")
                    return redirect(url_for("profile"))

                current_user.password_hash = generate_password_hash(new_pw)
                db.session.commit()
                flash("Đổi mật khẩu thành công!", "success")

            return redirect(url_for("profile"))

        # Thống kê tài khoản
        total_orders    = Order.query.filter_by(user_id=current_user.id).count()
        total_spent     = db.session.query(
            db.func.sum(Order.total_amount)
        ).filter(
            Order.user_id   == current_user.id,
            Order.status.in_(["confirmed", "shipped", "delivered"]),
        ).scalar() or 0
        total_reviews   = UserInteraction.query.filter(
            UserInteraction.user_id == current_user.id,
            UserInteraction.rating.isnot(None),
        ).count()
        recent_orders   = Order.query.filter_by(
            user_id=current_user.id
        ).order_by(Order.created_at.desc()).limit(5).all()

        return render_template(
            "profile.html",
            total_orders=total_orders,
            total_spent=total_spent,
            total_reviews=total_reviews,
            recent_orders=recent_orders,
        )

    # ========================================================
    #  THANH TOÁN LẠI CHO ĐƠN PENDING_PAYMENT
    # ========================================================
    @app.route("/order/<int:order_id>/retry-payment", methods=["GET", "POST"])
    @login_required
    def retry_payment(order_id):
        """Cho phép user thanh toán lại đơn hàng đang ở trạng thái pending_payment."""
        order = Order.query.get_or_404(order_id)

        # Chỉ user sở hữu đơn mới được retry
        if order.user_id != current_user.id:
            flash("Không có quyền truy cập.", "error")
            return redirect(url_for("order_history"))

        RETRYABLE_STATUSES = ("pending_payment", "payment_failed")
        if order.status not in RETRYABLE_STATUSES:
            flash("\u0110ơn hàng này không thể thanh toán lại.", "info")
            return redirect(url_for("order_history"))

        if request.method == "POST":
            method = request.form.get("method")

            # Lưu lại thông tin giao hàng vào session
            session["pending_order"] = {
                "full_name": order.full_name,
                "phone":     order.phone,
                "address":   order.address,
                "note":      order.note or "",
            }

            if method == "momo":
                pay_url, message = momo_create_payment(
                    order_id=order.id,
                    amount=order.total_amount,
                    order_info=f"Thanh toan don hang LUXE #{order.id}",
                )
                if pay_url:
                    session["momo_order_id"] = order.id
                    return redirect(pay_url)
                else:
                    flash(f"Không thể kết nối MoMo: {message}", "error")

            elif method == "vnpay":
                client_ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
                payment_url = vnpay_create_payment_url(
                    order_id=order.id,
                    amount=order.total_amount,
                    order_info=f"Thanh toan don hang LUXE #{order.id}",
                    client_ip=client_ip,
                )
                session["vnpay_order_id"] = order.id
                return redirect(payment_url)

            elif method == "cod":
                order.status         = "confirmed"
                order.payment_method = "cod"
                db.session.commit()

                # Xóa giỏ hàng + ghi interaction
                CartItem.query.filter_by(user_id=current_user.id).delete()
                for item in order.items:
                    db.session.add(UserInteraction(
                        user_id=current_user.id,
                        product_id=item.product_id,
                        interaction_type="purchase",
                        rating=5.0,
                    ))
                db.session.commit()
                recommendation_engine.invalidate_cache()
                session.pop("pending_order", None)

                flash("Đặt hàng thành công! Thanh toán khi nhận hàng.", "success")
                return render_template("order_success.html", order=order, payment_method="COD")

            return redirect(url_for("retry_payment", order_id=order_id))

        return render_template("retry_payment.html", order=order)


    @app.route("/order/<int:order_id>/cancel", methods=["POST"])
    @login_required
    def cancel_pending_order(order_id):
        """Cho phép user tự hủy đơn đang ở trạng thái pending_payment."""
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            flash("Không có quyền truy cập.", "error")
            return redirect(url_for("order_history"))
        RETRYABLE_STATUSES = ("pending_payment", "payment_failed")
        if order.status not in RETRYABLE_STATUSES:
            flash("Chỉ có thể hủy đơn hàng đang chờ thanh toán.", "warning")
            return redirect(url_for("order_history"))
        order.status = "cancelled"
        db.session.commit()
        flash(f"Đã hủy đơn hàng #{order.id}.", "success")
        return redirect(url_for("order_history"))

    # ========================================================
    #  ADMIN - DECORATOR & MIDDLEWARE
    # ========================================================
    from functools import wraps

    def admin_required(f):
        """Decorator: chỉ cho phép user có is_admin=True"""
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                flash("Bạn không có quyền truy cập trang này.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated

    # ========================================================
    #  ADMIN - DASHBOARD
    # ========================================================
    @app.route("/admin")
    @login_required
    @admin_required
    def admin_dashboard():
        from sqlalchemy import func
        from datetime import datetime, timedelta

        # Thống kê tổng quan
        stats = {
            "total_products": Product.query.count(),
            "total_users": User.query.count(),
            "total_orders": Order.query.count(),
            "total_revenue": db.session.query(func.sum(Order.total_amount)).scalar() or 0,
            "pending_orders": Order.query.filter_by(status="confirmed").count(),
            "total_interactions": UserInteraction.query.count(),
        }

        # Doanh thu 7 ngày gần nhất
        revenue_data = []
        for i in range(6, -1, -1):
            day = datetime.utcnow() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59)
            rev = db.session.query(func.sum(Order.total_amount)).filter(
                Order.created_at >= day_start,
                Order.created_at <= day_end,
            ).scalar() or 0
            revenue_data.append({
                "date": day.strftime("%d/%m"),
                "revenue": int(rev),
            })

        # Top 5 sản phẩm bán chạy
        top_products = db.session.query(
            Product,
            func.sum(OrderItem.quantity).label("total_sold"),
        ).join(OrderItem).group_by(Product.id).order_by(
            func.sum(OrderItem.quantity).desc()
        ).limit(5).all()

        # Đơn hàng mới nhất
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()

        return render_template(
            "admin/dashboard.html",
            stats=stats,
            revenue_data=revenue_data,
            top_products=top_products,
            recent_orders=recent_orders,
        )

    # ========================================================
    #  ADMIN - QUẢN LÝ SẢN PHẨM
    # ========================================================
    @app.route("/admin/products")
    @login_required
    @admin_required
    def admin_products():
        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "").strip()
        category_filter = request.args.get("category", "")

        query = Product.query
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))
        if category_filter:
            query = query.filter(Product.category_id == category_filter)

        products = query.order_by(Product.created_at.desc()).paginate(
            page=page, per_page=15, error_out=False
        )
        categories = Category.query.all()
        return render_template(
            "admin/products.html",
            products=products,
            categories=categories,
            search=search,
            category_filter=category_filter,
        )

    @app.route("/admin/products/create", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_product_create():
        categories = Category.query.all()
        if request.method == "POST":
            try:
                original_price_raw = request.form.get("original_price", "").strip()
                product = Product(
                    name=request.form.get("name", "").strip(),
                    description=request.form.get("description", "").strip(),
                    price=float(request.form.get("price", 0)),
                    original_price=float(original_price_raw) if original_price_raw else None,
                    image_url=request.form.get("image_url", "").strip(),
                    category_id=int(request.form.get("category_id")),
                    tags=request.form.get("tags", "").strip(),
                    gender=request.form.get("gender", "unisex"),
                    material=request.form.get("material", "").strip(),
                    style=request.form.get("style", "casual"),
                    is_featured=request.form.get("is_featured") == "on",
                    stock=int(request.form.get("stock", 50)),
                )
                db.session.add(product)
                db.session.commit()
                recommendation_engine.invalidate_cache()
                flash(f'Đã tạo sản phẩm "{product.name}" thành công!', "success")
                return redirect(url_for("admin_products"))
            except Exception as e:
                db.session.rollback()
                flash(f"Lỗi khi tạo sản phẩm: {str(e)}", "error")

        return render_template("admin/product_form.html", product=None, categories=categories)

    @app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_product_edit(product_id):
        product = Product.query.get_or_404(product_id)
        categories = Category.query.all()

        if request.method == "POST":
            try:
                original_price_raw = request.form.get("original_price", "").strip()
                product.name = request.form.get("name", "").strip()
                product.description = request.form.get("description", "").strip()
                product.price = float(request.form.get("price", 0))
                product.original_price = float(original_price_raw) if original_price_raw else None
                product.image_url = request.form.get("image_url", "").strip()
                product.category_id = int(request.form.get("category_id"))
                product.tags = request.form.get("tags", "").strip()
                product.gender = request.form.get("gender", "unisex")
                product.material = request.form.get("material", "").strip()
                product.style = request.form.get("style", "casual")
                product.is_featured = request.form.get("is_featured") == "on"
                product.stock = int(request.form.get("stock", 50))
                db.session.commit()
                recommendation_engine.invalidate_cache()
                flash(f'Đã cập nhật sản phẩm "{product.name}".', "success")
                return redirect(url_for("admin_products"))
            except Exception as e:
                db.session.rollback()
                flash(f"Lỗi khi cập nhật: {str(e)}", "error")

        return render_template("admin/product_form.html", product=product, categories=categories)

    @app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def admin_product_delete(product_id):
        product = Product.query.get_or_404(product_id)
        try:
            # Xóa các bản ghi liên quan trước
            CartItem.query.filter_by(product_id=product_id).delete()
            UserInteraction.query.filter_by(product_id=product_id).delete()
            name = product.name
            db.session.delete(product)
            db.session.commit()
            recommendation_engine.invalidate_cache()
            flash(f'Đã xóa sản phẩm "{name}".', "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Không thể xóa: {str(e)}", "error")
        return redirect(url_for("admin_products"))

    # ========================================================
    #  ADMIN - QUẢN LÝ DANH MỤC
    # ========================================================
    @app.route("/admin/categories")
    @login_required
    @admin_required
    def admin_categories():
        categories = Category.query.all()
        return render_template("admin/categories.html", categories=categories)

    @app.route("/admin/categories/create", methods=["POST"])
    @login_required
    @admin_required
    def admin_category_create():
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()
        description = request.form.get("description", "").strip()
        if not name or not slug:
            flash("Tên và slug không được để trống.", "error")
            return redirect(url_for("admin_categories"))
        if Category.query.filter_by(slug=slug).first():
            flash("Slug đã tồn tại.", "error")
            return redirect(url_for("admin_categories"))
        cat = Category(name=name, slug=slug, description=description)
        db.session.add(cat)
        db.session.commit()
        flash(f'Đã tạo danh mục "{name}".', "success")
        return redirect(url_for("admin_categories"))

    @app.route("/admin/categories/<int:cat_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def admin_category_delete(cat_id):
        cat = Category.query.get_or_404(cat_id)
        if cat.products:
            flash(f'Không thể xóa "{cat.name}" vì còn {len(cat.products)} sản phẩm.', "error")
            return redirect(url_for("admin_categories"))
        db.session.delete(cat)
        db.session.commit()
        flash(f'Đã xóa danh mục "{cat.name}".', "success")
        return redirect(url_for("admin_categories"))

    # ========================================================
    #  ADMIN - QUẢN LÝ ĐƠN HÀNG
    # ========================================================
    @app.route("/admin/orders")
    @login_required
    @admin_required
    def admin_orders():
        page = request.args.get("page", 1, type=int)
        status_filter = request.args.get("status", "")
        search = request.args.get("search", "").strip()

        query = Order.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if search:
            query = query.filter(
                db.or_(
                    Order.full_name.ilike(f"%{search}%"),
                    Order.phone.ilike(f"%{search}%"),
                )
            )
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=15, error_out=False
        )
        return render_template(
            "admin/orders.html",
            orders=orders,
            status_filter=status_filter,
            search=search,
        )

    @app.route("/admin/orders/<int:order_id>")
    @login_required
    @admin_required
    def admin_order_detail(order_id):
        order = Order.query.get_or_404(order_id)
        return render_template("admin/order_detail.html", order=order)

    @app.route("/admin/orders/<int:order_id>/update-status", methods=["POST"])
    @login_required
    @admin_required
    def admin_order_update_status(order_id):
        order = Order.query.get_or_404(order_id)
        new_status = request.form.get("status")
        valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
        if new_status not in valid_statuses:
            flash("Trạng thái không hợp lệ.", "error")
            return redirect(url_for("admin_order_detail", order_id=order_id))
        order.status = new_status
        db.session.commit()
        flash(f"Đã cập nhật trạng thái đơn hàng #{order.id} → {new_status}.", "success")
        return redirect(url_for("admin_order_detail", order_id=order_id))

    # ========================================================
    #  ADMIN - QUẢN LÝ NGƯỜI DÙNG
    # ========================================================
    @app.route("/admin/users")
    @login_required
    @admin_required
    def admin_users():
        from sqlalchemy import func
        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "").strip()

        query = User.query
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%"),
                )
            )
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=15, error_out=False
        )
        return render_template("admin/users.html", users=users, search=search)

    @app.route("/admin/users/<int:user_id>/toggle-admin", methods=["POST"])
    @login_required
    @admin_required
    def admin_user_toggle_admin(user_id):
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash("Không thể thay đổi quyền của chính mình.", "error")
            return redirect(url_for("admin_users"))
        user.is_admin = not user.is_admin
        db.session.commit()
        status = "Admin" if user.is_admin else "User"
        flash(f'Đã đổi quyền {user.username} → {status}.', "success")
        return redirect(url_for("admin_users"))

    # ========================================================
    #  ADMIN - THỐNG KÊ AI / RECOMMENDATION
    # ========================================================
    @app.route("/admin/ai-stats")
    @login_required
    @admin_required
    def admin_ai_stats():
        from sqlalchemy import func

        # Thống kê interaction theo loại
        interaction_stats = db.session.query(
            UserInteraction.interaction_type,
            func.count(UserInteraction.id).label("count"),
        ).group_by(UserInteraction.interaction_type).all()

        # Top sản phẩm được tương tác nhiều nhất
        top_interacted = db.session.query(
            Product,
            func.count(UserInteraction.id).label("interaction_count"),
        ).join(UserInteraction).group_by(Product.id).order_by(
            func.count(UserInteraction.id).desc()
        ).limit(10).all()

        # Rating trung bình theo sản phẩm
        avg_ratings = db.session.query(
            Product,
            func.avg(UserInteraction.rating).label("avg_rating"),
            func.count(UserInteraction.rating).label("rating_count"),
        ).join(UserInteraction).filter(
            UserInteraction.rating.isnot(None)
        ).group_by(Product.id).order_by(
            func.avg(UserInteraction.rating).desc()
        ).limit(10).all()

        # Số user có tương tác (có thể dùng CF)
        active_users = db.session.query(UserInteraction.user_id).distinct().count()

        stats = {
            "total_interactions": UserInteraction.query.count(),
            "active_users": active_users,
            "rated_interactions": UserInteraction.query.filter(UserInteraction.rating.isnot(None)).count(),
            "purchase_interactions": UserInteraction.query.filter_by(interaction_type="purchase").count(),
        }

        return render_template(
            "admin/ai_stats.html",
            interaction_stats=interaction_stats,
            top_interacted=top_interacted,
            avg_ratings=avg_ratings,
            stats=stats,
        )


    # ========================================================
    #  TRANG CHỌN PHƯƠNG THỨC THANH TOÁN
    # ========================================================
    @app.route("/checkout/payment", methods=["GET", "POST"])
    @login_required
    def checkout_payment():
        """
        Bước trung gian: sau khi nhập địa chỉ, chọn phương thức thanh toán.
        Lưu thông tin giao hàng vào session, chưa tạo Order.
        """
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash("Giỏ hàng trống!", "warning")
            return redirect(url_for("cart"))

        total = sum(item.product.price * item.quantity for item in cart_items)

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            phone     = request.form.get("phone", "").strip()
            address   = request.form.get("address", "").strip()
            note      = request.form.get("note", "").strip()

            if not full_name or not phone or not address:
                flash("Vui lòng điền đầy đủ thông tin giao hàng.", "error")
                return render_template("checkout_payment.html", cart_items=cart_items, total=total)

            # Lưu tạm vào session, chờ chọn phương thức thanh toán
            session["pending_order"] = {
                "full_name": full_name,
                "phone":     phone,
                "address":   address,
                "note":      note,
            }
            return render_template("checkout_payment.html",
                                   cart_items=cart_items,
                                   total=total,
                                   show_methods=True,
                                   shipping_info=session["pending_order"])

        return render_template("checkout_payment.html", cart_items=cart_items, total=total)

    # ========================================================
    #  VNPAY - TẠO URL THANH TOÁN
    # ========================================================
    @app.route("/payment/vnpay/create", methods=["POST"])
    @login_required
    def vnpay_create():
        pending = session.get("pending_order")
        if not pending:
            flash("Phiên đặt hàng đã hết hạn, vui lòng thử lại.", "warning")
            return redirect(url_for("checkout_payment"))

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash("Giỏ hàng trống!", "warning")
            return redirect(url_for("cart"))

        total = sum(item.product.price * item.quantity for item in cart_items)

        # Tái sử dụng pending_payment order nếu đã có (tránh tạo đơn trùng khi quay lại)
        existing_order = Order.query.filter_by(
            user_id=current_user.id,
            status="pending_payment",
        ).order_by(Order.created_at.desc()).first()

        if existing_order:
            OrderItem.query.filter_by(order_id=existing_order.id).delete()
            existing_order.total_amount = total
            existing_order.full_name    = pending["full_name"]
            existing_order.phone        = pending["phone"]
            existing_order.address      = pending["address"]
            existing_order.note         = pending.get("note", "")
            order = existing_order
            db.session.flush()
        else:
            order = Order(
                user_id=current_user.id,
                total_amount=total,
                status="pending_payment",
                full_name=pending["full_name"],
                phone=pending["phone"],
                address=pending["address"],
                note=pending.get("note", ""),
            )
            db.session.add(order)
            db.session.flush()

        for item in cart_items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price,
            ))

        # Xóa giỏ hàng ngay khi tạo đơn — dù thanh toán thành công hay thất bại
        # cart sẽ không còn nữa và đơn sẽ xuất hiện trong "Đơn hàng của tôi"
        CartItem.query.filter_by(user_id=current_user.id).delete()

        db.session.commit()

        # Lưu order_id vào session để xử lý khi VNPay callback
        session["vnpay_order_id"] = order.id

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        payment_url = vnpay_create_payment_url(
            order_id=order.id,
            amount=total,
            order_info=f"Thanh toan don hang LUXE #{order.id}",
            client_ip=client_ip,
        )

        return redirect(payment_url)

    # ========================================================
    #  VNPAY - XỬ LÝ KẾT QUẢ RETURN
    # ========================================================
    @app.route("/payment/vnpay/return")
    def vnpay_return():
        params = request.args.to_dict()
        is_valid, response_code, order_id_str = vnpay_verify_return(params)

        try:
            order_id = int(order_id_str)
        except (ValueError, TypeError):
            flash("Thông tin đơn hàng không hợp lệ.", "error")
            return redirect(url_for("index"))

        order = Order.query.get(order_id)
        if not order:
            flash("Không tìm thấy đơn hàng.", "error")
            return redirect(url_for("index"))

        if is_valid and response_code == "00":
            # Thanh toán thành công
            order.status = "confirmed"
            order.payment_method = "vnpay"

            # Xóa giỏ hàng + interaction
            CartItem.query.filter_by(user_id=order.user_id).delete()
            for item in order.items:
                db.session.add(UserInteraction(
                    user_id=order.user_id,
                    product_id=item.product_id,
                    interaction_type="purchase",
                    rating=5.0,
                ))
            db.session.commit()
            recommendation_engine.invalidate_cache()
            session.pop("pending_order", None)
            session.pop("vnpay_order_id", None)

            flash("Thanh toán VNPay thành công!", "success")
            return render_template("order_success.html", order=order, payment_method="VNPay")

        else:
            # Thanh toán thất bại / bị hủy → đánh dấu payment_failed
            # Giỏ hàng đã bị xóa từ lúc tạo đơn, đơn hàng vẫn ở trong lịch sử
            reason = VNPAY_RESPONSE_CODES.get(response_code, "Giao dịch thất bại")
            order.status = "payment_failed"
            order.payment_method = "vnpay"
            db.session.commit()
            session.pop("pending_order", None)
            session.pop("vnpay_order_id", None)
            if response_code == "24":
                flash(f"Bạn đã hủy thanh toán VNPay. Đơn hàng #{order.id} đã được lưu — bạn có thể thanh toán lại.", "warning")
            else:
                flash(f"Thanh toán VNPay thất bại: {reason}. Đơn hàng #{order.id} đã được lưu — bạn có thể thanh toán lại.", "error")
            return redirect(url_for("order_history"))

    # ========================================================
    #  MOMO - TẠO LINK THANH TOÁN
    # ========================================================
    @app.route("/payment/momo/create", methods=["POST"])
    @login_required
    def momo_create():
        pending = session.get("pending_order")
        if not pending:
            flash("Phiên đặt hàng đã hết hạn, vui lòng thử lại.", "warning")
            return redirect(url_for("checkout_payment"))

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash("Giỏ hàng trống!", "warning")
            return redirect(url_for("cart"))

        total = sum(item.product.price * item.quantity for item in cart_items)

        # Kiểm tra đã có pending_payment order chưa → tái sử dụng thay vì tạo mới
        # Tránh tình huống user hủy MoMo rồi thử lại → đơn hàng tăng lên
        existing_order = Order.query.filter_by(
            user_id=current_user.id,
            status="pending_payment",
        ).order_by(Order.created_at.desc()).first()

        if existing_order:
            # Xóa order items cũ và tạo lại theo giỏ hàng hiện tại
            OrderItem.query.filter_by(order_id=existing_order.id).delete()
            existing_order.total_amount = total
            existing_order.full_name    = pending["full_name"]
            existing_order.phone        = pending["phone"]
            existing_order.address      = pending["address"]
            existing_order.note         = pending.get("note", "")
            order = existing_order
            db.session.flush()
        else:
            order = Order(
                user_id=current_user.id,
                total_amount=total,
                status="pending_payment",
                full_name=pending["full_name"],
                phone=pending["phone"],
                address=pending["address"],
                note=pending.get("note", ""),
            )
            db.session.add(order)
            db.session.flush()

        for item in cart_items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price,
            ))

        # Xóa giỏ hàng ngay khi tạo đơn — dù thanh toán thành công hay thất bại
        # cart sẽ không còn nữa và đơn sẽ xuất hiện trong "Đơn hàng của tôi"
        CartItem.query.filter_by(user_id=current_user.id).delete()

        db.session.commit()
        session["momo_order_id"] = order.id

        pay_url, message = momo_create_payment(
            order_id=order.id,
            amount=total,
            order_info=f"Thanh toan don hang LUXE #{order.id}",
        )

        if pay_url:
            return redirect(pay_url)
        else:
            order.status = "payment_failed"
            db.session.commit()
            flash(f"Không thể kết nối MoMo: {message}. Đơn hàng #{order.id} đã được lưu.", "error")
            return redirect(url_for("order_history"))

    # ========================================================
    #  MOMO - XỬ LÝ KẾT QUẢ RETURN
    # ========================================================
    @app.route("/payment/momo/return")
    def momo_return():
        params = request.args.to_dict()
        is_valid, result_code, order_id_str = momo_verify_return(params)

        try:
            order_id = int(order_id_str)
        except (ValueError, TypeError):
            flash("Thông tin đơn hàng không hợp lệ.", "error")
            return redirect(url_for("index"))

        order = Order.query.get(order_id)
        if not order:
            flash("Không tìm thấy đơn hàng.", "error")
            return redirect(url_for("index"))

        if result_code == 0:
            order.status = "confirmed"
            order.payment_method = "momo"

            CartItem.query.filter_by(user_id=order.user_id).delete()
            for item in order.items:
                db.session.add(UserInteraction(
                    user_id=order.user_id,
                    product_id=item.product_id,
                    interaction_type="purchase",
                    rating=5.0,
                ))
            db.session.commit()
            recommendation_engine.invalidate_cache()
            session.pop("pending_order", None)
            session.pop("momo_order_id", None)

            flash("Thanh toán MoMo thành công!", "success")
            return render_template("order_success.html", order=order, payment_method="MoMo")

        else:
            # Giữ pending_payment để user có thể thanh toán lại
            order.status = "pending_payment"
            db.session.commit()
            session.pop("momo_order_id", None)

            # MoMo result_code 49 = user chủ động hủy
            if result_code == 49:
                flash("Bạn đã hủy thanh toán MoMo. Đơn hàng vẫn được giữ lại — bạn có thể thanh toán lại.", "warning")
            else:
                flash("Thanh toán MoMo thất bại. Đơn hàng vẫn được giữ lại — bạn có thể thanh toán lại.", "error")
            # Redirect thẳng đến trang retry_payment để tiện thanh toán lại
            return redirect(url_for("retry_payment", order_id=order.id))

    # ========================================================
    #  MOMO - IPN (server-to-server notify, tùy chọn)
    # ========================================================
    @app.route("/payment/momo/notify", methods=["POST"])
    def momo_notify():
        """MoMo gọi endpoint này server-to-server để xác nhận giao dịch."""
        try:
            data = request.get_json()
            _, result_code, order_id_str = momo_verify_return(data)
            order = Order.query.get(int(order_id_str))
            if order and result_code == 0 and order.status == "pending_payment":
                order.status = "confirmed"
                order.payment_method = "momo"
                db.session.commit()
            return jsonify({"status": "ok"}), 200
        except Exception:
            return jsonify({"status": "error"}), 400

    return app


# ========================================================
#  CHẠY ỨNG DỤNG
# ========================================================
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
