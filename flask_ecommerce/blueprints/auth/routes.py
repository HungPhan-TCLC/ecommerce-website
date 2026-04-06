"""
blueprints/auth/routes.py - Đăng nhập / Đăng ký / Đăng xuất
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()

        if User.query.filter_by(username=username).first():
            flash("Tên đăng nhập đã tồn tại.", "error")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Email đã được sử dụng.", "error")
            return render_template("auth/register.html")

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Đăng ký thành công! Chào mừng bạn.", "success")
        return redirect(url_for("home.index"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember", False)

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=bool(remember))
            flash(f"Chào mừng trở lại, {user.full_name or user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("home.index"))
        else:
            flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất thành công.", "success")
    return redirect(url_for("home.index"))
