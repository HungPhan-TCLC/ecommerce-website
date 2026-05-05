"""
blueprints/product/routes.py - Chi tiết sản phẩm & danh mục
"""

from flask import Blueprint, render_template, request
from flask_login import current_user
from models import db, Product, Category, UserInteraction
from recommendation import recommendation_engine

product_bp = Blueprint("product", __name__)

# Các nguồn hợp lệ cho online metrics tracking
VALID_SOURCES = {"recommendation", "search", "category", "homepage", "direct"}


@product_bp.route("/category/<slug>")
def category_products(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    products = Product.query.filter_by(category_id=category.id).paginate(page=page, per_page=32, error_out=False)
    return render_template("product/category.html", category=category, products=products)


@product_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)

    # Lấy source từ query param để tracking online metrics
    # Ví dụ: /product/5?source=recommendation
    source = request.args.get("source", "direct")
    if source not in VALID_SOURCES:
        source = "direct"

    # Ghi nhận lượt xem (cho recommendation + online metrics)
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
                source=source,
            )
            db.session.add(interaction)
            db.session.commit()
        elif source == "recommendation" and existing.source != "recommendation":
            # Cập nhật source nếu lần này đến từ recommendation (ưu tiên hơn)
            existing.source = "recommendation"
            db.session.commit()

    similar_products = recommendation_engine.get_similar_products(product_id, top_n=4)
    also_bought = recommendation_engine.get_also_bought(product_id, top_n=4)

    # Tính lý do gợi ý cho từng section
    uid = current_user.id if current_user.is_authenticated else 0

    similar_reasons = recommendation_engine.get_recommendation_reasons(
        user_id=uid,
        product_ids=[p.id for p in similar_products],
        algorithm="content_based",
    ) if similar_products else {}

    also_bought_reasons = recommendation_engine.get_recommendation_reasons(
        user_id=uid,
        product_ids=[p.id for p in also_bought],
        algorithm="popular",
    ) if also_bought else {}

    return render_template(
        "product/detail.html",
        product=product,
        similar_products=similar_products,
        also_bought=also_bought,
        similar_reasons=similar_reasons,
        also_bought_reasons=also_bought_reasons,
    )
