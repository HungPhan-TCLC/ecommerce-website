"""
blueprints/search/routes.py - Tìm kiếm sản phẩm
"""

from flask import Blueprint, render_template, request
from models import db, Product, Category

search_bp = Blueprint("search", __name__)


@search_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()

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

    product_query = Product.query

    if q:
        search_term = f"%{q}%"
        product_query = product_query.filter(
            db.or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
                Product.tags.ilike(search_term),
            )
        )

    if category_filter:
        try:
            product_query = product_query.filter(
                Product.category_id == int(category_filter)
            )
        except ValueError:
            pass

    if gender_filter in ("nam", "nu", "unisex"):
        product_query = product_query.filter(Product.gender == gender_filter)

    if style_filter:
        product_query = product_query.filter(
            Product.style.ilike(f"%{style_filter}%")
        )

    if price_min is not None:
        product_query = product_query.filter(Product.price >= price_min)
    if price_max is not None:
        product_query = product_query.filter(Product.price <= price_max)

    if sort_by == "price_asc":
        product_query = product_query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        product_query = product_query.order_by(Product.price.desc())
    elif sort_by == "newest":
        product_query = product_query.order_by(Product.created_at.desc())
    else:
        product_query = product_query.order_by(Product.name.asc())

    products = product_query.all()

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
        "search/search.html",
        products=products,
        query=q,
        all_categories=all_categories,
        gender_options=gender_options,
        style_options=style_options,
        active_filters=active_filters,
        category_filter=category_filter,
        gender_filter=gender_filter,
        style_filter=style_filter,
        price_min=price_min_raw,
        price_max=price_max_raw,
        sort_by=sort_by,
    )
