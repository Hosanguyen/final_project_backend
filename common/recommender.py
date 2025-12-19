"""
Production Recommender Engine
Sử dụng hybrid approach: Content-Based + Collaborative Filtering
"""

import pandas as pd
import numpy as np
import pickle
import os
import time
from scipy.sparse import csr_matrix
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.neighbors import NearestNeighbors


class ProductionRecommender:
    """
    Production-ready Recommender Engine
    Sử dụng hybrid approach: Content-Based + Collaborative Filtering
    """
    
    def __init__(self, model_path='recommendation_model.pkl'):
        self.content_knn = None
        self.collab_knn = None
        self.mlb = None
        self.content_vectors = None
        self.interaction_matrix = None
        self.problems_snapshot = None
        self.problem_id_map = None
        self.reverse_map = None
        self.model_path = model_path

    def recalculate_problem_ratings(self, problems_df, submissions_df):
        """
        Tính lại Rating bài toán dựa trên trung bình rating của những user đã giải được.
        Rating Bài Toán ~ Trung bình current_rating của những người AC nó.
        """
        print("[System] Đang tính lại Rating cho bài toán dựa trên user đã giải...")
        
        # Chỉ lấy submission AC
        ac_subs = submissions_df[submissions_df['status'] == 'ac'].copy()
        
        if ac_subs.empty:
            print("[Warning] Không có submission AC nào để tính rating!")
            return problems_df
        
        # Tính trung bình rating của users đã giải mỗi problem
        avg_ratings = ac_subs.groupby('problem_id')['user_rating'].mean()
        
        def update_rating(row):
            pid = row['problem_id']
            if pid in avg_ratings.index and not pd.isna(avg_ratings[pid]):
                # Làm tròn rating
                new_rating = int(round(avg_ratings[pid] / 100) * 100)
                # Giới hạn trong khoảng [800, 3000]
                return max(800, min(3000, new_rating))
            return row['rating']
        
        problems_df['rating'] = problems_df.apply(update_rating, axis=1)
        
        # Cập nhật lại Difficulty dựa trên Rating mới
        def get_difficulty(rating):
            if rating < 1400:
                return 'easy'
            elif rating < 2100:
                return 'medium'
            else:
                return 'hard'
        
        problems_df['difficulty'] = problems_df['rating'].apply(get_difficulty)
        
        print(f"[System] Đã cập nhật Rating cho {len(problems_df)} bài toán.")
        return problems_df

    def fit(self, problems_df, submissions_df):
        """
        Train model offline với dữ liệu từ database
        """
        print(f"\n[Offline Training] Bắt đầu với {len(problems_df)} problems và {len(submissions_df)} submissions...")
        
        # Lọc bài active và public
        active_problems = problems_df[
            (problems_df['is_public'] == True) & 
            (problems_df['is_synced'] == True)
        ].copy()
        
        if active_problems.empty:
            print("[Error] Không có bài toán public nào để train!")
            return False
        
        self.problems_snapshot = active_problems.set_index('problem_id')
        print(f"   -> Có {len(self.problems_snapshot)} bài toán public để train")
        
        # ============ 1. CONTENT-BASED (Tags) ============
        print("\n[1/2] Training Content-Based Model (Tags)...")
        t_start = time.time()
        
        # Chuyển tags thành binary vectors
        self.mlb = MultiLabelBinarizer()
        content_vectors = self.mlb.fit_transform(self.problems_snapshot['tags'])
        self.content_vectors = pd.DataFrame(
            content_vectors,
            index=self.problems_snapshot.index,
            columns=self.mlb.classes_
        )
        
        # Train KNN
        n_samples = len(self.problems_snapshot)
        effective_n = min(50, n_samples)
        
        self.content_knn = NearestNeighbors(
            n_neighbors=effective_n,
            metric='cosine',
            algorithm='brute'
        )
        self.content_knn.fit(content_vectors)
        
        print(f"   ✓ Content-Based trained trong {time.time() - t_start:.2f}s")
        print(f"   ✓ Tags detected: {list(self.mlb.classes_)}")
        
        # ============ 2. COLLABORATIVE FILTERING ============
        print("\n[2/2] Training Collaborative Filtering Model...")
        t_start = time.time()
        
        # Chỉ lấy AC submissions cho valid problems
        ac_subs = submissions_df[submissions_df['status'] == 'ac'].copy()
        valid_problem_ids = set(self.problems_snapshot.index)
        ac_subs = ac_subs[ac_subs['problem_id'].isin(valid_problem_ids)]
        
        if ac_subs.empty:
            print("[Warning] Không có AC submissions, chỉ dùng Content-Based!")
            self.collab_knn = None
            self.interaction_matrix = None
            return True
        
        # Tạo mapping
        self.problem_id_map = {pid: i for i, pid in enumerate(self.problems_snapshot.index)}
        self.reverse_map = {i: pid for pid in self.problems_snapshot.index for i in [self.problem_id_map[pid]]}
        
        unique_users = ac_subs['user_id'].unique()
        user_id_map = {uid: i for i, uid in enumerate(unique_users)}
        
        # Tạo sparse matrix (problem x user)
        row_indices = [self.problem_id_map[pid] for pid in ac_subs['problem_id']]
        col_indices = [user_id_map[uid] for uid in ac_subs['user_id']]
        data = np.ones(len(ac_subs))
        
        self.interaction_matrix = csr_matrix(
            (data, (row_indices, col_indices)),
            shape=(len(self.problems_snapshot), len(unique_users))
        )
        
        # Train KNN
        self.collab_knn = NearestNeighbors(
            n_neighbors=effective_n,
            metric='cosine',
            algorithm='brute'
        )
        self.collab_knn.fit(self.interaction_matrix)
        
        print(f"   ✓ Collaborative trained trong {time.time() - t_start:.2f}s")
        print(f"   ✓ Matrix shape: {self.interaction_matrix.shape} (problems x users)")
        print(f"   ✓ Sparsity: {(1 - self.interaction_matrix.nnz / (self.interaction_matrix.shape[0] * self.interaction_matrix.shape[1])) * 100:.2f}%")
        
        return True

    def save_model(self):
        """Lưu model xuống đĩa"""
        data = {
            'content_knn': self.content_knn,
            'collab_knn': self.collab_knn,
            'mlb': self.mlb,
            'content_vectors': self.content_vectors,
            'interaction_matrix': self.interaction_matrix,
            'problems_snapshot': self.problems_snapshot,
            'problem_id_map': self.problem_id_map,
            'reverse_map': self.reverse_map
        }
        
        # Lưu vào thư mục media
        from django.conf import settings
        model_dir = os.path.join(settings.BASE_DIR, 'media', 'models')
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, self.model_path)
        
        with open(model_path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        print(f"\n[✓] Model đã lưu: {model_path}")
        print(f"    Size: {file_size:.2f} MB")
        
        return model_path

    def _get_candidates(self, model, vector, n_neighbors, is_collab=False):
        """Lấy các bài toán candidate từ KNN model"""
        if model is None:
            return {}
        
        if is_collab:
            n_samples_fit = self.interaction_matrix.shape[0]
        else:
            n_samples_fit = self.content_vectors.shape[0]
        
        safe_n = min(n_neighbors, n_samples_fit)
        
        try:
            distances, indices = model.kneighbors(vector, n_neighbors=safe_n)
        except Exception as e:
            print(f"[Warning] KNN error: {e}")
            return {}
        
        candidates = {}
        for i in range(len(indices[0])):
            idx = indices[0][i]
            dist = distances[0][i]
            
            if is_collab:
                if idx in self.reverse_map:
                    problem_id = self.reverse_map[idx]
                else:
                    continue
            else:
                problem_id = self.content_vectors.index[idx]
            
            # Cosine similarity = 1 - cosine distance
            candidates[problem_id] = 1 - dist
        
        return candidates

    def recommend(self, user_id, solved_ids, valid_problem_ids_set, n_recommendations=5, strategy='similar'):
        """
        Tạo gợi ý cho user
        
        Args:
            user_id: ID của user
            solved_ids: List các problem_id đã giải
            valid_problem_ids_set: Set các problem_id hợp lệ (public, active)
            n_recommendations: Số lượng gợi ý
            strategy: 'similar' (tương đương rating) hoặc 'challenging' (khó hơn)
        
        Returns:
            List of recommended problems
        """
        if self.problems_snapshot is None:
            return []
        
        # Lọc solved_ids nằm trong snapshot
        known_solved_ids = [pid for pid in solved_ids if pid in self.problems_snapshot.index]
        
        # Cold start: User chưa giải bài nào
        if not known_solved_ids:
            # Gợi ý các bài Easy phổ biến
            easy_problems = self.problems_snapshot[
                self.problems_snapshot['difficulty'] == 'easy'
            ].head(n_recommendations)
            
            return easy_problems.reset_index().to_dict('records')
        
        # Tính rating hiện tại của user (dựa trên 10 bài khó nhất đã giải)
        solved_df = self.problems_snapshot.loc[known_solved_ids]
        top_solved = solved_df.sort_values('rating', ascending=False).head(10)
        current_rating = top_solved['rating'].mean()
        
        print(f"[Recommend] User {user_id} rating ước tính: {current_rating:.0f}")
        
        # ============ HYBRID APPROACH ============
        candidates = {}
        alpha = 0.7  # Trọng số Content-Based
        
        # Lấy 5 bài gần nhất làm profile
        recent_ids = known_solved_ids[-5:]
        
        # 1. Content-Based
        if self.content_knn is not None:
            content_profile = self.content_vectors.loc[recent_ids].mean(axis=0).values.reshape(1, -1)
            c_cands = self._get_candidates(self.content_knn, content_profile, n_neighbors=100, is_collab=False)
            
            for pid, score in c_cands.items():
                candidates[pid] = candidates.get(pid, 0) + score * alpha
        
        # 2. Collaborative Filtering
        if self.collab_knn is not None:
            valid_collab_idxs = [
                self.problem_id_map[pid] 
                for pid in known_solved_ids 
                if pid in self.problem_id_map
            ]
            
            if valid_collab_idxs:
                collab_profile = np.asarray(
                    self.interaction_matrix[valid_collab_idxs].mean(axis=0)
                )
                collab_cands = self._get_candidates(
                    self.collab_knn, 
                    collab_profile, 
                    n_neighbors=100, 
                    is_collab=True
                )
                
                for pid, score in collab_cands.items():
                    candidates[pid] = candidates.get(pid, 0) + score * (1 - alpha)
        
        # ============ SCORING & RANKING ============
        final_scores = []
        
        for pid, score in candidates.items():
            # Loại bỏ bài không hợp lệ
            if pid not in valid_problem_ids_set:
                continue
            if pid in solved_ids:
                continue
            
            prob_info = self.problems_snapshot.loc[pid]
            prob_rating = prob_info['rating']
            diff = prob_rating - current_rating
            
            # Rating boost dựa trên strategy
            boost = 1.0
            
            if strategy == 'similar':
                # Ưu tiên bài cùng mức hoặc cao hơn 1 chút
                if -150 <= diff <= 150:
                    boost = 2.0  # Tăng boost cho bài phù hợp
                elif 150 < diff <= 300:
                    boost = 1.5
                elif -300 <= diff < -150:
                    boost = 0.5
                elif diff < -300:
                    boost = 0.1  # Penalty mạnh cho bài quá dễ
                else:
                    boost = 0.3  # Penalty cho bài quá khó
            
            elif strategy == 'challenging':
                # Ưu tiên bài khó hơn
                if 200 <= diff <= 500:
                    boost = 1.5
                elif diff > 500:
                    boost = 1.2
                else:
                    boost = 0.7
            
            # Tính final score với nhiều yếu tố để tạo diversity
            base_score = score * boost
            
            # Thêm random factor nhỏ để tránh duplicate scores (0-5%)
            diversity_factor = 1 + (np.random.random() * 0.05)
            
            final_scores.append({
                'problem_id': pid,
                'title': prob_info['title'],
                'tags': prob_info['tags'],
                'rating': prob_rating,
                'difficulty': prob_info['difficulty'],
                'score': base_score * diversity_factor
            })
        
        # Sort và trả về top N
        if not final_scores:
            return []
        
        df_results = pd.DataFrame(final_scores)
        top_results = df_results.sort_values('score', ascending=False).head(n_recommendations)
        
        return top_results.to_dict('records')
