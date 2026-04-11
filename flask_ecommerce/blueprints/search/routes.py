"""
blueprints/search/routes.py - Tìm kiếm sản phẩm
"""

from flask import Blueprint, render_template, request
from models import db, Product, Category
import re

search_bp = Blueprint("search", __name__)

# Mapping từ khóa giới tính để tự động điều chỉnh bộ lọc
GENDER_KEYWORDS = {
    "nam": "nam",
    "nữ": "nu",
    "nu": "nu",
    "unisex": "unisex",
}

# Chuẩn hóa dấu tiếng Việt đơn giản (chỉ dùng cho gender detection)
GENDER_NORM = {
    "nữ": "nu", "nu": "nu",
    "nam": "nam",
    "unisex": "unisex",
}


def _build_product_query(q, category_filter, gender_filter, style_filter,
                          price_min, price_max, sort_by):
    """Xây dựng SQLAlchemy query tìm kiếm sản phẩm nâng cao."""

    product_query = Product.query.join(Category, Product.category_id == Category.id)

    # ── Tìm kiếm theo từ khóa ──
    if q:
        q_lower = q.lower().strip()

        # Tách thành các token riêng lẻ (bỏ từ rỗng)
        tokens = [t for t in re.split(r"[\s,]+", q_lower) if t]

        # Kiểm tra nếu cụm từ nguyên văn khớp trước (ưu tiên cao nhất)
        full_term = f"%{q}%"

        # Xây dựng điều kiện OR cho toàn bộ cụm từ
        full_phrase_cond = db.or_(
            Product.name.ilike(full_term),
            Product.description.ilike(full_term),
            Product.tags.ilike(full_term),
            Category.name.ilike(full_term),
            Category.description.ilike(full_term),
        )

        if len(tokens) > 1:
            # Multi-token: mỗi token phải khớp ít nhất một trường (AND giữa các token)
            token_conditions = []
            for tok in tokens:
                t = f"%{tok}%"
                token_conditions.append(
                    db.or_(
                        Product.name.ilike(t),
                        Product.description.ilike(t),
                        Product.tags.ilike(t),
                        Category.name.ilike(t),
                        Category.description.ilike(t),
                        # Tìm theo giới tính nếu token là từ khóa giới tính
                        Product.gender.ilike(t) if tok in GENDER_NORM else db.false(),
                        Product.style.ilike(t),
                    )
                )
            # Kết hợp: khớp cụm nguyên văn OR (tất cả các token đều khớp)
            multi_token_cond = db.and_(*token_conditions)
            product_query = product_query.filter(
                db.or_(full_phrase_cond, multi_token_cond)
            )
        else:
            # Single token: tìm trong tất cả trường
            single_tok = tokens[0] if tokens else q_lower
            t = f"%{single_tok}%"
            product_query = product_query.filter(
                db.or_(
                    full_phrase_cond,
                    Product.name.ilike(t),
                    Product.description.ilike(t),
                    Product.tags.ilike(t),
                    Category.name.ilike(t),
                    Category.description.ilike(t),
                    Product.gender.ilike(t),
                    Product.material.ilike(t),
                    Product.style.ilike(t),
                )
            )

        # Tự động áp dụng gender filter nếu từ khóa chứa từ giới tính
        # nhưng chưa có gender_filter được chọn rõ ràng
        if not gender_filter:
            for kw, gval in GENDER_NORM.items():
                if kw in q_lower:
                    gender_filter = gval
                    break

    # ── Lọc theo danh mục ──
    if category_filter:
        try:
            product_query = product_query.filter(
                Product.category_id == int(category_filter)
            )
        except ValueError:
            pass

    # ── Lọc theo giới tính ──
    if gender_filter in ("nam", "nu", "unisex"):
        product_query = product_query.filter(Product.gender == gender_filter)

    # ── Lọc theo phong cách ──
    if style_filter:
        product_query = product_query.filter(
            Product.style.ilike(f"%{style_filter}%")
        )

    # ── Lọc theo giá ──
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
        product_query = product_query.order_by(Product.name.asc())

    return product_query, gender_filter


@search_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()

    category_filter = request.args.get("category", "").strip()
    gender_param    = request.args.get("gender", "").strip()  # Giá trị user chọn thủ công
    gender_filter   = gender_param  # Có thể được auto-detect thêm khi q chứa từ ngữ giới tính
    style_filter    = request.args.get("style", "").strip()
    price_min_raw   = request.args.get("price_min", "").strip()
    price_max_raw   = request.args.get("price_max", "").strip()
    sort_by         = request.args.get("sort", "relevant")
    page            = request.args.get("page", 1, type=int)

    try:
        price_min = float(price_min_raw) if price_min_raw else None
    except ValueError:
        price_min = None
    try:
        price_max = float(price_max_raw) if price_max_raw else None
    except ValueError:
        price_max = None

    product_query, gender_filter = _build_product_query(
        q, category_filter, gender_filter, style_filter,
        price_min, price_max, sort_by
    )

    pagination = product_query.paginate(page=page, per_page=32, error_out=False)
    products   = pagination.items

    all_categories_full = Category.query.order_by(Category.name).all()

    # Lọc danh mục theo từ khóa: chỉ hiển thị danh mục liên quan
    if q:
        q_tokens = [t for t in re.split(r"[\s,]+", q.lower()) if t]
        def _cat_matches(cat):
            cat_text = (cat.name + " " + (cat.description or "")).lower()
            return any(tok in cat_text for tok in q_tokens)
        filtered_categories = [c for c in all_categories_full if _cat_matches(c)]
        # Nếu không có danh mục nào khớp thì hiện tất cả
        all_categories = filtered_categories if filtered_categories else all_categories_full
    else:
        all_categories = all_categories_full
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
    # Chỉ hiện badge gender khi user chọn thủ công (không phải auto-detect)
    if gender_param:
        label_map = {"nam": "Nam", "nu": "Nữ", "unisex": "Unisex"}
        active_filters["gender"] = {"label": label_map.get(gender_param, gender_param), "value": gender_param}
    if style_filter:
        active_filters["style"] = {"label": style_filter.capitalize(), "value": style_filter}
    if price_min is not None:
        active_filters["price_min"] = {"label": f"Từ {int(price_min):,}₫".replace(",", "."), "value": price_min_raw}
    if price_max is not None:
        active_filters["price_max"] = {"label": f"Đến {int(price_max):,}₫".replace(",", "."), "value": price_max_raw}

    return render_template(
        "search/search.html",
        products=products,
        pagination=pagination,
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
