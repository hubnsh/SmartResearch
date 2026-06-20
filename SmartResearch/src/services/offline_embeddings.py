"""
离线 Embedding 服务 —— 基于 scikit-learn TF-IDF
不依赖任何外部模型下载，完全本地运行
"""
import pickle
from pathlib import Path
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


class OfflineEmbeddings:
    """零网络依赖的 TF-IDF 向量化服务"""

    def __init__(self, cache_path: str = "data/tfidf_cache.pkl"):
        self.cache_path = Path(cache_path)
        self.vectorizer: TfidfVectorizer = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        if self.cache_path.exists():
            with open(self.cache_path, "rb") as f:
                self.vectorizer = pickle.load(f)
        else:
            self.vectorizer = TfidfVectorizer(
                max_features=384,
                ngram_range=(1, 2),
            )
        self._loaded = True

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self._ensure_loaded()
        if not texts:
            return []
        try:
            matrix = self.vectorizer.fit_transform(texts).toarray()
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "wb") as f:
                pickle.dump(self.vectorizer, f)
            return matrix.tolist()
        except Exception:
            return [[0.0] * 384 for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        self._ensure_loaded()
        if not text:
            return [0.0] * 384
        try:
            vec = self.vectorizer.transform([text]).toarray()
            return vec[0].tolist()
        except Exception:
            return [0.0] * 384
