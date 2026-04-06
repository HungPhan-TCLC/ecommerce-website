"""
blueprints/profile/routes.py - Tài khoản người dùng
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Order, UserInteraction

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_info":
            full_name = request.form.get("full_name", "").strip()
            email     = request.form.get("email", "").strip()

            if not email:
                flash("Email không được để trống.", "error")
                return redirect(url_for("profile.profile"))

            from models import User
            existing = User.query.filter(
                User.email == email,
                User.id != current_user.id
            ).first()
            if existing:
                flash("Email này đã được sử dụng bởi tài khoản khác.", "error")
                return redirect(url_for("profile.profile"))

            current_user.full_name = full_name
            current_user.email     = email
            db.session.commit()
            flash("Cập nhật thông tin thành công!", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw     = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not check_password_hash(current_user.password_hash, current_pw):
                flash("Mật khẩu hiện tại không đúng.", "error")
                return redirect(url_for("profile.profile"))

            if len(new_pw) < 6:
                flash("Mật khẩu mới phải có ít nhất 6 ký tự.", "error")
                return redirect(url_for("profile.profile"))

            if new_pw != confirm_pw:
                flash("Mật khẩu xác nhận không khớp.", "error")
                return redirect(url_for("profile.profile"))

            current_user.password_hash = generate_password_hash(new_pw)
            db.session.commit()
            flash("Đổi mật khẩu thành công!", "success")

        return redirect(url_for("profile.profile"))

    total_orders  = Order.query.filter_by(user_id=current_user.id).count()
    total_spent   = db.session.query(
        db.func.sum(Order.total_amount)
    ).filter(
        Order.user_id == current_user.id,
        Order.status.in_(["confirmed", "shipped", "delivered"]),
    ).scalar() or 0
    total_reviews = UserInteraction.query.filter(
        UserInteraction.user_id == current_user.id,
        UserInteraction.rating.isnot(None),
    ).count()
    recent_orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.created_at.desc()).limit(5).all()

    return render_template(
        "profile/profile.html",
        total_orders=total_orders,
        total_spent=total_spent,
        total_reviews=total_reviews,
        recent_orders=recent_orders,
    )
