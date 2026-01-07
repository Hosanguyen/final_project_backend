
import pandas as pd
import numpy as np
import pickle
import os
import time
from scipy.sparse import csr_matrix
from sklearn.preprocessing import MultiLabelBinarizer, MinMaxScaler
from sklearn.neighbors import NearestNeighbors
import implicit
from contests.models import Contest, ContestProblem


os.environ['OPENBLAS_NUM_THREADS'] = '1'


class ProductionRecommender:
    
    def __init__(self, model_path='recommendation_model.pkl'):
        self.als_model = None  
        self.knn_model = None  
        self.item_features = None  
        self.user_item_matrix = None  
        
        self.mlb = None
        self.scaler = None
        
        self.df_problems = None
        self.df_users = None
        
        self.config = {
            'N_LATENT_FACTORS': 30,
            'KNN_NEIGHBORS': 15,
            'HYBRID_ALPHA': 0.6, 
            'RATING_WEIGHT': 10,
            'BEST_RATING_BOOST_WEIGHT': 0.3,
            'NUM_USERS': 0,
            'NUM_PROBLEMS': 0
        }
        
        self.model_path = model_path

    def recalculate_problem_ratings(self, problems_df, submissions_df):
        print("[System] Đang tính lại Rating cho bài toán dựa trên user đã giải...")
        
        ac_subs = submissions_df[submissions_df['status'] == 'ac'].copy()
        
        if ac_subs.empty:
            print("[Warning] Không có submission AC nào để tính rating!")
            return problems_df
        
        avg_elos = ac_subs.groupby('problem_id')['user_elo'].mean()
        
        def update_rating(row):
            pid = row['problem_id']
            if pid in avg_elos.index and not pd.isna(avg_elos[pid]):
                new_rating = int(round(avg_elos[pid] / 100) * 100)
                return max(800, min(3000, new_rating))
            return row['rating']
        
        problems_df['rating'] = problems_df.apply(update_rating, axis=1)
        
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
        print(f"\n[Offline Training] Bắt đầu với {len(problems_df)} problems và {len(submissions_df)} submissions...")
        
        active_problems = problems_df[
            (problems_df['is_public'] == True) & 
            (problems_df['is_synced'] == True)
        ].copy()
        
        if active_problems.empty:
            print("[Error] Không có bài toán public nào để train!")
            return False

        self.df_problems = active_problems.reset_index(drop=True)
        self.config['NUM_PROBLEMS'] = len(self.df_problems)
        print(f"   -> Có {self.config['NUM_PROBLEMS']} bài toán public để train")
        
        print("\n[1/3] Tạo User-Item Interaction Matrix...")
        t_start = time.time()
        
        if submissions_df.empty:
            print("   ⚠ Warning: Không có submissions!")
            return False
        
        interaction_group = submissions_df.groupby(['user_id', 'problem_id']).agg(
            total_attempts=('status', 'count'),
            has_ac=('status', lambda x: (x == 'ac').any())
        ).reset_index()
        
        def calculate_r_ui(row):
            if row['has_ac']: 
                return 1.0
            else:
                return min(0.1 * row['total_attempts'], 0.8)
        
        interaction_group['r_ui'] = interaction_group.apply(calculate_r_ui, axis=1)
        
        if interaction_group.empty:
            print("   ⚠ Warning: Không có interactions!")
            return False  
        
        all_users = submissions_df['user_id'].unique()
        self.config['NUM_USERS'] = len(all_users)
        
        user_id_to_idx = {uid: idx for idx, uid in enumerate(all_users)}
        problem_id_to_idx = {pid: idx for idx, pid in enumerate(self.df_problems['problem_id'])}
        
        row_ind = [user_id_to_idx[uid] for uid in interaction_group['user_id']]
        col_ind = [problem_id_to_idx.get(pid, -1) for pid in interaction_group['problem_id']]
        
        valid_indices = [i for i, col in enumerate(col_ind) if col != -1]
        row_ind = [row_ind[i] for i in valid_indices]
        col_ind = [col_ind[i] for i in valid_indices]
        data = [interaction_group['r_ui'].iloc[i] for i in valid_indices]
        
        self.user_item_matrix = csr_matrix(
            (data, (row_ind, col_ind)),
            shape=(self.config['NUM_USERS'], self.config['NUM_PROBLEMS'])
        )
        
        sparsity = 1.0 - (self.user_item_matrix.nnz / (self.config['NUM_USERS'] * self.config['NUM_PROBLEMS']))
        print(f"   ✓ Matrix shape: {self.user_item_matrix.shape}")
        print(f"   ✓ Sparsity: {sparsity:.4%}")
        print(f"   ✓ Interactions: {self.user_item_matrix.nnz:,}")
        print(f"   ✓ Time: {time.time() - t_start:.2f}s")
        
        self.user_id_to_idx = user_id_to_idx
        self.problem_id_to_idx = problem_id_to_idx
        self.idx_to_user_id = {idx: uid for uid, idx in user_id_to_idx.items()}
        self.idx_to_problem_id = {idx: pid for pid, idx in problem_id_to_idx.items()}
        
        print("\n[2/3] Training Content-Based Model (Tags + Rating)...")
        t_start = time.time()
        
        self.mlb = MultiLabelBinarizer()
        tags_matrix = self.mlb.fit_transform(self.df_problems['tags'])
        
        self.scaler = MinMaxScaler()
        rating_matrix = self.scaler.fit_transform(self.df_problems[['rating']])
        
        rating_weighted = np.repeat(rating_matrix, self.config['RATING_WEIGHT'], axis=1)
        
        self.item_features = np.hstack([rating_weighted, tags_matrix])
        
        n_samples = len(self.df_problems)
        effective_n = min(self.config['KNN_NEIGHBORS'], n_samples)
        
        self.knn_model = NearestNeighbors(
            n_neighbors=effective_n,
            metric='cosine',
            algorithm='brute'
        )
        self.knn_model.fit(self.item_features)
        
        print(f"   ✓ Features shape: {self.item_features.shape}")
        print(f"   ✓ Rating weight: {self.config['RATING_WEIGHT']}/{self.item_features.shape[1]} dims")
        print(f"   ✓ Tags detected: {len(self.mlb.classes_)}")
        print(f"   ✓ Time: {time.time() - t_start:.2f}s")
        
        print("\n[3/3] Training Collaborative Filtering (ALS)...")
        t_start = time.time()
        
        self.als_model = implicit.als.AlternatingLeastSquares(
            factors=self.config['N_LATENT_FACTORS'],
            regularization=0.1,
            iterations=15,
            random_state=42
        )
        
        ALPHA_VAL = 40
        data_conf = (self.user_item_matrix * ALPHA_VAL).astype('double')
        
        self.als_model.fit(data_conf)
        
        print(f"   ✓ Factors: {self.config['N_LATENT_FACTORS']}")
        print(f"   ✓ User factors shape: {self.als_model.user_factors.shape}")
        print(f"   ✓ Item factors shape: {self.als_model.item_factors.shape}")
        print(f"   ✓ Time: {time.time() - t_start:.2f}s")
        
        user_elos = submissions_df.groupby('user_id')['user_elo'].first()
        self.df_users = pd.DataFrame({
            'user_id': all_users,
            'elo': [user_elos.get(uid, 1500) for uid in all_users]
        })
        
        return True

    def save_model(self):
        data = {
            'als_model': self.als_model,
            'knn_model': self.knn_model,
            'item_features': self.item_features,
            'user_item_matrix': self.user_item_matrix,
            'mlb': self.mlb,
            'scaler': self.scaler,
            'df_problems': self.df_problems,
            'df_users': self.df_users,
            'user_id_to_idx': self.user_id_to_idx,
            'problem_id_to_idx': self.problem_id_to_idx,
            'idx_to_user_id': self.idx_to_user_id,
            'idx_to_problem_id': self.idx_to_problem_id,
            'config': self.config,
            'version': '2.0_improved',
            'description': 'Hybrid RS with Implicit ALS + Rating Matching Boost'
        }
        
        from django.conf import settings
        model_dir = os.path.join(settings.BASE_DIR, 'media', 'models')
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, self.model_path)
        
        with open(model_path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        file_size = os.path.getsize(model_path) / (1024 * 1024)
        print(f"\n[✓] Model đã lưu: {model_path}")
        print(f"    Size: {file_size:.2f} MB")
        
        return model_path
    
    def load_model(self):
        from django.conf import settings
        model_dir = os.path.join(settings.BASE_DIR, 'media', 'models')
        model_path = os.path.join(model_dir, self.model_path)
        
        if not os.path.exists(model_path):
            print(f"[Error] Model file not found: {model_path}")
            return False
        
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        self.als_model = data['als_model']
        self.knn_model = data['knn_model']
        self.item_features = data['item_features']
        self.user_item_matrix = data['user_item_matrix']
        
        self.mlb = data['mlb']
        self.scaler = data['scaler']
        
        self.df_problems = data['df_problems']
        self.df_users = data['df_users']
        
        self.user_id_to_idx = data['user_id_to_idx']
        self.problem_id_to_idx = data['problem_id_to_idx']
        self.idx_to_user_id = data['idx_to_user_id']
        self.idx_to_problem_id = data['idx_to_problem_id']
        
        self.config = data['config']
        
        print(f"[✓] Model loaded: {model_path}")
        print(f"    Version: {data.get('version', 'N/A')}")
        
        return True

    def recommend(self, user_id, solved_ids, valid_problem_ids_set, n_recommendations=5):
        if self.df_problems is None or self.als_model is None:
            return []
        
        if user_id not in self.user_id_to_idx:
            return self._cold_start_recommend(n_recommendations)
        
        user_idx = self.user_id_to_idx[user_id]
        
        user_history_idx = self.user_item_matrix[user_idx].indices
        
        if len(user_history_idx) == 0:
            return self._cold_start_recommend(n_recommendations)
        
        user_elo = self.df_users[self.df_users['user_id'] == user_id]['elo'].values
        if len(user_elo) == 0:
            user_elo = 1500
        else:
            user_elo = user_elo[0]
        
        NUM_PROBLEMS = self.config['NUM_PROBLEMS']
        HYBRID_ALPHA = self.config['HYBRID_ALPHA']
        KNN_NEIGHBORS = self.config['KNN_NEIGHBORS']
        rating_boost_weight = self.config['BEST_RATING_BOOST_WEIGHT']
        
        exclude_items = set()
        for pid in solved_ids:
            if pid in self.problem_id_to_idx:
                exclude_items.add(self.problem_id_to_idx[pid])
        
        u_vec = self.als_model.user_factors[user_idx]
        i_mat = self.als_model.item_factors
        cf_raw = np.dot(i_mat, u_vec)
        
        if cf_raw.max() > cf_raw.min():
            cf_norm = (cf_raw - cf_raw.min()) / (cf_raw.max() - cf_raw.min())
        else:
            cf_norm = np.zeros_like(cf_raw)
        
        cb_raw = np.zeros(NUM_PROBLEMS)
        
        if len(user_history_idx) > 0:
            history_features = self.item_features[user_history_idx]
            distances, indices = self.knn_model.kneighbors(history_features)
            
            neighbor_sims = np.zeros(NUM_PROBLEMS)
            neighbor_counts = np.zeros(NUM_PROBLEMS)
            
            for i in range(len(user_history_idx)):
                for j in range(min(KNN_NEIGHBORS, len(indices[i]))):
                    neighbor_idx = indices[i][j]
                    if neighbor_idx in exclude_items:
                        continue
                    sim = 1 - distances[i][j]
                    neighbor_sims[neighbor_idx] += sim
                    neighbor_counts[neighbor_idx] += 1
            
            cb_raw = np.divide(
                neighbor_sims,
                neighbor_counts,
                out=np.zeros_like(neighbor_sims),
                where=neighbor_counts > 0
            )

        if cb_raw.max() > 0:
            cb_norm = cb_raw / cb_raw.max()
        else:
            cb_norm = np.zeros_like(cb_raw)

        problem_ratings = self.df_problems['rating'].values
        rating_diff = problem_ratings - user_elo
        rating_boost = np.zeros(NUM_PROBLEMS)

        for i in range(NUM_PROBLEMS):
            diff = rating_diff[i]

            if diff < -100:
                rating_boost[i] = max(0, 1 - abs(diff) / 500)
            elif -100 <= diff <= 50:
                rating_boost[i] = 1.0
            elif 50 < diff <= 200:
                rating_boost[i] = 0.9 - (diff - 50) / 300
            elif 200 < diff <= 400:
                rating_boost[i] = 0.6 - (diff - 200) / 400
            else:
                rating_boost[i] = max(0.2, 0.4 - (diff - 400) / 1000)
        
        hybrid_base = HYBRID_ALPHA * cf_norm + (1 - HYBRID_ALPHA) * cb_norm
        final_scores = (1 - rating_boost_weight) * hybrid_base + rating_boost_weight * rating_boost

        for item_idx in exclude_items:
            final_scores[item_idx] = -1.0

        for i in range(NUM_PROBLEMS):
            prob_id = self.idx_to_problem_id[i]
            if prob_id not in valid_problem_ids_set:
                final_scores[i] = -1.0

        results = []
        for idx in top_indices:
            if final_scores[idx] < 0:
                continue
            
            prob_id = self.idx_to_problem_id[idx]
            prob_info = self.df_problems[self.df_problems['problem_id'] == prob_id].iloc[0]

            diversity_factor = 1 + (np.random.random() * 0.05)

            contest = Contest.objects.get(slug="practice")
            problem_contest = ContestProblem.objects.filter(problem_id=prob_id, contest=contest).first()

            if not problem_contest:
                continue
            
            results.append({
                'problem_id': int(prob_id),
                'contest_problem_id': problem_contest.id,
                'title': prob_info['title'],
                'tags': prob_info['tags'],
                'rating': int(prob_info['rating']),
                'difficulty': prob_info['difficulty'],
                'score': float(final_scores[idx] * diversity_factor)
            })
        
        return results
    
    def _cold_start_recommend(self, n_recommendations):
        if self.df_problems is None or len(self.df_problems) == 0:
            return []

        easy_problems = self.df_problems[
            self.df_problems['difficulty'] == 'easy'
        ].sort_values('rating').head(n_recommendations)
        
        results = []
        for _, prob in easy_problems.iterrows():
            
            contest = Contest.objects.get(slug="practice")
            problem_contest = ContestProblem.objects.filter(problem_id=prob['problem_id'], contest=contest).first()

            if not problem_contest:
                continue
            
            results.append({
                'problem_id': int(prob['problem_id']),
                'contest_problem_id': problem_contest.id,
                'title': prob['title'],
                'tags': prob['tags'],
                'rating': int(prob['rating']),
                'difficulty': prob['difficulty'],
                'score': 1.0
            })
        
        return results
