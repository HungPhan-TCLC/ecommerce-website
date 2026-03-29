"""
setup_and_seed.py - Kết hợp Migration + Seed Data cho Evaluation
=================================================================
Script này làm 2 việc:
  1. MIGRATE: Tạo tables mới (evaluation_results) và thêm cột source
             vào user_interactions nếu chưa có.
  2. SEED EVAL: Thêm 15 user mới + ~200 interactions phong phú
                để hệ thống đánh giá có đủ data.

* KHÔNG xóa data cũ — chỉ thêm vào.
* Bỏ qua nếu user/product đã tồn tại.

Chạy: python setup_and_seed.py
"""

import os
import sys
import random
from datetime import datetime, timedelta

from app import create_app
from models import db, User, Category, Product, UserInteraction, Order, OrderItem, EvaluationResult
from werkzeug.security import generate_password_hash


# ─── Cấu hình seed ────────────────────────────────────────────────────────────
RANDOM_SEED        = 99        # Seed cố định để tái tạo được
NUM_EVAL_USERS     = 15        # Số user mới thêm vào
MIN_INTERACTIONS   = 12        # Tối thiểu interactions/user (để split 80/20 có test set)
MAX_INTERACTIONS   = 22        # Tối đa interactions/user
NUM_CART           = 5         # Số sản phẩm thêm vào giỏ/user
NUM_PURCHASE       = 3         # Số sản phẩm mua/user
# ──────────────────────────────────────────────────────────────────────────────


# ─── 15 User profiles đa dạng cho evaluation ──────────────────────────────────
EVAL_USERS = [
    # (username, email, full_name, gender_pref, styles, categories)
    ("linh_trang",   "linhtrang@eval.vn",   "Đinh Linh Trang",    ["nu","unisex"],    ["casual","formal"],     ["ao-nu","vay-dam","phu-kien"]),
    ("an_khang",     "ankhang@eval.vn",     "Bùi An Khang",       ["nam","unisex"],   ["streetwear","casual"], ["ao-nam","quan-nam","giay-dep"]),
    ("phuong_anh",   "phuonganh@eval.vn",   "Cao Phương Anh",     ["nu","unisex"],    ["formal"],              ["ao-nu","vay-dam","giay-dep"]),
    ("tuan_kiet",    "tuankiet@eval.vn",     "Ngô Tuấn Kiệt",      ["nam","unisex"],   ["sporty","casual"],     ["ao-nam","quan-nam","giay-dep"]),
    ("thu_ha",       "thuha@eval.vn",        "Đặng Thu Hà",        ["nu","unisex"],    ["casual"],              ["ao-nu","quan-nu","phu-kien"]),
    ("minh_chau",    "minhchau@eval.vn",    "Trịnh Minh Châu",    ["nu","unisex"],    ["casual","formal"],     ["vay-dam","quan-nu","phu-kien"]),
    ("hai_dang",     "haidang@eval.vn",      "Lý Hải Đăng",        ["nam","unisex"],   ["formal"],              ["ao-nam","quan-nam","giay-dep","phu-kien"]),
    ("bao_anh",      "baoanhev@eval.vn",     "Nguyễn Bảo Anh",     ["nu","unisex"],    ["streetwear","casual"], ["ao-nu","quan-nu","giay-dep"]),
    ("viet_hung",    "viethung@eval.vn",     "Phạm Việt Hùng",     ["nam","unisex"],   ["streetwear"],          ["ao-nam","quan-nam","giay-dep"]),
    ("khanh_linh",   "khanhlinh@eval.vn",   "Hồ Khánh Linh",     ["nu","unisex"],    ["formal","casual"],     ["vay-dam","ao-nu","giay-dep"]),
    ("duc_minh",     "ducminh@eval.vn",      "Tô Đức Minh",        ["nam","unisex"],   ["casual","sporty"],     ["ao-nam","quan-nam","giay-dep"]),
    ("thanh_van",    "thanhvan@eval.vn",    "Lê Thanh Vân",       ["nu","unisex"],    ["casual","formal"],     ["ao-nu","vay-dam","quan-nu"]),
    ("quoc_bao",     "quocbao@eval.vn",      "Mai Quốc Bảo",       ["nam","unisex"],   ["formal","casual"],     ["ao-nam","quan-nam","phu-kien"]),
    ("ngoc_han",     "ngochan@eval.vn",      "Dương Ngọc Hân",     ["nu","unisex"],    ["casual","streetwear"], ["ao-nu","quan-nu","giay-dep"]),
    ("bach_khoa",    "bachkhoa@eval.vn",    "Võ Bách Khoa",       ["nam","unisex"],   ["sporty","streetwear"], ["ao-nam","quan-nam","giay-dep"]),
]


def step_migrate(app):
    """Bước 1: Migrate DB — tạo bảng mới, thêm cột mới nếu thiếu."""
    print("\n" + "=" * 55)
    print("  BƯỚC 1: MIGRATE DATABASE")
    print("=" * 55)

    with app.app_context():
        from sqlalchemy import text, inspect

        # Tạo tất cả bảng theo models (không drop bảng cũ)
        db.create_all()
        print("[OK] db.create_all() — Tables created/verified.")

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        # ── Thêm cột 'source' vào user_interactions nếu chưa có ──
        if 'user_interactions' in tables:
            cols = [c['name'] for c in inspector.get_columns('user_interactions')]
            if 'source' not in cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE user_interactions ADD COLUMN source VARCHAR(50)"
                    ))
                    conn.commit()
                print("[OK] Added column 'source' to user_interactions.")
            else:
                print("[OK] Column 'source' already exists — skipped.")
        else:
            print("[WARN] Table 'user_interactions' not found.")

        # ── Check evaluation_results ──
        if 'evaluation_results' in inspector.get_table_names():
            print("[OK] Table 'evaluation_results' exists.")
        else:
            print("[ERROR] Table 'evaluation_results' missing — check models.py!")

        print("\nMigration hoàn tất!")


def step_seed_eval_users(app):
    """Bước 2: Thêm 15 user evaluation nếu chưa tồn tại."""
    print("\n" + "=" * 55)
    print("  BƯỚC 2: SEED EVALUATION USERS (15 users)")
    print("=" * 55)

    with app.app_context():
        created = 0
        skipped = 0
        user_ids = []  # Chỉ lưu IDs, không lưu objects

        for (username, email, full_name, *_) in EVAL_USERS:
            existing = User.query.filter_by(username=username).first()
            if existing:
                user_ids.append(existing.id)
                skipped += 1
                continue

            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash("evalpass123"),
                full_name=full_name,
                is_admin=False,
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 120)),
            )
            db.session.add(user)
            db.session.flush()  # Lấy ID ngay sau khi add
            user_ids.append(user.id)
            created += 1

        db.session.commit()
        print(f"[OK] Tạo mới: {created} users | Đã tồn tại (skip): {skipped} users.")
        return user_ids  # Trả về list[int] IDs


def step_seed_interactions(app, user_ids: list[int]):
    """
    Bước 3: Seed interactions phong phú cho evaluation.

    Chiến lược temporal để offline eval (split 80/20 theo thời gian):
      - 80% interactions đầu (ngày cũ hơn) → train set
      - 20% interactions sau (ngày gần đây) → test set (ground truth)

    Mỗi user:
      - View: 10-18 sản phẩm  (ngày -60 đến -15)
      - Cart:  4-6 sản phẩm   (ngày -14 đến -8)
      - Purchase: 2-4 sản phẩm (ngày -7 đến -1)  ← test set sẽ chứa cái này
    """
    print("\n" + "=" * 55)
    print("  BƯỚC 3: SEED INTERACTIONS CHO EVALUATION")
    print("=" * 55)

    random.seed(RANDOM_SEED)

    with app.app_context():
        products = Product.query.all()
        if not products:
            print("[ERROR] Không có sản phẩm trong DB. Hãy seed products trước!")
            return

        total_interactions = 0
        skipped_users      = 0

        for idx, user_id in enumerate(user_ids):
            # Re-query User bên trong context hiện tại
            user = User.query.get(user_id)
            if user is None:
                print(f"  [WARN] User ID {user_id} không tìm thấy, bỏ qua.")
                continue

            # Lấy preferences tương ứng từ EVAL_USERS
            if idx < len(EVAL_USERS):
                _, _, _, gender_pref, style_pref, cat_pref = EVAL_USERS[idx]
            else:
                gender_pref = ["unisex"]
                style_pref  = ["casual"]
                cat_pref    = []

            # Kiểm tra user đã có quá nhiều interactions chưa
            existing_count = UserInteraction.query.filter_by(user_id=user.id).count()
            if existing_count >= MIN_INTERACTIONS:
                print(f"  [SKIP] {user.username} đã có {existing_count} interactions.")
                skipped_users += 1
                continue

            # Lọc sản phẩm phù hợp sở thích
            preferred = [
                p for p in products
                if p.gender in gender_pref or p.style in style_pref
            ]
            other = [p for p in products if p not in preferred]

            if len(preferred) < 4:
                preferred = products[:]
            if not other:
                other = products[:]

            # ── Phase 1: VIEW (train set — 60 đến 15 ngày trước) ──────────────
            num_views = random.randint(10, 18)
            view_products = random.sample(preferred, min(num_views, len(preferred)))

            # Thêm vài sản phẩm "ngoài sở thích" — tạo noise thực tế
            noise = random.sample(other, min(3, len(other)))
            view_products = list(set(view_products + noise))

            for product in view_products:
                days_ago = random.randint(15, 60)  # Trong train set
                db.session.add(UserInteraction(
                    user_id=user.id,
                    product_id=product.id,
                    interaction_type="view",
                    rating=round(random.uniform(2.5, 5.0), 1),
                    source=random.choice(["homepage", "search", "category", "direct"]),
                    created_at=datetime.utcnow() - timedelta(days=days_ago),
                ))
                total_interactions += 1

            # ── Phase 2: CART (train set — 14 đến 8 ngày trước) ──────────────
            viewed_preferred = [p for p in preferred if p in view_products]
            if not viewed_preferred:
                viewed_preferred = view_products[:]
            num_carts = random.randint(4, NUM_CART + 1)
            cart_products = random.sample(viewed_preferred, min(num_carts, len(viewed_preferred)))

            for product in cart_products:
                days_ago = random.randint(8, 14)
                db.session.add(UserInteraction(
                    user_id=user.id,
                    product_id=product.id,
                    interaction_type="cart",
                    rating=round(random.uniform(3.5, 5.0), 1),
                    source=random.choice(["recommendation", "search", "direct"]),
                    created_at=datetime.utcnow() - timedelta(days=days_ago),
                ))
                total_interactions += 1

            # ── Phase 3: PURCHASE (test set — 7 đến 1 ngày trước) ────────────
            # Đây sẽ là ground truth cho offline evaluation
            num_purchases = random.randint(2, NUM_PURCHASE + 1)
            # Mua từ giỏ hàng hoặc preferred products chưa xem
            purchase_candidates = list(set(cart_products))
            new_products = [p for p in preferred if p not in view_products]
            if new_products:
                purchase_candidates += random.sample(new_products, min(2, len(new_products)))

            purchase_products = random.sample(
                purchase_candidates,
                min(num_purchases, len(purchase_candidates))
            )

            for product in purchase_products:
                days_ago = random.randint(1, 7)  # Gần đây → sẽ vào test set
                db.session.add(UserInteraction(
                    user_id=user.id,
                    product_id=product.id,
                    interaction_type="purchase",
                    rating=round(random.uniform(4.0, 5.0), 1),
                    source=random.choice(["recommendation", "direct"]),
                    created_at=datetime.utcnow() - timedelta(days=days_ago),
                ))
                total_interactions += 1

            # ── Tạo Order tương ứng với purchase ─────────────────────────────
            if purchase_products:
                addresses = [
                    "123 Nguyễn Huệ, Quận 1, TP.HCM",
                    "456 Lê Lợi, Quận 3, TP.HCM",
                    "789 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội",
                    "321 Bạch Đằng, Hải Châu, Đà Nẵng",
                    "654 Nguyễn Văn Linh, Quận 7, TP.HCM",
                ]
                total_amount = sum(p.price for p in purchase_products)
                order = Order(
                    user_id=user.id,
                    total_amount=total_amount,
                    status=random.choice(["confirmed", "delivered"]),
                    full_name=user.full_name,
                    phone=f"090{random.randint(1000000, 9999999)}",
                    address=random.choice(addresses),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 7)),
                )
                db.session.add(order)
                db.session.flush()

                for product in purchase_products:
                    db.session.add(OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=1,
                        price=product.price,
                    ))

            print(f"  [OK] {user.username:20s} → "
                  f"{len(view_products)} views | {len(cart_products)} carts | {len(purchase_products)} purchases")

        db.session.commit()
        print(f"\n[OK] Tổng cộng thêm {total_interactions} interactions | Bỏ qua {skipped_users} users đã đủ data.")


def step_seed_recommendation_source_interactions(app):
    """
    Bước 4: Seed một số interactions với source='recommendation'
    để Online Metrics (CTR, Conversion Rate) có data demo hiển thị.
    """
    print("\n" + "=" * 55)
    print("  BƯỚC 4: SEED ONLINE METRICS DEMO DATA")
    print("=" * 55)

    random.seed(77)

    with app.app_context():
        users = User.query.filter_by(is_admin=False).all()
        products = Product.query.all()

        if not users or not products:
            print("[SKIP] Không đủ user/product.")
            return

        # Chỉ seed nếu chưa có interaction từ recommendation source
        existing_rec = UserInteraction.query.filter_by(source="recommendation").count()
        if existing_rec > 30:
            print(f"[SKIP] Đã có {existing_rec} interactions từ 'recommendation'.")
            return

        total = 0
        for user in random.sample(users, min(10, len(users))):
            # Simulate: user thấy 5-8 sản phẩm từ trang recommendations
            shown_products = random.sample(products, random.randint(5, 8))

            for product in shown_products:
                # View (= impression click từ rec page)
                db.session.add(UserInteraction(
                    user_id=user.id,
                    product_id=product.id,
                    interaction_type="view",
                    source="recommendation",
                    created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                ))
                total += 1

                # 30% chance thêm vào giỏ
                if random.random() < 0.30:
                    db.session.add(UserInteraction(
                        user_id=user.id,
                        product_id=product.id,
                        interaction_type="cart",
                        source="recommendation",
                        created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
                    ))
                    total += 1

                    # 40% trong số đó mua luôn
                    if random.random() < 0.40:
                        db.session.add(UserInteraction(
                            user_id=user.id,
                            product_id=product.id,
                            interaction_type="purchase",
                            source="recommendation",
                            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                        ))
                        total += 1

        db.session.commit()
        print(f"[OK] Thêm {total} interactions với source='recommendation'.")

        # Tóm tắt online metrics data
        views    = UserInteraction.query.filter_by(source="recommendation", interaction_type="view").count()
        carts    = UserInteraction.query.filter_by(source="recommendation", interaction_type="cart").count()
        purchases = UserInteraction.query.filter_by(source="recommendation", interaction_type="purchase").count()
        print(f"     → Views: {views} | Carts: {carts} | Purchases: {purchases}")
        if views > 0:
            print(f"     → CTR est: {carts/views:.1%} | Conversion est: {purchases/views:.1%}")


def print_summary(app):
    """In tổng kết cuối cùng."""
    print("\n" + "=" * 55)
    print("  TỔNG KẾT")
    print("=" * 55)
    with app.app_context():
        from models import Category, EvaluationResult

        total_users   = User.query.count()
        total_products = Product.query.count()
        total_inter   = UserInteraction.query.count()
        total_orders  = Order.query.count()
        total_evals   = EvaluationResult.query.count()

        inter_view  = UserInteraction.query.filter_by(interaction_type="view").count()
        inter_cart  = UserInteraction.query.filter_by(interaction_type="cart").count()
        inter_purch = UserInteraction.query.filter_by(interaction_type="purchase").count()
        inter_rec   = UserInteraction.query.filter_by(source="recommendation").count()

        # Users đủ điều kiện cho offline eval (≥ 4 interactions)
        from sqlalchemy import func
        qualified = db.session.query(
            UserInteraction.user_id
        ).group_by(UserInteraction.user_id).having(
            func.count(UserInteraction.id) >= 4
        ).count()

        print(f"  Users     : {total_users} total | {qualified} đủ điều kiện eval (≥4 interactions)")
        print(f"  Products  : {total_products}")
        print(f"  Interactions: {total_inter}")
        print(f"    - View     : {inter_view}")
        print(f"    - Cart     : {inter_cart}")
        print(f"    - Purchase : {inter_purch}")
        print(f"    - Từ Rec   : {inter_rec}")
        print(f"  Orders    : {total_orders}")
        print(f"  Eval Results: {total_evals} (từ các lần chạy đánh giá trước)")
        print("=" * 55)
        print("\n✅ Xong! Vào Admin → AI & Gợi ý → nhấn 'Chạy Đánh Giá (K=8)'")
        print(f"   Kỳ vọng đánh giá được ít nhất {qualified} users.\n")


def main():
    print("\n" + "🚀 " * 18)
    print("  SETUP & SEED FOR EVALUATION METRICS")
    print("🚀 " * 18)

    app = create_app()

    # Bước 1: Migrate
    step_migrate(app)

    # Bước 2-4: Seed (dùng chung app context)
    user_objects = step_seed_eval_users(app)
    step_seed_interactions(app, user_objects)
    step_seed_recommendation_source_interactions(app)

    # Tổng kết
    print_summary(app)


if __name__ == "__main__":
    main()
