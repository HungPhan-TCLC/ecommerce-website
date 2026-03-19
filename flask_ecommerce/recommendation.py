"""
recommendation.py - Hệ thống Gợi ý Sản phẩm (Recommendation System)
Bao gồm 2 phương pháp chính:
1. Content-based Filtering: Gợi ý sản phẩm tương tự dựa trên mô tả, tags, category
2. User-based Collaborative Filtering: Gợi ý dựa trên hành vi user tương tự
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models import db, Product, UserInteraction, User


class RecommendationEngine:
    """Engine chính xử lý tất cả logic recommendation"""

    def __init__(self):
        self._tfidf_matrix = None
        self._product_ids = None
        self._vectorizer = None

    # ========================================================
    #  1. CONTENT-BASED FILTERING
    #  Gợi ý sản phẩm tương tự dựa trên nội dung (tags, mô tả, category, style...)
    # ========================================================

    def _build_product_features(self, products):
        """
        Xây dựng feature text cho mỗi sản phẩm bằng cách kết hợp:
        - Tags
        - Category name
        - Gender
        - Material
        - Style
        - Mô tả sản phẩm
        Tất cả ghép lại thành 1 chuỗi text để TF-IDF vectorize.
        """
        feature_texts = []
        product_ids = []

        for product in products:
            # Kết hợp nhiều trường thông tin → 1 chuỗi feature
            features = " ".join([
                product.tags or "",
                product.category.name if product.category else "",
                product.gender or "",
                product.material or "",
                product.style or "",
                product.description or "",
            ])
            feature_texts.append(features)
            product_ids.append(product.id)

        return feature_texts, product_ids

    def _compute_tfidf_matrix(self):
        """Tính TF-IDF matrix cho toàn bộ sản phẩm (cache lại để tái sử dụng)"""
        products = Product.query.all()
        if not products:
            return None, None, None

        feature_texts, product_ids = self._build_product_features(products)

        # TF-IDF Vectorizer: chuyển text thành vector số
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words=None,  # Giữ lại tiếng Việt
            ngram_range=(1, 2),  # Unigram + Bigram
        )
        tfidf_matrix = vectorizer.fit_transform(feature_texts)

        self._tfidf_matrix = tfidf_matrix
        self._product_ids = product_ids
        self._vectorizer = vectorizer

        return tfidf_matrix, product_ids, vectorizer

    def get_similar_products(self, product_id, top_n=8):
        """
        CONTENT-BASED: Tìm top_n sản phẩm tương tự với product_id
        Sử dụng Cosine Similarity trên TF-IDF vectors.

        Returns: List[Product] - danh sách sản phẩm tương tự
        """
        # Tính TF-IDF nếu chưa có
        if self._tfidf_matrix is None:
            self._compute_tfidf_matrix()

        if self._tfidf_matrix is None or self._product_ids is None:
            return []

        # Tìm index của product trong matrix
        try:
            product_idx = self._product_ids.index(product_id)
        except ValueError:
            return []

        # Tính cosine similarity giữa sản phẩm hiện tại và tất cả sản phẩm khác
        product_vector = self._tfidf_matrix[product_idx:product_idx + 1]
        similarity_scores = cosine_similarity(product_vector, self._tfidf_matrix).flatten()

        # Sắp xếp theo similarity giảm dần, bỏ qua chính nó (index 0 = similarity = 1.0)
        similar_indices = similarity_scores.argsort()[::-1]

        # Lấy top_n sản phẩm (bỏ chính sản phẩm đang xem)
        recommended_ids = []
        for idx in similar_indices:
            pid = self._product_ids[idx]
            if pid != product_id:
                recommended_ids.append(pid)
            if len(recommended_ids) >= top_n:
                break

        # Query từ database
        recommended_products = Product.query.filter(
            Product.id.in_(recommended_ids)
        ).all()

        # Sắp xếp lại theo thứ tự similarity
        id_order = {pid: i for i, pid in enumerate(recommended_ids)}
        recommended_products.sort(key=lambda p: id_order.get(p.id, 999))

        return recommended_products

    # ========================================================
    #  2. USER-BASED COLLABORATIVE FILTERING
    #  Gợi ý dựa trên hành vi của các user tương tự
    # ========================================================

    def _build_user_item_matrix(self):
        """
        Xây dựng User-Item interaction matrix.
        Giá trị = rating score dựa trên interaction type:
        - view = 1 điểm
        - cart = 3 điểm
        - purchase = 5 điểm
        Nếu có rating thực tế thì dùng rating đó.
        """
        interactions = UserInteraction.query.all()
        if not interactions:
            return None, None, None

        # Chuyển thành DataFrame
        data = []
        for inter in interactions:
            # Tính score dựa trên loại interaction
            type_scores = {"view": 1.0, "cart": 3.0, "purchase": 5.0}
            score = inter.rating if inter.rating else type_scores.get(inter.interaction_type, 1.0)
            data.append({
                "user_id": inter.user_id,
                "product_id": inter.product_id,
                "score": score,
            })

        df = pd.DataFrame(data)

        # Nếu user có nhiều interaction với cùng product, lấy score cao nhất
        df = df.groupby(["user_id", "product_id"])["score"].max().reset_index()

        # Tạo User-Item matrix (pivot table)
        user_item_matrix = df.pivot_table(
            index="user_id",
            columns="product_id",
            values="score",
            fill_value=0,
        )

        return user_item_matrix, df

    def get_personalized_recommendations(self, user_id, top_n=12):
        """
        USER-BASED COLLABORATIVE FILTERING:
        1. Tìm users có hành vi tương tự (cosine similarity trên interaction vectors)
        2. Gợi ý sản phẩm mà các user tương tự đã thích nhưng user hiện tại chưa tương tác

        Returns: List[Product]
        """
        result = self._build_user_item_matrix()
        if result is None or result[0] is None:
            return self._get_popular_products(top_n)

        user_item_matrix, df = result

        # Kiểm tra user có trong matrix không
        if user_id not in user_item_matrix.index:
            return self._get_popular_products(top_n)

        # Tính cosine similarity giữa các users
        user_similarity = cosine_similarity(user_item_matrix)
        user_sim_df = pd.DataFrame(
            user_similarity,
            index=user_item_matrix.index,
            columns=user_item_matrix.index,
        )

        # Tìm user index
        current_user_idx = list(user_sim_df.index).index(user_id)

        # Lấy similarity scores với các user khác
        sim_scores = user_sim_df.iloc[current_user_idx].drop(user_id)

        # Sắp xếp các user theo độ tương tự giảm dần
        similar_users = sim_scores.sort_values(ascending=False)

        # Sản phẩm user hiện tại đã tương tác
        user_interacted = set(
            user_item_matrix.loc[user_id][user_item_matrix.loc[user_id] > 0].index.tolist()
        )

        # Tập hợp sản phẩm được gợi ý (weighted score)
        recommendation_scores = {}

        for other_user_id, similarity in similar_users.items():
            if similarity <= 0:
                continue

            # Sản phẩm user khác đã tương tác (có score cao)
            other_user_items = user_item_matrix.loc[other_user_id]
            other_liked = other_user_items[other_user_items >= 3.0].index.tolist()

            for product_id in other_liked:
                if product_id not in user_interacted:
                    # Weighted score = similarity * rating score
                    weighted_score = similarity * other_user_items[product_id]
                    if product_id in recommendation_scores:
                        recommendation_scores[product_id] += weighted_score
                    else:
                        recommendation_scores[product_id] = weighted_score

        if not recommendation_scores:
            return self._get_popular_products(top_n)

        # Sắp xếp và lấy top_n
        sorted_recs = sorted(recommendation_scores.items(), key=lambda x: x[1], reverse=True)
        recommended_ids = [int(pid) for pid, _ in sorted_recs[:top_n]]

        # Query products
        recommended_products = Product.query.filter(
            Product.id.in_(recommended_ids)
        ).all()

        # Sắp xếp lại theo score
        id_order = {pid: i for i, pid in enumerate(recommended_ids)}
        recommended_products.sort(key=lambda p: id_order.get(p.id, 999))

        # Nếu không đủ, bổ sung từ popular
        if len(recommended_products) < top_n:
            existing_ids = {p.id for p in recommended_products}
            popular = self._get_popular_products(top_n - len(recommended_products), exclude_ids=existing_ids)
            recommended_products.extend(popular)

        return recommended_products[:top_n]

    # ========================================================
    #  3. POPULAR / TRENDING PRODUCTS (Fallback)
    # ========================================================

    def _get_popular_products(self, top_n=12, exclude_ids=None):
        """
        Fallback: Gợi ý sản phẩm phổ biến nhất dựa trên:
        - Số lượt tương tác (view + cart + purchase)
        - Ưu tiên sản phẩm is_featured

        Dùng khi user mới hoặc không có đủ dữ liệu cho collaborative filtering.
        """
        if exclude_ids is None:
            exclude_ids = set()

        # Đếm số interactions cho mỗi product
        from sqlalchemy import func
        popular_query = db.session.query(
            UserInteraction.product_id,
            func.count(UserInteraction.id).label("interaction_count"),
        ).group_by(
            UserInteraction.product_id
        ).order_by(
            func.count(UserInteraction.id).desc()
        ).limit(top_n + len(exclude_ids)).all()

        popular_ids = [pid for pid, _ in popular_query if pid not in exclude_ids][:top_n]

        if not popular_ids:
            # Nếu không có interaction data, lấy featured products
            query = Product.query.filter(Product.is_featured == True)
            if exclude_ids:
                query = query.filter(~Product.id.in_(exclude_ids))
            products = query.limit(top_n).all()

            # Nếu vẫn không đủ, lấy random
            if len(products) < top_n:
                remaining = top_n - len(products)
                existing = {p.id for p in products} | exclude_ids
                more = Product.query.filter(
                    ~Product.id.in_(existing)
                ).limit(remaining).all()
                products.extend(more)
            return products

        products = Product.query.filter(Product.id.in_(popular_ids)).all()
        id_order = {pid: i for i, pid in enumerate(popular_ids)}
        products.sort(key=lambda p: id_order.get(p.id, 999))
        return products

    # ========================================================
    #  4. "PEOPLE ALSO BOUGHT" - Dựa trên co-purchase
    # ========================================================

    def get_also_bought(self, product_id, top_n=6):
        """
        Tìm sản phẩm mà người mua sản phẩm này cũng thường mua.
        Logic: Tìm các user đã mua product_id → xem họ còn mua gì khác → rank theo tần suất.
        """
        # Tìm tất cả user đã mua sản phẩm này
        buyers = db.session.query(UserInteraction.user_id).filter(
            UserInteraction.product_id == product_id,
            UserInteraction.interaction_type == "purchase",
        ).all()

        buyer_ids = [b[0] for b in buyers]

        if not buyer_ids:
            # Fallback: dùng content-based
            return self.get_similar_products(product_id, top_n)

        # Tìm sản phẩm các buyer này cũng đã mua
        from sqlalchemy import func
        also_bought = db.session.query(
            UserInteraction.product_id,
            func.count(UserInteraction.user_id).label("buy_count"),
        ).filter(
            UserInteraction.user_id.in_(buyer_ids),
            UserInteraction.interaction_type.in_(["purchase", "cart"]),
            UserInteraction.product_id != product_id,
        ).group_by(
            UserInteraction.product_id,
        ).order_by(
            func.count(UserInteraction.user_id).desc(),
        ).limit(top_n).all()

        product_ids = [pid for pid, _ in also_bought]

        if not product_ids:
            return self.get_similar_products(product_id, top_n)

        products = Product.query.filter(Product.id.in_(product_ids)).all()
        id_order = {pid: i for i, pid in enumerate(product_ids)}
        products.sort(key=lambda p: id_order.get(p.id, 999))
        return products

    # ========================================================
    #  5. HYBRID RECOMMENDATION (Switching + Weighted)
    #  Kết hợp thông minh các thuật toán theo tình huống user
    # ========================================================

    # Trọng số Weighted Hybrid (tổng = 1.0)
    WEIGHT_CF      = 0.50
    WEIGHT_CONTENT = 0.30
    WEIGHT_POPULAR = 0.20

    # Ngưỡng tối thiểu để dùng CF
    CF_MIN_INTERACTIONS = 3

    def _normalize_scores(self, scores):
        """Normalize dict scores về [0, 1]."""
        if not scores:
            return {}
        max_val = max(scores.values()) or 1
        return {k: v / max_val for k, v in scores.items()}

    def _get_content_scores_for_user(self, interacted_ids, exclude_ids):
        """
        Tính Content-based score cho user dựa trên trung bình TF-IDF
        vector của các sản phẩm user đã tương tác.
        Trả về dict {product_id: score}.
        """
        if self._tfidf_matrix is None:
            self._compute_tfidf_matrix()
        if self._tfidf_matrix is None:
            return {}

        indices = [
            self._product_ids.index(pid)
            for pid in interacted_ids
            if pid in self._product_ids
        ]
        if not indices:
            return {}

        # Vector trung bình = user profile
        import numpy as np
        user_profile = np.asarray(self._tfidf_matrix[indices].mean(axis=0))
        sims = cosine_similarity(user_profile, self._tfidf_matrix).flatten()

        return {
            self._product_ids[i]: float(sims[i])
            for i in range(len(sims))
            if self._product_ids[i] not in exclude_ids
        }

    def _get_popular_scores(self, exclude_ids):
        """
        Tính Popular score normalize về [0,1].
        Trả về dict {product_id: score}.
        """
        from sqlalchemy import func
        rows = db.session.query(
            UserInteraction.product_id,
            func.count(UserInteraction.id).label("cnt"),
        ).group_by(UserInteraction.product_id).all()

        if not rows:
            return {}
        max_cnt = max(cnt for _, cnt in rows) or 1
        return {
            pid: cnt / max_cnt
            for pid, cnt in rows
            if pid not in exclude_ids
        }

    def _get_cf_scores(self, user_id, exclude_ids):
        """
        Tính Collaborative Filtering score.
        Tái sử dụng logic từ get_personalized_recommendations.
        Trả về dict {product_id: score}.
        """
        result = self._build_user_item_matrix()
        if result is None or result[0] is None:
            return {}

        user_item_matrix, _ = result
        if user_id not in user_item_matrix.index:
            return {}

        user_similarity = cosine_similarity(user_item_matrix)
        user_sim_df = pd.DataFrame(
            user_similarity,
            index=user_item_matrix.index,
            columns=user_item_matrix.index,
        )
        sim_scores   = user_sim_df.loc[user_id].drop(user_id)
        similar_users = sim_scores.sort_values(ascending=False)

        user_interacted = set(
            user_item_matrix.loc[user_id][user_item_matrix.loc[user_id] > 0].index.tolist()
        )

        cf_scores = {}
        for other_id, similarity in similar_users.items():
            if similarity <= 0:
                continue
            other_items = user_item_matrix.loc[other_id]
            for pid, score in other_items[other_items >= 3.0].items():
                if pid not in user_interacted and pid not in exclude_ids:
                    cf_scores[pid] = cf_scores.get(pid, 0) + similarity * score

        return cf_scores

    def get_hybrid_recommendations(self, user_id, top_n=12):
        """
        HYBRID RECOMMENDATION — Switching ưu tiên, fallback về Weighted Hybrid.

        Chiến lược Switching:
          - user_interaction < CF_MIN_INTERACTIONS (user mới) → Content-based
          - Ngược lại                                         → Collaborative Filtering

        Nếu thuật toán chính không đủ top_n kết quả → Weighted Hybrid bổ sung:
          score = CF×0.5 + Content×0.3 + Popular×0.2

        Fallback cuối: Popular / Featured products.

        Returns: (List[Product], str) — danh sách sản phẩm + tên thuật toán đã dùng
        """
        interaction_count = UserInteraction.query.filter_by(user_id=user_id).count()
        interacted        = UserInteraction.query.filter_by(user_id=user_id).all()
        interacted_ids    = list({i.product_id for i in interacted})
        exclude_ids       = set(interacted_ids)

        # ── Tầng 1A: User mới → Content-based ──────────────────────────
        if interaction_count < self.CF_MIN_INTERACTIONS:
            algorithm = "content_based"
            if interacted_ids:
                scores     = self._get_content_scores_for_user(interacted_ids, exclude_ids)
                sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_n]
                products   = self._ids_to_products(sorted_ids)
            else:
                products = []

        # ── Tầng 1B: User có lịch sử → Collaborative Filtering ─────────
        else:
            algorithm = "collaborative_filtering"
            cf_scores  = self._get_cf_scores(user_id, exclude_ids)
            sorted_ids = sorted(cf_scores, key=cf_scores.get, reverse=True)[:top_n]
            products   = self._ids_to_products(sorted_ids)

            if not cf_scores:
                algorithm = "weighted_hybrid"
                products  = []

        # ── Tầng 2: Bổ sung bằng Weighted Hybrid nếu chưa đủ ──────────
        if len(products) < top_n:
            algorithm   = "weighted_hybrid"
            need        = top_n - len(products)
            new_exclude = exclude_ids | {p.id for p in products}

            cf_s      = self._normalize_scores(self._get_cf_scores(user_id, new_exclude))
            content_s = self._normalize_scores(
                self._get_content_scores_for_user(interacted_ids, new_exclude)
            )
            popular_s = self._normalize_scores(self._get_popular_scores(new_exclude))

            all_pids = set(cf_s) | set(content_s) | set(popular_s)
            weighted = {
                pid: (
                    self.WEIGHT_CF      * cf_s.get(pid, 0) +
                    self.WEIGHT_CONTENT * content_s.get(pid, 0) +
                    self.WEIGHT_POPULAR * popular_s.get(pid, 0)
                )
                for pid in all_pids
            }
            hybrid_ids = sorted(weighted, key=weighted.get, reverse=True)[:need]
            products.extend(self._ids_to_products(hybrid_ids))

        # ── Tầng 3: Fallback Popular ────────────────────────────────────
        if len(products) < top_n:
            skip     = exclude_ids | {p.id for p in products}
            products.extend(self._get_popular_products(top_n - len(products), exclude_ids=skip))

        return products[:top_n], algorithm

    def _ids_to_products(self, product_ids):
        """Query và sắp xếp products theo thứ tự đã cho."""
        if not product_ids:
            return []
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        order    = {pid: i for i, pid in enumerate(product_ids)}
        products.sort(key=lambda p: order.get(p.id, 999))
        return products

    def invalidate_cache(self):
        """Xóa cache TF-IDF khi có sản phẩm mới"""
        self._tfidf_matrix = None
        self._product_ids = None
        self._vectorizer = None


# Singleton instance
recommendation_engine = RecommendationEngine()
