"""
compute_sparsity.py
Tính tỷ lệ thưa thớt (Sparsity) của ma trận User-Item trong hệ thống recommendation.

Công thức:
    Sparsity = 1 - (số cặp (user, product) có tương tác duy nhất)
                   / (tổng_users × tổng_products)

Chạy:  python compute_sparsity.py
"""

import sys
import os

# Đảm bảo import đúng module
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, Product, UserInteraction
import pandas as pd


def compute_sparsity():
    app = create_app()
    with app.app_context():

        # ── 1. Thống kê cơ bản ────────────────────────────────────────────
        n_users    = User.query.filter_by(is_admin=False).count()
        n_products = Product.query.count()
        n_interactions_total = UserInteraction.query.count()

        # Số cặp (user, product) có ít nhất 1 tương tác (không tính duplicate)
        from sqlalchemy import func, distinct, tuple_
        n_unique_pairs = (
            db.session.query(
                func.count(
                    func.distinct(
                        func.concat(
                            UserInteraction.user_id, '-',
                            UserInteraction.product_id
                        )
                    )
                )
            ).scalar()
        )

        # ── 2. Tính sparsity ──────────────────────────────────────────────
        total_possible = n_users * n_products
        sparsity       = 1.0 - (n_unique_pairs / total_possible) if total_possible > 0 else 1.0
        density        = 1.0 - sparsity

        # ── 3. Phân tích theo loại interaction ────────────────────────────
        type_counts = (
            db.session.query(
                UserInteraction.interaction_type,
                func.count(UserInteraction.id).label("cnt")
            )
            .group_by(UserInteraction.interaction_type)
            .all()
        )

        # ── 4. Phân bố tương tác theo user ───────────────────────────────
        interactions_per_user = (
            db.session.query(
                UserInteraction.user_id,
                func.count(UserInteraction.id).label("cnt")
            )
            .group_by(UserInteraction.user_id)
            .all()
        )
        user_counts = [row.cnt for row in interactions_per_user]
        n_active_users = len(user_counts)   # users có ít nhất 1 interaction

        # Users có đủ ngưỡng CF (>= 3 interactions)
        n_cf_eligible = sum(1 for c in user_counts if c >= 3)

        # Phân bố tương tác theo product
        interactions_per_product = (
            db.session.query(
                UserInteraction.product_id,
                func.count(UserInteraction.id).label("cnt")
            )
            .group_by(UserInteraction.product_id)
            .all()
        )
        product_counts    = [row.cnt for row in interactions_per_product]
        n_covered_products = len(product_counts)

        # ── 5. In kết quả ─────────────────────────────────────────────────
        sep = "=" * 60
        print(sep)
        print("   PHÂN TÍCH TỶ LỆ THƯA THỚT (SPARSITY) - USER-ITEM MATRIX")
        print(sep)

        print(f"\n{'── Kích thước tập dữ liệu':─<55}")
        print(f"  Tổng users (không phải admin) : {n_users:>8,}")
        print(f"  Tổng sản phẩm                 : {n_products:>8,}")
        print(f"  Tổng ô trong ma trận          : {total_possible:>8,}  ({n_users} × {n_products})")

        print(f"\n{'── Tương tác':─<55}")
        print(f"  Tổng lượt tương tác (raw)     : {n_interactions_total:>8,}")
        print(f"  Số cặp (user, product) duy nhất: {n_unique_pairs:>7,}")
        for itype, cnt in type_counts:
            pct = cnt / n_interactions_total * 100 if n_interactions_total else 0
            print(f"    └─ {itype:<12}: {cnt:>6,}  ({pct:.1f}%)")

        print(f"\n{'── Sparsity / Density':─<55}")
        print(f"  *** Sparsity = {sparsity * 100:.4f}%  ({sparsity:.6f}) ***")
        print(f"      Density  = {density  * 100:.4f}%  ({density:.6f})")

        # Đánh giá mức độ
        if sparsity >= 0.99:
            level = "RẤT CAO  → Collaborative Filtering gặp khó (cold-start nặng)"
        elif sparsity >= 0.95:
            level = "CAO      → CF hoạt động hạn chế; cần Hybrid/Content-based"
        elif sparsity >= 0.90:
            level = "TRUNG BÌNH → CF hoạt động được, nên kết hợp Hybrid"
        else:
            level = "THẤP     → CF hoạt động tốt"
        print(f"  Mức độ: {level}")

        print(f"\n{'── Phân bố users':─<55}")
        print(f"  Users có ít nhất 1 tương tác : {n_active_users:>7,} / {n_users}")
        print(f"  Users đủ ngưỡng CF (≥3 inter): {n_cf_eligible:>7,} / {n_users}")
        if n_active_users:
            import statistics
            print(f"  Trung bình inter/user (active): {sum(user_counts)/n_active_users:>7.2f}")
            print(f"  Trung vị inter/user (active)  : {statistics.median(user_counts):>7.1f}")
            print(f"  Max inter/user                : {max(user_counts):>7,}")
            print(f"  Min inter/user (active)       : {min(user_counts):>7,}")

        print(f"\n{'── Phân bố sản phẩm':─<55}")
        print(f"  Sản phẩm có ít nhất 1 tương tác: {n_covered_products:>6,} / {n_products}")
        print(f"  Sản phẩm chưa có tương tác nào : {n_products - n_covered_products:>6,}")
        if product_counts:
            print(f"  Trung bình inter/product       : {sum(product_counts)/n_covered_products:>6.2f}")
            print(f"  Max inter/product              : {max(product_counts):>6,}")

        print(f"\n{sep}\n")

        return {
            "n_users": n_users,
            "n_products": n_products,
            "total_possible": total_possible,
            "n_unique_pairs": n_unique_pairs,
            "sparsity": sparsity,
            "density": density,
        }


if __name__ == "__main__":
    compute_sparsity()
