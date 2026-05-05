"""
blueprints/home/routes.py - Trang chủ
"""

from flask import Blueprint, render_template
from flask_login import current_user
from models import Product
from recommendation import recommendation_engine

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    featured_products = Product.query.filter_by(is_featured=True).limit(8).all()
    new_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()

    rec_algo = "popular"  # default cho user chưa đăng nhập
    if current_user.is_authenticated:
        # Dùng get_hybrid_recommendations() để có switching logic:
        # - user mới (< CF_MIN_INTERACTIONS=3) → Content-based Filtering
        # - user có lịch sử               → Collaborative Filtering
        personalized, rec_algo = recommendation_engine.get_hybrid_recommendations(
            current_user.id, top_n=8
        )
    else:
        personalized = recommendation_engine._get_popular_products(top_n=8)

    # Tính lý do gợi ý cho từng sản phẩm personalized
    rec_reasons = {}
    if personalized:
        uid = current_user.id if current_user.is_authenticated else 0
        rec_reasons = recommendation_engine.get_recommendation_reasons(
            user_id=uid,
            product_ids=[p.id for p in personalized],
            algorithm=rec_algo,
        )

    return render_template(
        "home/index.html",
        featured_products=featured_products,
        new_products=new_products,
        personalized=personalized,
        rec_algo=rec_algo,
        personalized_reasons=rec_reasons,
    )
