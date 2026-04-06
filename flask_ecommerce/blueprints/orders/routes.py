"""
blueprints/orders/routes.py - Lịch sử đơn hàng & retry payment
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Order, CartItem, UserInteraction
from recommendation import recommendation_engine
from payment import vnpay_create_payment_url, momo_create_payment

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders")
@login_required
def order_history():
    from sqlalchemy import func

    status_filter = request.args.get("status", "all").strip()

    raw_counts = db.session.query(
        Order.status,
        func.count(Order.id).label("cnt")
    ).filter(
        Order.user_id == current_user.id
    ).group_by(Order.status).all()

    status_map = {row.status: row.cnt for row in raw_counts}
    total = sum(status_map.values())

    counts = {
        "all":             total,
        "pending_payment": status_map.get("pending_payment", 0),
        "payment_failed":  status_map.get("payment_failed",  0),
        "confirmed":       status_map.get("confirmed",       0),
        "shipped":         status_map.get("shipped",         0),
        "delivered":       status_map.get("delivered",       0),
        "cancelled": status_map.get("cancelled", 0) + status_map.get("pending", 0),
    }

    base_q = Order.query.filter_by(user_id=current_user.id)

    if status_filter == "cancelled":
        orders = base_q.filter(
            Order.status.in_(["cancelled", "pending"])
        ).order_by(Order.created_at.desc()).all()
    elif status_filter != "all":
        orders = base_q.filter_by(
            status=status_filter
        ).order_by(Order.created_at.desc()).all()
    else:
        orders = base_q.order_by(Order.created_at.desc()).all()

    all_user_orders_asc = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.created_at.asc()).all()
    order_seq = {o.id: i + 1 for i, o in enumerate(all_user_orders_asc)}

    return render_template(
        "orders/orders.html",
        orders=orders,
        status_filter=status_filter,
        counts=counts,
        order_seq=order_seq,
    )


@orders_bp.route("/order/<int:order_id>/retry-payment", methods=["GET", "POST"])
@login_required
def retry_payment(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash("Không có quyền truy cập.", "error")
        return redirect(url_for("orders.order_history"))

    RETRYABLE_STATUSES = ("pending_payment", "payment_failed")
    if order.status not in RETRYABLE_STATUSES:
        flash("Đơn hàng này không thể thanh toán lại.", "info")
        return redirect(url_for("orders.order_history"))

    if request.method == "POST":
        method = request.form.get("method")

        session["pending_order"] = {
            "full_name": order.full_name,
            "phone":     order.phone,
            "address":   order.address,
            "note":      order.note or "",
        }

        if method == "momo":
            pay_url, message = momo_create_payment(
                order_id=order.id,
                amount=order.total_amount,
                order_info=f"Thanh toan don hang LUXE #{order.id}",
            )
            if pay_url:
                session["momo_order_id"] = order.id
                return redirect(pay_url)
            else:
                flash(f"Không thể kết nối MoMo: {message}", "error")

        elif method == "vnpay":
            client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            payment_url = vnpay_create_payment_url(
                order_id=order.id,
                amount=order.total_amount,
                order_info=f"Thanh toan don hang LUXE #{order.id}",
                client_ip=client_ip,
            )
            session["vnpay_order_id"] = order.id
            return redirect(payment_url)

        elif method == "cod":
            order.status         = "confirmed"
            order.payment_method = "cod"
            db.session.commit()

            CartItem.query.filter_by(user_id=current_user.id).delete()
            for item in order.items:
                db.session.add(UserInteraction(
                    user_id=current_user.id,
                    product_id=item.product_id,
                    interaction_type="purchase",
                    rating=5.0,
                ))
            db.session.commit()
            recommendation_engine.invalidate_cache()
            session.pop("pending_order", None)

            flash("Đặt hàng thành công! Thanh toán khi nhận hàng.", "success")
            return render_template("checkout/success.html", order=order, payment_method="COD")

        return redirect(url_for("orders.retry_payment", order_id=order_id))

    return render_template("checkout/retry_payment.html", order=order)


@orders_bp.route("/order/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_pending_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Không có quyền truy cập.", "error")
        return redirect(url_for("orders.order_history"))

    RETRYABLE_STATUSES = ("pending_payment", "payment_failed")
    if order.status not in RETRYABLE_STATUSES:
        flash("Không thể hủy đơn hàng này.", "info")
        return redirect(url_for("orders.order_history"))

    order.status = "cancelled"
    db.session.commit()
    flash(f"Đã hủy đơn hàng #{order.id}.", "success")
    return redirect(url_for("orders.order_history"))
