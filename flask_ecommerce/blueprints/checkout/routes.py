"""
blueprints/checkout/routes.py - Checkout & Payment (VNPay, MoMo, COD)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from models import db, CartItem, Order, OrderItem, UserInteraction
from recommendation import recommendation_engine
from payment import (
    vnpay_create_payment_url, vnpay_verify_return, VNPAY_RESPONSE_CODES,
    momo_create_payment, momo_verify_return,
)

checkout_bp = Blueprint("checkout", __name__)


@checkout_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Giỏ hàng trống!", "warning")
        return redirect(url_for("cart.cart"))

    total = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone     = request.form.get("phone", "").strip()
        address   = request.form.get("address", "").strip()
        note      = request.form.get("note", "").strip()

        if not full_name or not phone or not address:
            flash("Vui lòng điền đầy đủ thông tin giao hàng.", "error")
            return render_template("checkout/checkout.html", cart_items=cart_items, total=total)

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

        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
            )
            db.session.add(order_item)

            db.session.add(UserInteraction(
                user_id=current_user.id,
                product_id=cart_item.product_id,
                interaction_type="purchase",
                rating=5.0,
            ))
            db.session.delete(cart_item)

        db.session.commit()
        recommendation_engine.invalidate_cache()

        flash("Đặt hàng thành công! Cảm ơn bạn đã mua sắm.", "success")
        return render_template("checkout/success.html", order=order)

    return render_template("checkout/checkout.html", cart_items=cart_items, total=total)


@checkout_bp.route("/checkout/payment", methods=["GET", "POST"])
@login_required
def checkout_payment():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Giỏ hàng trống!", "warning")
        return redirect(url_for("cart.cart"))

    total = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone     = request.form.get("phone", "").strip()
        address   = request.form.get("address", "").strip()
        note      = request.form.get("note", "").strip()

        if not full_name or not phone or not address:
            flash("Vui lòng điền đầy đủ thông tin giao hàng.", "error")
            return render_template("checkout/payment.html", cart_items=cart_items, total=total)

        session["pending_order"] = {
            "full_name": full_name,
            "phone":     phone,
            "address":   address,
            "note":      note,
        }
        return render_template(
            "checkout/payment.html",
            cart_items=cart_items,
            total=total,
            show_methods=True,
            shipping_info=session["pending_order"],
        )

    return render_template("checkout/payment.html", cart_items=cart_items, total=total)


# ── VNPay ──────────────────────────────────────────────────

@checkout_bp.route("/payment/vnpay/create", methods=["POST"])
@login_required
def vnpay_create():
    pending = session.get("pending_order")
    if not pending:
        flash("Phiên đặt hàng đã hết hạn, vui lòng thử lại.", "warning")
        return redirect(url_for("checkout.checkout_payment"))

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Giỏ hàng trống!", "warning")
        return redirect(url_for("cart.cart"))

    total = sum(item.product.price * item.quantity for item in cart_items)

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

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    session["vnpay_order_id"] = order.id

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    payment_url = vnpay_create_payment_url(
        order_id=order.id,
        amount=total,
        order_info=f"Thanh toan don hang LUXE #{order.id}",
        client_ip=client_ip,
    )
    return redirect(payment_url)


@checkout_bp.route("/payment/vnpay/return")
def vnpay_return():
    params = request.args.to_dict()
    is_valid, response_code, order_id_str = vnpay_verify_return(params)

    try:
        order_id = int(order_id_str)
    except (ValueError, TypeError):
        flash("Thông tin đơn hàng không hợp lệ.", "error")
        return redirect(url_for("home.index"))

    order = Order.query.get(order_id)
    if not order:
        flash("Không tìm thấy đơn hàng.", "error")
        return redirect(url_for("home.index"))

    if is_valid and response_code == "00":
        order.status = "confirmed"
        order.payment_method = "vnpay"

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
        return render_template("checkout/success.html", order=order, payment_method="VNPay")

    else:
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

        return redirect(url_for("orders.order_history"))


# ── MoMo ───────────────────────────────────────────────────

@checkout_bp.route("/payment/momo/create", methods=["POST"])
@login_required
def momo_create():
    pending = session.get("pending_order")
    if not pending:
        flash("Phiên đặt hàng đã hết hạn, vui lòng thử lại.", "warning")
        return redirect(url_for("checkout.checkout_payment"))

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Giỏ hàng trống!", "warning")
        return redirect(url_for("cart.cart"))

    total = sum(item.product.price * item.quantity for item in cart_items)

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
        return redirect(url_for("orders.order_history"))


@checkout_bp.route("/payment/momo/return")
def momo_return():
    params = request.args.to_dict()
    is_valid, result_code, order_id_str = momo_verify_return(params)

    try:
        order_id = int(order_id_str)
    except (ValueError, TypeError):
        flash("Thông tin đơn hàng không hợp lệ.", "error")
        return redirect(url_for("home.index"))

    order = Order.query.get(order_id)
    if not order:
        flash("Không tìm thấy đơn hàng.", "error")
        return redirect(url_for("home.index"))

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
        return render_template("checkout/success.html", order=order, payment_method="MoMo")

    else:
        order.status = "pending_payment"
        db.session.commit()
        session.pop("momo_order_id", None)

        if result_code == 49:
            flash("Bạn đã hủy thanh toán MoMo. Đơn hàng vẫn được giữ lại — bạn có thể thanh toán lại.", "warning")
        else:
            flash("Thanh toán MoMo thất bại. Đơn hàng vẫn được giữ lại — bạn có thể thanh toán lại.", "error")

        return redirect(url_for("orders.retry_payment", order_id=order.id))


@checkout_bp.route("/payment/momo/notify", methods=["POST"])
def momo_notify():
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
