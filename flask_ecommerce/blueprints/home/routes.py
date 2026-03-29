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

    if current_user.is_authenticated:
        personalized = recommendation_engine.get_personalized_recommendations(
            current_user.id, top_n=8
        )
    else:
        personalized = recommendation_engine._get_popular_products(top_n=8)

    return render_template(
        "home/index.html",
        featured_products=featured_products,
        new_products=new_products,
        personalized=personalized,
    )
