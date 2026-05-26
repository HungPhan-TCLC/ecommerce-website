"""
seed_data.py - Seed dynamic data cho Fashion E-commerce Store
=============================================================
Script này làm 2 việc:
  1. Chạy seed_static.sql để INSERT categories + products (idempotent).
  2. Tạo users mẫu (cần Werkzeug hash) + interactions + orders (dynamic).

Static data (categories, products) → seed_static.sql
Dynamic data (users, interactions, orders) → file này

Chạy: python seed_data.py
"""

import os
import sys
from datetime import datetime, timedelta
import random

from app import create_app
from models import db, User, Category, Product, Order, OrderItem, UserInteraction, CartItem
from werkzeug.security import generate_password_hash


# ─── Đường dẫn đến file SQL static ───────────────────────────────────────────
SQL_FILE = os.path.join(os.path.dirname(__file__), "seed_static.sql")


def run_static_sql():
    """Đọc và thực thi seed_static.sql để seed categories + products + users."""
    if not os.path.exists(SQL_FILE):
        print(f"[ERROR] Không tìm thấy file: {SQL_FILE}")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    from sqlalchemy import text
    with db.engine.connect() as conn:
        conn.execute(text(sql_content))
        conn.commit()

    cat_count = Category.query.count()
    prod_count = Product.query.count()
    print(f"[OK] seed_static.sql executed — {cat_count} categories | {prod_count} products.")


def seed_interactions(users, products):
    """
    Tạo lịch sử tương tác giả lập cho recommendation system.
    Mỗi user sẽ có sở thích khác nhau để test collaborative filtering.
    """
    random.seed(42)

    # Định nghĩa sở thích cho từng user (theo thứ tự trong users_data, bỏ qua admin)
    # User 1 (minh_anh - nữ): Thích thời trang nữ, váy đầm, phụ kiện
    # User 2 (duc_huy - nam): Thích streetwear nam, giày sneaker
    # User 3 (thu_trang - nữ): Thích formal, công sở
    # User 4 (hoang_nam - nam): Thích sporty, casual nam
    # User 5 (my_linh - nữ): Thích casual nữ, bohemian
    user_preferences = {
        "minh_anh":  {"genders": ["nu", "unisex"],  "styles": ["casual", "formal"],     "categories": ["ao-nu", "vay-dam", "phu-kien"]},
        "duc_huy":   {"genders": ["nam", "unisex"], "styles": ["streetwear", "casual"],  "categories": ["ao-nam", "quan-nam", "giay-dep"]},
        "thu_trang": {"genders": ["nu", "unisex"],  "styles": ["formal"],               "categories": ["ao-nu", "vay-dam", "giay-dep"]},
        "hoang_nam": {"genders": ["nam", "unisex"], "styles": ["sporty", "casual"],      "categories": ["ao-nam", "quan-nam", "giay-dep"]},
        "my_linh":   {"genders": ["nu", "unisex"],  "styles": ["casual"],               "categories": ["ao-nu", "vay-dam", "quan-nu", "phu-kien"]},
    }

    interaction_count = 0

    for user in users:
        if user.is_admin:
            continue

        prefs = user_preferences.get(user.username, {
            "genders": ["unisex"], "styles": ["casual"], "categories": []
        })

        preferred_products = [
            p for p in products
            if p.gender in prefs["genders"] or p.style in prefs["styles"]
        ]
        other_products = [p for p in products if p not in preferred_products]

        # View: sản phẩm ưa thích
        viewed_preferred = random.sample(preferred_products, min(12, len(preferred_products)))
        for product in viewed_preferred:
            db.session.add(UserInteraction(
                user_id=user.id, product_id=product.id,
                interaction_type="view",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            ))
            interaction_count += 1

        # View: một số sản phẩm khác (ít hơn)
        viewed_others = random.sample(other_products, min(4, len(other_products)))
        for product in viewed_others:
            db.session.add(UserInteraction(
                user_id=user.id, product_id=product.id,
                interaction_type="view",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            ))
            interaction_count += 1

        # Cart
        carted = random.sample(viewed_preferred, min(5, len(viewed_preferred)))
        for product in carted:
            db.session.add(UserInteraction(
                user_id=user.id, product_id=product.id,
                interaction_type="cart",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20)),
            ))
            interaction_count += 1

        # Purchase
        purchased = random.sample(carted, min(random.randint(2, 4), len(carted)))
        for product in purchased:
            db.session.add(UserInteraction(
                user_id=user.id, product_id=product.id,
                interaction_type="purchase",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15)),
            ))
            interaction_count += 1

    db.session.commit()
    print(f"[OK] Đã tạo {interaction_count} user interactions.")


def seed_orders(users, products):
    """Tạo một số đơn hàng mẫu."""
    random.seed(42)
    order_count = 0

    addresses = [
        "123 Nguyễn Huệ, Quận 1, TP.HCM",
        "456 Lê Lợi, Quận 3, TP.HCM",
        "789 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội",
        "321 Bạch Đằng, Hải Châu, Đà Nẵng",
        "654 Nguyễn Văn Linh, Quận 7, TP.HCM",
    ]
    phones = ["0901234567", "0912345678", "0923456789", "0934567890", "0945678901"]

    normal_users = [u for u in users if not u.is_admin]

    for i, user in enumerate(normal_users):
        num_orders = random.randint(1, 2)
        user_products = random.sample(products, min(num_orders * 3, len(products)))

        for j in range(num_orders):
            order_products = user_products[j * 2:(j + 1) * 2 + 1]
            if not order_products:
                continue

            total = sum(p.price * random.randint(1, 2) for p in order_products)
            order = Order(
                user_id=user.id,
                total_amount=total,
                status=random.choice(["confirmed", "shipped", "delivered"]),
                full_name=user.full_name,
                phone=phones[i % len(phones)],
                address=addresses[i % len(addresses)],
                note="Giao giờ hành chính" if random.random() > 0.5 else "",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
            )
            db.session.add(order)
            db.session.flush()

            for product in order_products:
                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=random.randint(1, 2),
                    price=product.price,
                ))

            order_count += 1

    db.session.commit()
    print(f"[OK] Đã tạo {order_count} orders.")


def run_seed():
    """Chạy toàn bộ quá trình seed data."""
    app = create_app()

    with app.app_context():
        # Xóa và tạo lại schema (dùng CASCADE để tránh lỗi foreign key)
        from sqlalchemy import text
        with db.engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))
            conn.commit()
        db.create_all()

        print("=" * 55)
        print("  SEED DATA - Fashion E-commerce Store")
        print("=" * 55)

        # Bước 1: Static data từ SQL (categories + products + users)
        print("\n[1/3] Seeding static data từ seed_static.sql ...")
        run_static_sql()

        # Bước 2: Interactions
        print("\n[2/3] Seeding interactions ...")
        users = User.query.all()
        products = Product.query.all()
        seed_interactions(users, products)

        # Bước 3: Orders
        print("\n[3/3] Seeding orders ...")
        seed_orders(users, products)

        print("\n" + "=" * 55)
        print("  SEED HOÀN TẤT!")
        print(f"  - {Category.query.count()} categories")
        print(f"  - {Product.query.count()} products")
        print(f"  - {User.query.count()} users (admin=admin123 | users=password123)")
        print(f"  - {UserInteraction.query.count()} interactions")
        print(f"  - {Order.query.count()} orders")
        print("=" * 55)


if __name__ == "__main__":
    run_seed()
