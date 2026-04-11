"""
blueprints/recommendations/routes.py - Trang gợi ý AI
"""

from flask import Blueprint, render_template
from flask_login import current_user
from models import db, Product, User, Order, UserInteraction
from recommendation import recommendation_engine

recommendations_bp = Blueprint("recommendations", __name__)


@recommendations_bp.route("/recommendations")
def recommendations():
    stats = {
        "total_products":    Product.query.count(),
        "total_users":       User.query.count(),
        "total_interactions": UserInteraction.query.count(),
        "total_orders":      Order.query.count(),
    }

    personalized = []
    personalized_algo = "popular"  # default cho user chưa đăng nhập
    user_stats = {"views": 0, "carts": 0, "purchases": 0, "total_interactions": 0}
    rated_products = []

    if current_user.is_authenticated:
        # Dùng get_hybrid_recommendations() để có switching logic:
        # - user mới (<3 interactions) → Content-based
        # - user có lịch sử           → Collaborative Filtering
        personalized, personalized_algo = recommendation_engine.get_hybrid_recommendations(
            current_user.id, top_n=8
        )
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

    sample_product = Product.query.filter_by(is_featured=True).first()
    similar_products = []
    also_bought = []
    if sample_product:
        similar_products = recommendation_engine.get_similar_products(sample_product.id, top_n=4)
        also_bought = recommendation_engine.get_also_bought(sample_product.id, top_n=4)

    popular = recommendation_engine._get_popular_products(top_n=8)

    # Hybrid section dùng lại dữ liệu đã tính từ get_hybrid_recommendations() ở trên
    # để tránh tính 2 lần
    hybrid_products = personalized
    hybrid_algo = personalized_algo

    return render_template(
        "recommendations/recommendations.html",
        stats=stats,
        personalized=personalized,
        personalized_algo=personalized_algo,
        user_stats=user_stats,
        rated_products=rated_products,
        sample_product=sample_product,
        similar_products=similar_products,
        also_bought=also_bought,
        popular=popular,
        hybrid_products=hybrid_products,
        hybrid_algo=hybrid_algo,
        # Source tag: template sẽ gắn ?source=recommendation vào mọi link product
        source_tag="recommendation",
    )

