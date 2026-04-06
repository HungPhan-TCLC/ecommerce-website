"""
blueprints/api/routes.py - API endpoints (JSON responses)
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Product, UserInteraction
from recommendation import recommendation_engine

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/rate/<int:product_id>", methods=["POST"])
@login_required
def rate_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    if not data or "rating" not in data:
        return jsonify({"success": False, "error": "Missing rating"}), 400

    rating = float(data["rating"])
    if rating < 1 or rating > 5:
        return jsonify({"success": False, "error": "Rating must be 1-5"}), 400

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


@api_bp.route("/recommendations/personalized")
@login_required
def api_personalized():
    recs = recommendation_engine.get_personalized_recommendations(current_user.id, top_n=8)
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


@api_bp.route("/recommendations/similar/<int:product_id>")
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


@api_bp.route("/recommendations/also-bought/<int:product_id>")
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
