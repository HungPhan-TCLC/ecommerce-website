"""
blueprints/cart/routes.py - Giỏ hàng
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Product, CartItem, UserInteraction

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/cart")
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template("cart/cart.html", cart_items=cart_items, total=total)


@cart_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get("quantity", 1))

    if quantity < 1:
        quantity = 1

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

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({"success": True, "cart_count": cart_count})

    return redirect(request.referrer or url_for("home.index"))


@cart_bp.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash("Không có quyền truy cập.", "error")
        return redirect(url_for("cart.cart"))

    quantity = int(request.form.get("quantity", 1))
    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity
    db.session.commit()

    return redirect(url_for("cart.cart"))


@cart_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash("Không có quyền truy cập.", "error")
        return redirect(url_for("cart.cart"))

    db.session.delete(cart_item)
    db.session.commit()
    flash("Đã xóa sản phẩm khỏi giỏ hàng.", "success")
    return redirect(url_for("cart.cart"))
