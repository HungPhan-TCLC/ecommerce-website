"""
evaluation.py - Bộ Đánh Giá Chất Lượng Recommendation System

Phương án A — Offline Evaluation (Temporal Split 80/20):
  - Precision@K, Recall@K, Hit Rate@K, NDCG@K
  - Catalog Coverage, Intra-list Diversity

Phương án B — Online Metrics (từ UserInteraction.source):
  - CTR (Click-through Rate từ recommendation)
  - Conversion Rate (purchase / click_from_rec)
  - Recommendation Acceptance Rate

K mặc định = 8 (theo cấu hình hệ thống)
"""

import uuid
import math
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict

from models import db, Product, UserInteraction, Order, OrderItem, Category, EvaluationResult
from recommendation import RecommendationEngine


DEFAULT_K = 8

# ─── Ngưỡng minimum để user được đưa vào offline eval ────────────────────────
MIN_INTERACTIONS_PER_USER = 4   # user phải có ít nhất 4 interactions
TRAIN_RATIO = 0.8               # 80% đầu làm train, 20% sau làm test


class RecommendationEvaluator:
    """
    Đánh giá chất lượng recommendation theo 2 phương án:
      A) Offline: dùng temporal split trên UserInteraction
      B) Online:  đọc field source='recommendation' từ UserInteraction

    Sử dụng: evaluator = RecommendationEvaluator()
             results   = evaluator.run_full_evaluation(k=8)
    """

    def __init__(self):
        self._engine = RecommendationEngine()

    # =========================================================================
    #  HELPER: Split train / test theo thời gian
    # =========================================================================

    def _split_train_test(self):
        """
        Temporal split 80/20 trên UserInteraction.
        Với mỗi user có đủ MIN_INTERACTIONS interactions:
          - Sắp xếp interactions theo created_at
          - 80% đầu → train_set, 20% sau → test_set

        Returns:
            train_dict : {user_id: [product_id, ...]}  (80% đầu)
            test_dict  : {user_id: [product_id, ...]}  (20% sau — ground truth)
            qualified_users: list[int]
        """
        all_interactions = (
            UserInteraction.query
            .filter(UserInteraction.interaction_type.in_(["view", "cart", "purchase"]))
            .order_by(UserInteraction.user_id, UserInteraction.created_at)
            .all()
        )

        # Nhóm theo user
        user_interactions: dict[int, list] = defaultdict(list)
        for inter in all_interactions:
            user_interactions[inter.user_id].append(inter)

        train_dict: dict[int, list[int]] = {}
        test_dict:  dict[int, list[int]] = {}
        qualified_users = []

        for user_id, interactions in user_interactions.items():
            if len(interactions) < MIN_INTERACTIONS_PER_USER:
                continue

            # Sắp xếp theo thời gian (đã order ở query nhưng sort lại cho chắc)
            interactions.sort(key=lambda x: x.created_at)

            split_idx = max(1, int(len(interactions) * TRAIN_RATIO))
            train_items = interactions[:split_idx]
            test_items  = interactions[split_idx:]

            if not test_items:
                continue

            # Ưu tiên purchase/cart trong test set (positive_interactions)
            positive_test = [
                i.product_id for i in test_items
                if i.interaction_type in ("purchase", "cart")
            ]
            # Nếu không có purchase/cart, dùng view
            if not positive_test:
                positive_test = [i.product_id for i in test_items]

            train_pids = list({i.product_id for i in train_items})
            test_pids  = list(set(positive_test))

            train_dict[user_id] = train_pids
            test_dict[user_id]  = test_pids
            qualified_users.append(user_id)

        return train_dict, test_dict, qualified_users

    # =========================================================================
    #  Offline Metric: Hit Rate@K
    #  HitRate = % users có ít nhất 1 recommended item trùng với test set
    # =========================================================================

    def evaluate_hit_rate(self, k: int = DEFAULT_K) -> dict:
        """
        Hit Rate@K: % users mà ít nhất 1 trong K gợi ý khớp với ground truth.

        Returns:
            {
                "hit_rate_content_based": float,
                "hit_rate_collaborative":  float,
                "hit_rate_hybrid":         float,
                "num_users":               int,
            }
        """
        train_dict, test_dict, qualified_users = self._split_train_test()
        if not qualified_users:
            return {"error": "Không đủ dữ liệu (cần ít nhất {} interactions/user)".format(MIN_INTERACTIONS_PER_USER)}

        hits = {"content_based": 0, "collaborative": 0, "hybrid": 0}

        for user_id in qualified_users:
            train_pids = set(train_dict.get(user_id, []))
            test_pids  = set(test_dict.get(user_id, []))

            # Content-based: gợi ý dựa trên trung bình TF-IDF của products đã interact
            cb_recs  = self._get_content_recs_from_ids(list(train_pids), train_pids, k)
            cf_recs  = self._get_cf_recs(user_id, train_pids, k)
            hyb_recs = self._get_hybrid_recs(user_id, train_pids, k)

            if set(cb_recs) & test_pids:
                hits["content_based"] += 1
            if set(cf_recs) & test_pids:
                hits["collaborative"] += 1
            if set(hyb_recs) & test_pids:
                hits["hybrid"] += 1

        n = len(qualified_users)
        return {
            "hit_rate_content_based": round(hits["content_based"] / n, 4) if n else 0.0,
            "hit_rate_collaborative":  round(hits["collaborative"]  / n, 4) if n else 0.0,
            "hit_rate_hybrid":         round(hits["hybrid"]         / n, 4) if n else 0.0,
            "num_users":               n,
        }

    # =========================================================================
    #  Offline Metric: Precision@K và Recall@K
    # =========================================================================

    def evaluate_precision_recall(self, k: int = DEFAULT_K) -> dict:
        """
        Precision@K: (# recommended ∩ relevant) / K
        Recall@K   : (# recommended ∩ relevant) / |relevant|

        Returns dict với precision và recall cho từng algorithm.
        """
        train_dict, test_dict, qualified_users = self._split_train_test()
        if not qualified_users:
            return {"error": "Không đủ dữ liệu"}

        sums = {
            "content_based": {"precision": 0.0, "recall": 0.0},
            "collaborative":  {"precision": 0.0, "recall": 0.0},
            "hybrid":         {"precision": 0.0, "recall": 0.0},
        }

        for user_id in qualified_users:
            train_pids = set(train_dict.get(user_id, []))
            test_pids  = set(test_dict.get(user_id, []))
            if not test_pids:
                continue

            recs = {
                "content_based": self._get_content_recs_from_ids(list(train_pids), train_pids, k),
                "collaborative":  self._get_cf_recs(user_id, train_pids, k),
                "hybrid":         self._get_hybrid_recs(user_id, train_pids, k),
            }

            for algo, rec_ids in recs.items():
                hits = len(set(rec_ids) & test_pids)
                sums[algo]["precision"] += hits / k if k else 0
                sums[algo]["recall"]    += hits / len(test_pids)

        n = len(qualified_users)
        result = {"num_users": n, "k": k}
        for algo in sums:
            result[f"precision_{algo}"] = round(sums[algo]["precision"] / n, 4) if n else 0.0
            result[f"recall_{algo}"]    = round(sums[algo]["recall"]    / n, 4) if n else 0.0

        return result

    # =========================================================================
    #  Offline Metric: NDCG@K (Normalized Discounted Cumulative Gain)
    # =========================================================================

    def evaluate_ndcg(self, k: int = DEFAULT_K) -> dict:
        """
        NDCG@K: xét thứ hạng trong danh sách — item ở vị trí đầu quan trọng hơn.
        Relevance score: purchase=3, cart=2, view=1.

        Returns dict với ndcg cho từng algorithm.
        """
        # Lấy relevance score thực tế từ test data
        all_interactions = (
            UserInteraction.query
            .filter(UserInteraction.interaction_type.in_(["view", "cart", "purchase"]))
            .all()
        )
        rel_score_map = {"purchase": 3.0, "cart": 2.0, "view": 1.0}
        # {(user_id, product_id): max_relevance_score}
        relevance: dict[tuple, float] = {}
        for inter in all_interactions:
            key = (inter.user_id, inter.product_id)
            score = rel_score_map.get(inter.interaction_type, 1.0)
            relevance[key] = max(relevance.get(key, 0.0), score)

        train_dict, test_dict, qualified_users = self._split_train_test()
        if not qualified_users:
            return {"error": "Không đủ dữ liệu"}

        ndcg_sums = {"content_based": 0.0, "collaborative": 0.0, "hybrid": 0.0}

        for user_id in qualified_users:
            train_pids = set(train_dict.get(user_id, []))
            test_pids  = set(test_dict.get(user_id, []))

            recs = {
                "content_based": self._get_content_recs_from_ids(list(train_pids), train_pids, k),
                "collaborative":  self._get_cf_recs(user_id, train_pids, k),
                "hybrid":         self._get_hybrid_recs(user_id, train_pids, k),
            }

            for algo, rec_ids in recs.items():
                dcg  = self._dcg(user_id, rec_ids, test_pids, relevance)
                idcg = self._idcg(user_id, test_pids, relevance, k)
                ndcg_sums[algo] += (dcg / idcg) if idcg > 0 else 0.0

        n = len(qualified_users)
        return {
            "ndcg_content_based": round(ndcg_sums["content_based"] / n, 4) if n else 0.0,
            "ndcg_collaborative":  round(ndcg_sums["collaborative"]  / n, 4) if n else 0.0,
            "ndcg_hybrid":         round(ndcg_sums["hybrid"]         / n, 4) if n else 0.0,
            "num_users":           n,
            "k":                   k,
        }

    def _dcg(self, user_id, rec_ids, test_pids, relevance):
        """Tính DCG cho 1 user."""
        dcg = 0.0
        for rank, pid in enumerate(rec_ids, start=1):
            if pid in test_pids:
                rel = relevance.get((user_id, pid), 1.0)
                dcg += rel / math.log2(rank + 1)
        return dcg

    def _idcg(self, user_id, test_pids, relevance, k):
        """Tính IDCG (ideal DCG) cho 1 user — sắp xếp test items theo relevance."""
        scores = sorted(
            [relevance.get((user_id, pid), 1.0) for pid in test_pids],
            reverse=True
        )[:k]
        idcg = 0.0
        for rank, rel in enumerate(scores, start=1):
            idcg += rel / math.log2(rank + 1)
        return idcg

    # =========================================================================
    #  Offline Metric: Catalog Coverage
    #  % sản phẩm trong catalog được gợi ý ít nhất 1 lần
    # =========================================================================

    def evaluate_catalog_coverage(self, k: int = DEFAULT_K) -> dict:
        """
        Catalog Coverage: Tổng % sản phẩm được hệ thống gợi ý cho ít nhất 1 user.
        Số cao = ít filter bubble, đề xuất đa dạng.
        """
        total_products = Product.query.count()
        if total_products == 0:
            return {"error": "Không có sản phẩm"}

        _, _, qualified_users = self._split_train_test()
        train_dict, _, _ = self._split_train_test()

        recommended_sets = {
            "content_based": set(),
            "collaborative":  set(),
            "hybrid":         set(),
        }

        for user_id in qualified_users:
            train_pids = set(train_dict.get(user_id, []))
            recommended_sets["content_based"].update(
                self._get_content_recs_from_ids(list(train_pids), train_pids, k)
            )
            recommended_sets["collaborative"].update(
                self._get_cf_recs(user_id, train_pids, k)
            )
            recommended_sets["hybrid"].update(
                self._get_hybrid_recs(user_id, train_pids, k)
            )

        return {
            "coverage_content_based": round(len(recommended_sets["content_based"]) / total_products, 4),
            "coverage_collaborative":  round(len(recommended_sets["collaborative"])  / total_products, 4),
            "coverage_hybrid":         round(len(recommended_sets["hybrid"])         / total_products, 4),
            "total_products":          total_products,
            "num_users":               len(qualified_users),
        }

    # =========================================================================
    #  Offline Metric: Intra-list Diversity
    #  Độ đa dạng category trong 1 batch gợi ý
    # =========================================================================

    def evaluate_diversity(self, k: int = DEFAULT_K) -> dict:
        """
        Intra-list Diversity: Trung bình tỷ lệ category khác nhau trong K gợi ý.
        Score = (số category khác nhau) / K. Cao = đa dạng, thấp = filter bubble.
        """
        # Map product_id → category_id
        products = Product.query.all()
        pid_to_cat = {p.id: p.category_id for p in products}

        _, _, qualified_users = self._split_train_test()
        train_dict, _, _ = self._split_train_test()

        div_sums = {"content_based": 0.0, "collaborative": 0.0, "hybrid": 0.0}

        for user_id in qualified_users:
            train_pids = set(train_dict.get(user_id, []))
            recs = {
                "content_based": self._get_content_recs_from_ids(list(train_pids), train_pids, k),
                "collaborative":  self._get_cf_recs(user_id, train_pids, k),
                "hybrid":         self._get_hybrid_recs(user_id, train_pids, k),
            }
            for algo, rec_ids in recs.items():
                if rec_ids:
                    categories_in_list = {pid_to_cat.get(pid) for pid in rec_ids if pid in pid_to_cat}
                    div_sums[algo] += len(categories_in_list) / len(rec_ids)

        n = len(qualified_users) or 1
        return {
            "diversity_content_based": round(div_sums["content_based"] / n, 4),
            "diversity_collaborative":  round(div_sums["collaborative"]  / n, 4),
            "diversity_hybrid":         round(div_sums["hybrid"]         / n, 4),
            "num_users":                n,
            "k":                        k,
        }

    # =========================================================================
    #  Online Metrics (Phương án B) — từ UserInteraction.source
    # =========================================================================

    def get_online_metrics(self) -> dict:
        """
        Online metrics dựa trên field source='recommendation' trong UserInteraction.

        Tính:
          - CTR: view từ recommendation / tổng interaction từ recommendation
          - Conversion Rate: purchase từ recommendation / view từ recommendation
          - Acceptance Rate: % users click+purchase ≥1 sản phẩm từ rec
          - Avg recommendation count per user (who saw rec)
        """
        from sqlalchemy import func

        total_rec_views = UserInteraction.query.filter_by(
            source="recommendation", interaction_type="view"
        ).count()

        total_rec_carts = UserInteraction.query.filter_by(
            source="recommendation", interaction_type="cart"
        ).count()

        total_rec_purchases = UserInteraction.query.filter_by(
            source="recommendation", interaction_type="purchase"
        ).count()

        total_rec_interactions = total_rec_views + total_rec_carts + total_rec_purchases
        total_interactions = UserInteraction.query.count()

        # CTR = xem từ recommendation / tổng xem
        all_views = UserInteraction.query.filter_by(interaction_type="view").count()
        ctr = round(total_rec_views / all_views, 4) if all_views else 0.0

        # Conversion Rate = purchase_from_rec / view_from_rec
        conversion_rate = round(total_rec_purchases / total_rec_views, 4) if total_rec_views else 0.0

        # Cart Rate = cart_from_rec / view_from_rec
        cart_rate = round(total_rec_carts / total_rec_views, 4) if total_rec_views else 0.0

        # Users tương tác từ recommendation
        rec_user_ids = db.session.query(
            UserInteraction.user_id
        ).filter(
            UserInteraction.source == "recommendation"
        ).distinct().count()

        # Acceptance Rate (≥1 purchase từ recommendation)
        accepted_users = db.session.query(UserInteraction.user_id).filter(
            UserInteraction.source == "recommendation",
            UserInteraction.interaction_type == "purchase",
        ).distinct().count()

        acceptance_rate = round(accepted_users / rec_user_ids, 4) if rec_user_ids else 0.0

        return {
            "ctr":                    ctr,
            "conversion_rate":        conversion_rate,
            "cart_rate":              cart_rate,
            "acceptance_rate":        acceptance_rate,
            "total_rec_views":        total_rec_views,
            "total_rec_carts":        total_rec_carts,
            "total_rec_purchases":    total_rec_purchases,
            "total_rec_interactions": total_rec_interactions,
            "rec_active_users":       rec_user_ids,
            "accepted_users":         accepted_users,
            "total_interactions":     total_interactions,
        }

    # =========================================================================
    #  Main: Run Full Evaluation + Save to DB
    # =========================================================================

    def run_full_evaluation(self, k: int = DEFAULT_K) -> dict:
        """
        Chạy toàn bộ offline + online metrics, lưu vào EvaluationResult.

        Returns: dict kết quả đầy đủ + run_id + timestamp
        """
        run_id = str(uuid.uuid4())[:8]
        computed_at = datetime.utcnow()

        # ── Offline ─────────────────────────────────────────────────────────
        pr      = self.evaluate_precision_recall(k)
        hr      = self.evaluate_hit_rate(k)
        ndcg_r  = self.evaluate_ndcg(k)
        cov     = self.evaluate_catalog_coverage(k)
        div     = self.evaluate_diversity(k)

        # ── Online ──────────────────────────────────────────────────────────
        online  = self.get_online_metrics()

        num_users = pr.get("num_users", 0)

        # ── Lưu vào DB ──────────────────────────────────────────────────────
        records_to_save = []

        # Offline metrics per algorithm
        for algo in ["content_based", "collaborative", "hybrid"]:
            records_to_save += [
                EvaluationResult(run_id=run_id, computed_at=computed_at, algorithm=algo,
                                 metric_name="precision_at_k",
                                 metric_value=pr.get(f"precision_{algo}", 0.0),
                                 k_value=k, num_users_evaluated=num_users),
                EvaluationResult(run_id=run_id, computed_at=computed_at, algorithm=algo,
                                 metric_name="recall_at_k",
                                 metric_value=pr.get(f"recall_{algo}", 0.0),
                                 k_value=k, num_users_evaluated=num_users),
                EvaluationResult(run_id=run_id, computed_at=computed_at, algorithm=algo,
                                 metric_name="hit_rate",
                                 metric_value=hr.get(f"hit_rate_{algo}", 0.0),
                                 k_value=k, num_users_evaluated=num_users),
                EvaluationResult(run_id=run_id, computed_at=computed_at, algorithm=algo,
                                 metric_name="ndcg",
                                 metric_value=ndcg_r.get(f"ndcg_{algo}", 0.0),
                                 k_value=k, num_users_evaluated=num_users),
                EvaluationResult(run_id=run_id, computed_at=computed_at, algorithm=algo,
                                 metric_name="catalog_coverage",
                                 metric_value=cov.get(f"coverage_{algo}", 0.0),
                                 k_value=k, num_users_evaluated=num_users),
                EvaluationResult(run_id=run_id, computed_at=computed_at, algorithm=algo,
                                 metric_name="diversity",
                                 metric_value=div.get(f"diversity_{algo}", 0.0),
                                 k_value=k, num_users_evaluated=num_users),
            ]

        # Online metrics (algorithm = 'all')
        for metric_name, metric_value in [
            ("ctr",             online["ctr"]),
            ("conversion_rate", online["conversion_rate"]),
            ("cart_rate",       online["cart_rate"]),
            ("acceptance_rate", online["acceptance_rate"]),
        ]:
            records_to_save.append(
                EvaluationResult(run_id=run_id, computed_at=computed_at, algorithm="all",
                                 metric_name=metric_name,
                                 metric_value=metric_value,
                                 k_value=None, num_users_evaluated=online["rec_active_users"])
            )

        db.session.add_all(records_to_save)
        db.session.commit()

        return {
            "run_id":       run_id,
            "computed_at":  computed_at.isoformat(),
            "k":            k,
            "offline": {
                "precision_recall": pr,
                "hit_rate":         hr,
                "ndcg":             ndcg_r,
                "catalog_coverage": cov,
                "diversity":        div,
            },
            "online": online,
        }

    # =========================================================================
    #  HELPER: Wrapper gọi recommendation_engine với dữ liệu train
    # =========================================================================

    def _get_content_recs_from_ids(self, interacted_ids: list, exclude_ids: set, k: int) -> list[int]:
        """Content-based: Lấy top-K sản phẩm tương tự dựa trên profile của interacted_ids."""
        self._engine._compute_tfidf_matrix()
        if self._engine._tfidf_matrix is None:
            return []

        product_ids = self._engine._product_ids or []
        indices = [
            product_ids.index(pid)
            for pid in interacted_ids
            if pid in product_ids
        ]
        if not indices:
            return []

        user_profile = np.asarray(self._engine._tfidf_matrix[indices].mean(axis=0))
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(user_profile, self._engine._tfidf_matrix).flatten()

        scored = sorted(
            [(product_ids[i], float(sims[i])) for i in range(len(sims)) if product_ids[i] not in exclude_ids],
            key=lambda x: x[1], reverse=True
        )
        return [pid for pid, _ in scored[:k]]

    def _get_cf_recs(self, user_id: int, exclude_ids: set, k: int) -> list[int]:
        """Collaborative Filtering: Lấy top-K với CF scores."""
        cf_scores = self._engine._get_cf_scores(user_id, exclude_ids)
        if not cf_scores:
            return []
        sorted_ids = sorted(cf_scores, key=cf_scores.get, reverse=True)[:k]
        return sorted_ids

    def _get_hybrid_recs(self, user_id: int, exclude_ids: set, k: int) -> list[int]:
        """Hybrid: Weighted combination CF + Content + Popular."""
        interacted_ids = list(exclude_ids)
        cf_s      = self._engine._normalize_scores(self._engine._get_cf_scores(user_id, exclude_ids))
        content_s = self._engine._normalize_scores(
            self._engine._get_content_scores_for_user(interacted_ids, exclude_ids)
        )
        popular_s = self._engine._normalize_scores(self._engine._get_popular_scores(exclude_ids))

        all_pids = set(cf_s) | set(content_s) | set(popular_s)
        weighted = {
            pid: (
                0.50 * cf_s.get(pid, 0) +
                0.30 * content_s.get(pid, 0) +
                0.20 * popular_s.get(pid, 0)
            )
            for pid in all_pids
        }
        return sorted(weighted, key=weighted.get, reverse=True)[:k]


# Singleton
recommendation_evaluator = RecommendationEvaluator()
