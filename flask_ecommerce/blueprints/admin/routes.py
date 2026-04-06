"""
bluprints/admin/routes.py - Khu vực quản trị Admin
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Product, Category, Order, OrderItem, User, CartItem, UserInteraction, EvaluationResult
from recommendation import recommendation_engine

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator: chỉ cho phép user có is_admin=True"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Bạn không có quyền truy cập trang này.", "error")
            return redirect(url_for("home.index"))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────

@admin_bp.route("")
@login_required
@admin_required
def admin_dashboard():
    from sqlalchemy import func
    from datetime import datetime, timedelta

    stats = {
        "total_products":    Product.query.count(),
        "total_users":       User.query.count(),
        "total_orders":      Order.query.count(),
        "total_revenue":     db.session.query(func.sum(Order.total_amount)).scalar() or 0,
        "pending_orders":    Order.query.filter_by(status="confirmed").count(),
        "total_interactions": UserInteraction.query.count(),
    }

    revenue_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day.replace(hour=23, minute=59, second=59)
        rev = db.session.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end,
        ).scalar() or 0
        revenue_data.append({"date": day.strftime("%d/%m"), "revenue": int(rev)})

    top_products = db.session.query(
        Product,
        func.sum(OrderItem.quantity).label("total_sold"),
    ).join(OrderItem).group_by(Product.id).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(5).all()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        revenue_data=revenue_data,
        top_products=top_products,
        recent_orders=recent_orders,
    )


# ── Sản phẩm ──────────────────────────────────────────────

@admin_bp.route("/products")
@login_required
@admin_required
def admin_products():
    page            = request.args.get("page", 1, type=int)
    search          = request.args.get("search", "").strip()
    category_filter = request.args.get("category", "")

    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if category_filter:
        query = query.filter(Product.category_id == category_filter)

    products   = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    categories = Category.query.all()

    return render_template(
        "admin/products.html",
        products=products,
        categories=categories,
        search=search,
        category_filter=category_filter,
    )


@admin_bp.route("/products/create", methods=["GET", "POST"])
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
            return redirect(url_for("admin.admin_products"))
        except Exception as e:
            db.session.rollback()
            flash(f"Lỗi khi tạo sản phẩm: {str(e)}", "error")

    return render_template("admin/product_form.html", product=None, categories=categories)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_product_edit(product_id):
    product    = Product.query.get_or_404(product_id)
    categories = Category.query.all()

    if request.method == "POST":
        try:
            original_price_raw   = request.form.get("original_price", "").strip()
            product.name         = request.form.get("name", "").strip()
            product.description  = request.form.get("description", "").strip()
            product.price        = float(request.form.get("price", 0))
            product.original_price = float(original_price_raw) if original_price_raw else None
            product.image_url    = request.form.get("image_url", "").strip()
            product.category_id  = int(request.form.get("category_id"))
            product.tags         = request.form.get("tags", "").strip()
            product.gender       = request.form.get("gender", "unisex")
            product.material     = request.form.get("material", "").strip()
            product.style        = request.form.get("style", "casual")
            product.is_featured  = request.form.get("is_featured") == "on"
            product.stock        = int(request.form.get("stock", 50))
            db.session.commit()
            recommendation_engine.invalidate_cache()
            flash(f'Đã cập nhật sản phẩm "{product.name}".', "success")
            return redirect(url_for("admin.admin_products"))
        except Exception as e:
            db.session.rollback()
            flash(f"Lỗi khi cập nhật: {str(e)}", "error")

    return render_template("admin/product_form.html", product=product, categories=categories)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    try:
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
    return redirect(url_for("admin.admin_products"))


# ── Danh mục ──────────────────────────────────────────────

@admin_bp.route("/categories")
@login_required
@admin_required
def admin_categories():
    categories = Category.query.all()
    return render_template("admin/categories.html", categories=categories)


@admin_bp.route("/categories/create", methods=["POST"])
@login_required
@admin_required
def admin_category_create():
    name        = request.form.get("name", "").strip()
    slug        = request.form.get("slug", "").strip()
    description = request.form.get("description", "").strip()

    if not name or not slug:
        flash("Tên và slug không được để trống.", "error")
        return redirect(url_for("admin.admin_categories"))

    if Category.query.filter_by(slug=slug).first():
        flash("Slug đã tồn tại.", "error")
        return redirect(url_for("admin.admin_categories"))

    db.session.add(Category(name=name, slug=slug, description=description))
    db.session.commit()
    flash(f'Đã tạo danh mục "{name}".', "success")
    return redirect(url_for("admin.admin_categories"))


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_category_delete(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.products:
        flash(f'Không thể xóa "{cat.name}" vì còn {len(cat.products)} sản phẩm.', "error")
        return redirect(url_for("admin.admin_categories"))
    db.session.delete(cat)
    db.session.commit()
    flash(f'Đã xóa danh mục "{cat.name}".', "success")
    return redirect(url_for("admin.admin_categories"))


# ── Đơn hàng ──────────────────────────────────────────────

@admin_bp.route("/orders")
@login_required
@admin_required
def admin_orders():
    page          = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    search        = request.args.get("search", "").strip()

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

    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template(
        "admin/orders.html",
        orders=orders,
        status_filter=status_filter,
        search=search,
    )


@admin_bp.route("/orders/<int:order_id>")
@login_required
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/order_detail.html", order=order)


@admin_bp.route("/orders/<int:order_id>/update-status", methods=["POST"])
@login_required
@admin_required
def admin_order_update_status(order_id):
    order      = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]

    if new_status not in valid_statuses:
        flash("Trạng thái không hợp lệ.", "error")
        return redirect(url_for("admin.admin_order_detail", order_id=order_id))

    order.status = new_status
    db.session.commit()
    flash(f"Đã cập nhật trạng thái đơn hàng #{order.id} → {new_status}.", "success")
    return redirect(url_for("admin.admin_order_detail", order_id=order_id))


# ── Người dùng ────────────────────────────────────────────

@admin_bp.route("/users")
@login_required
@admin_required
def admin_users():
    page   = request.args.get("page", 1, type=int)
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

    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template("admin/users.html", users=users, search=search)


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def admin_user_toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Không thể thay đổi quyền của chính mình.", "error")
        return redirect(url_for("admin.admin_users"))

    user.is_admin = not user.is_admin
    db.session.commit()
    status = "Admin" if user.is_admin else "User"
    flash(f'Đã đổi quyền {user.username} → {status}.', "success")
    return redirect(url_for("admin.admin_users"))


# ── AI Stats ──────────────────────────────────────────────

@admin_bp.route("/ai-stats")
@login_required
@admin_required
def admin_ai_stats():
    from sqlalchemy import func

    interaction_stats = db.session.query(
        UserInteraction.interaction_type,
        func.count(UserInteraction.id).label("count"),
    ).group_by(UserInteraction.interaction_type).all()

    top_interacted = db.session.query(
        Product,
        func.count(UserInteraction.id).label("interaction_count"),
    ).join(UserInteraction).group_by(Product.id).order_by(
        func.count(UserInteraction.id).desc()
    ).limit(10).all()

    avg_ratings = db.session.query(
        Product,
        func.avg(UserInteraction.rating).label("avg_rating"),
        func.count(UserInteraction.rating).label("rating_count"),
    ).join(UserInteraction).filter(
        UserInteraction.rating.isnot(None)
    ).group_by(Product.id).order_by(
        func.avg(UserInteraction.rating).desc()
    ).limit(10).all()

    active_users = db.session.query(UserInteraction.user_id).distinct().count()

    stats = {
        "total_interactions":  UserInteraction.query.count(),
        "active_users":        active_users,
        "rated_interactions":  UserInteraction.query.filter(UserInteraction.rating.isnot(None)).count(),
        "purchase_interactions": UserInteraction.query.filter_by(interaction_type="purchase").count(),
    }

    # ── Load kết quả evaluation gần nhất ───────────────────────────────────────────
    latest_run_id = None
    eval_results  = {}    # {algorithm: {metric_name: value}}
    eval_computed_at = None
    eval_num_users   = None
    eval_k           = None
    online_metrics   = {}

    # Lấy run_id mới nhất
    latest = EvaluationResult.query.order_by(EvaluationResult.computed_at.desc()).first()
    if latest:
        latest_run_id    = latest.run_id
        eval_computed_at = latest.computed_at
        eval_num_users   = latest.num_users_evaluated
        eval_k           = latest.k_value

        batch = EvaluationResult.query.filter_by(run_id=latest_run_id).all()
        for row in batch:
            if row.algorithm == "all":
                online_metrics[row.metric_name] = row.metric_value
            else:
                if row.algorithm not in eval_results:
                    eval_results[row.algorithm] = {}
                eval_results[row.algorithm][row.metric_name] = round(row.metric_value, 4)

    return render_template(
        "admin/ai_stats.html",
        interaction_stats=interaction_stats,
        top_interacted=top_interacted,
        avg_ratings=avg_ratings,
        stats=stats,
        # Evaluation results
        eval_results=eval_results,
        online_metrics=online_metrics,
        eval_computed_at=eval_computed_at,
        eval_num_users=eval_num_users,
        eval_k=eval_k,
        has_eval=bool(latest_run_id),
    )


@admin_bp.route("/ai-stats/run-evaluation", methods=["POST"])
@login_required
@admin_required
def admin_run_evaluation():
    """
    Trigger offline + online evaluation.
    Admin click nút → chạy RecommendationEvaluator.run_full_evaluation(k=8)
    → lưu vào DB → redirect về ai-stats với kết quả mới.
    """
    try:
        from evaluation import recommendation_evaluator
        results = recommendation_evaluator.run_full_evaluation(k=8)
        num_users = results["offline"]["precision_recall"].get("num_users", 0)
        flash(
            f"✅ Đã chạy đánh giá thành công! Run ID: {results['run_id']} | "
            f"Evaluated {num_users} users | K=8",
            "success"
        )
    except Exception as exc:
        flash(f"❌ Lỗi khi chạy đánh giá: {str(exc)}", "error")

    return redirect(url_for("admin.admin_ai_stats"))
